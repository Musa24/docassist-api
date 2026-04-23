# DOC-2 · Step 3 — `Document` model + `models/__init__.py` export

## Goal

Define the `Document` ORM model (the project's first persistent entity),
register it with `Base.metadata` by subclassing `Base`, and export it
from `app/models/__init__.py` so callers can write
`from app.models import Document`.

No DB table is created yet — declaring a model only registers it with
`Base.metadata` in memory. The actual `CREATE TABLE` runs in Step 5
when `create_all` is called.

## Why Step 3 is "just a model definition"

ORM models are the contract that everything else depends on:

- Step 4's Pydantic schemas mirror fields of this model.
- Step 5's `create_all` walks `Base.metadata` and materialises tables
  from it.
- Future upload/query tickets will read/write rows of this table.

Keeping the model definition in its own step means if the schema is
wrong, we notice *before* stacking schemas and app wiring on top of it.

## The file structure

### `app/models/document.py`

```python
"""Document ORM model — tracks uploaded PDF metadata, extracted text, AI summary, status."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Document(Base):
    """A document uploaded for question-answering."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int] = mapped_column(Integer)
    text_content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

### `app/models/__init__.py`

```python
"""ORM model exports."""

from app.models.document import Document

__all__ = ["Document"]
```

## Why each design choice

### Typed `Mapped[T]` + `mapped_column(...)` (2.x style)

Two older styles exist in SQLAlchemy:

- 1.x: `id = Column(Integer, primary_key=True)` — no Python type info.
- 2.0 transitional: `id: int = Column(...)` — annotation ignored by
  SQLAlchemy, type info is misleading.

We use 2.x-native:

```python
id: Mapped[int] = mapped_column(Integer, primary_key=True)
```

This single line gives:

- A column named `id` with the SQL type `Integer` and `PRIMARY KEY`.
- A Python-level type hint: `Document.id` is `int`. IDEs and mypy
  honour this.
- Nullability read from the type: `Mapped[int]` = NOT NULL,
  `Mapped[int | None]` = NULL allowed.

Because nullability is inferred from the type hint, we don't *need*
`nullable=False` on most columns. I still pass `nullable=False` / `nullable=True`
explicitly in a few places (`filename`, `summary`, `error_message`,
`created_at`, `updated_at`) because being explicit in the column
definition improves code review — a reviewer doesn't have to mentally
cross-reference the type to know the column's nullability.

### `__tablename__ = "documents"`

SQLAlchemy requires a table name for every mapped class. Plural
(`documents`) follows a common convention: table holds multiple rows
of the singular entity. Not a rule, but widely seen in real codebases
and consistent with Rails/Django heritage.

### Field-by-field notes

| Field | Column type | Why |
|---|---|---|
| `id` | `Integer` PK | Ticket-specified auto-increment primary key |
| `filename` | `String` NOT NULL | Original uploaded filename; always present |
| `file_size` | `Integer` | Bytes; cheap to store, useful for UI |
| `page_count` | `Integer` | Populated after PDF parsing |
| `text_content` | `Text` | Extracted body. `Text` over `String` because content can be arbitrarily large — SQLite ignores the distinction but Postgres etc. don't |
| `summary` | `Text` NULL | AI-generated, populated asynchronously after summarisation; NULL until ready |
| `status` | `String` | `"processing"` / `"completed"` / `"failed"` — kept as plain string, see next section |
| `error_message` | `String` NULL | Populated only when `status == "failed"` |
| `created_at` | `DateTime` NOT NULL, server default `NOW()` | Row creation timestamp |
| `updated_at` | `DateTime` NOT NULL, server default `NOW()`, on-update `NOW()` | Last modification timestamp |

### Why `status` is a `String`, not a Python `Enum`

Options considered:

1. Plain `String`. Matches ticket text. Three known values enforced by
   the service layer (`"processing"` / `"completed"` / `"failed"`).
2. Python `enum.Enum` + SQLAlchemy `Enum(DocumentStatus)`. Type-safe at
   the Python level. SQLAlchemy translates it to a `VARCHAR` with a
   `CHECK` constraint on most backends (SQLite lacks native ENUM type).

Chose (1) because:

- The ticket explicitly says `String`.
- JSON responses already need to stringify whatever representation we
  pick — an Enum would round-trip through `.value` anyway.
- The three-value constraint can be enforced at the Pydantic schema
  layer in Step 4 (we use `Literal["processing", "completed", "failed"]`
  on input/output schemas once they matter).
- Introducing an Enum now is YAGNI for a model that isn't even queried
  yet.

### Why `server_default=func.now()` and `onupdate=func.now()` (DB-side)

Two ways to auto-populate timestamps:

1. Python-side: `default=datetime.now` (or `default=datetime.utcnow`).
2. DB-side: `server_default=func.now()`, `onupdate=func.now()`.

DB-side is preferred because:

- The database's clock is the single source of truth. Matters less for
  SQLite on one machine, matters a lot once there are multiple writers
  or replicas.
- Avoids tz-awareness foot-guns in Python (`datetime.now()` vs
  `datetime.now(timezone.utc)` — easy to get wrong).
- `onupdate=func.now()` makes the DB handle `updated_at` automatically
  on every `UPDATE`, without service code remembering to set it.
- Standard industry pattern for audit columns.

`func.now()` compiles to `CURRENT_TIMESTAMP` on SQLite, `NOW()` on
Postgres, etc. Dialect-correct automatically.

### Why `text_content` is non-null (empty string on failure, not NULL)

When a PDF fails to parse, our row will look like:

```
status="failed"
error_message="...stack trace or cause..."
text_content=""          # empty string, not NULL
summary=NULL
```

Reasons for empty-string over NULL:

- The ticket's column list doesn't flag `text_content` as nullable.
- Code reading `doc.text_content` doesn't need a `None` guard — it
  just sees an empty string and handles it naturally.
- `None` means "unknown yet" more than "parsing failed". An empty
  string carries the "parsed but nothing came out" semantic cleanly.

### `models/__init__.py` export

```python
from app.models.document import Document

__all__ = ["Document"]
```

Two effects:

1. `from app.models import Document` works (ticket requirement).
2. Importing `app.models` triggers `document.py`'s class definition,
   which registers `Document` with `Base.metadata`. This matters for
   Step 5: `create_all` relies on `Base.metadata` knowing about every
   model class. If a model file is never imported, its table is never
   created.

`__all__` is a gentle hint for `from app.models import *` (which we
won't use), and for docs / IDE completion.

We deliberately don't re-export `Base` here — `Base` lives in
`app.database`, and mixing it into `app.models` would blur the layer
separation.

## Verification

After writing both files:

```
uv run python -c "
from app.models import Document
print('tablename:', Document.__tablename__)
print('columns:', list(Document.__table__.columns.keys()))
"
```

Expected:

- `tablename: documents`
- `columns: ['id', 'filename', 'file_size', 'page_count', 'text_content', 'summary', 'status', 'error_message', 'created_at', 'updated_at']`

No DB file created yet (still lazy).

## What is deliberately NOT in this step

- Pydantic schemas → Step 4
- `Base.metadata.create_all(engine)` → Step 5
- Any route that reads/writes documents → later ticket
- Alembic migrations → out of scope; `create_all` is sufficient for
  this early phase
- Indexes beyond the PK → we don't know query patterns yet; adding
  indexes speculatively would be premature

## Acceptance for this step

- `app/models/document.py` exists with all 10 fields.
- `Document` subclasses `Base` from `app.database`.
- `app/models/__init__.py` exports `Document`.
- `from app.models import Document` succeeds.
- `Document.__tablename__ == "documents"`.
- Column list matches the ticket's field list exactly.
- No DB file created.

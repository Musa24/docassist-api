# DOC-2 · Step 4 — Pydantic schemas (`app/schemas/document.py`)

## Goal

Define the Pydantic v2 schemas that the API will use to serialise
`Document` ORM rows into JSON responses:

- `DocumentResponse` — full detail (all 10 fields). For single-resource
  endpoints: `GET /documents/{id}`, create/update responses, etc.
- `DocumentSummary` — lightweight (4 fields). For list endpoints:
  `GET /documents`. Avoids pushing megabytes of `text_content` over
  the wire when callers only want to see what documents exist.

No route uses these schemas yet — DOC-3+ will. This step just gives us
the stable shape.

## Why two schemas, not one

The ticket asks for both deliberately. Returning the full `Document`
(including `text_content` which can be the entire extracted body of a
PDF) in a list-of-documents response would be a real performance
problem — the response payload could be megabytes per row.

Industry pattern:

- **Summary** schema for list views (IDs, labels, a few status columns).
- **Response** schema for detail views (everything).
- **Create** / **Update** schemas would come next — writing-only
  inputs, without server-generated fields like `id` or `created_at`.
  Not in DOC-2's scope.

## The file structure

### `app/schemas/document.py`

```python
"""Pydantic schemas for Document API responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """Full document representation for single-resource API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_size: int
    page_count: int
    text_content: str
    summary: str | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentSummary(BaseModel):
    """Lightweight document representation for list-view endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: str
    created_at: datetime
```

### `app/schemas/__init__.py`

```python
"""Pydantic schema exports."""

from app.schemas.document import DocumentResponse, DocumentSummary

__all__ = ["DocumentResponse", "DocumentSummary"]
```

## Why each design choice

### `model_config = ConfigDict(from_attributes=True)`

This is the Pydantic v2 replacement for the v1 pattern:

```python
# v1 — DO NOT USE in new code
class Config:
    orm_mode = True
```

`from_attributes=True` enables Pydantic to validate a model by reading
*attributes* off an input object (as opposed to keys off a dict). So:

```python
doc: Document = db.get(Document, 1)          # SQLAlchemy ORM row
return DocumentResponse.model_validate(doc)  # reads doc.id, doc.filename, ...
```

FastAPI uses this automatically when a route's return type is a
Pydantic model and you return an ORM object — it calls
`model_validate(...)` for you.

`model_config = ConfigDict(...)` (class attribute) is the modern v2
shape. Inner `class Config` works but emits a deprecation warning in
v2.

### Field types mirror the ORM model exactly

| Schema field | Pydantic type | ORM field |
|---|---|---|
| `id` | `int` | `Integer` primary key |
| `filename` | `str` | `String` NOT NULL |
| `file_size` | `int` | `Integer` |
| `page_count` | `int` | `Integer` |
| `text_content` | `str` | `Text` (empty string for failed parses) |
| `summary` | `str \| None` | `Text` NULL |
| `status` | `str` | `String` |
| `error_message` | `str \| None` | `String` NULL |
| `created_at` | `datetime` | `DateTime` NOT NULL |
| `updated_at` | `datetime` | `DateTime` NOT NULL |

Nullability matches the ORM: `summary` and `error_message` use
`str | None` (PEP 604 union syntax, Python 3.10+). The remaining
`str` / `int` / `datetime` fields are required and non-null on output.

### Why `status: str` and not `Literal["processing","completed","failed"]`

Considered tightening `status` to:

```python
status: Literal["processing", "completed", "failed"]
```

Pydantic would then reject any other value during serialisation.

Chose plain `str` for now because:

- The ticket specifies `status: String`, and DOC-2 is about persistence
  shape, not value constraints.
- The status transitions are driven by the upload / processing flow
  (DOC-3+). Tightening at the schema level before defining that flow
  risks picking the wrong literal set or the wrong layer.
- When a Literal is introduced, it will likely be a shared enum /
  type alias used by both the model (`Mapped[DocumentStatus]`) and
  the schemas. Doing it piecemeal in two tickets would cause churn.

### Why `text_content` is `str`, not `str | None`

The ORM model stores `text_content` as non-null. Failed-parse rows get
an empty string, not `NULL`. The schema mirrors that: `str`, always
present. Service-layer consumers can check `if doc.text_content:` for
emptiness; they never need `if doc.text_content is None:`.

### Why no `DocumentCreate` / `DocumentUpdate` schemas yet

Those schemas describe **input** payloads for write endpoints. The
ticket doesn't ask for any write endpoint in DOC-2. DOC-3 introduces
PDF upload, and that will bring the create schema with it — probably
a schema like:

```python
class DocumentCreate(BaseModel):
    filename: str
    file_size: int
    # text_content, page_count, status filled in by the service, not the caller
```

Building that here now, with no upload flow to validate the shape
against, is speculative and likely to need rework. Avoid YAGNI.

### `__init__.py` exports

Same pattern as `app/models/__init__.py` — intentional re-exports with
`__all__`:

```python
from app.schemas.document import DocumentResponse, DocumentSummary

__all__ = ["DocumentResponse", "DocumentSummary"]
```

Lets callers write `from app.schemas import DocumentResponse, DocumentSummary`
instead of reaching into `app.schemas.document`.

### Why two separate schemas instead of a single one with excluded fields

Alternative: one `DocumentResponse` schema, and in the list route use:

```python
return DocumentResponse.model_validate(doc).model_dump(include={"id", "filename", "status", "created_at"})
```

Rejected because:

- The API consumer has no way of knowing *statically* which fields
  come back from which endpoint — OpenAPI/Swagger schema docs would
  still advertise the full `DocumentResponse`.
- Every list endpoint would need to know the whitelist — easy to forget.
- Two named schemas is self-documenting in the API schema and in code.

This mirrors how FastAPI's own docs teach response models.

## Verification

After writing both files:

```
uv run python -c "
from app.schemas import DocumentResponse, DocumentSummary
print('response fields:', list(DocumentResponse.model_fields.keys()))
print('summary fields:', list(DocumentSummary.model_fields.keys()))
print('response from_attributes:', DocumentResponse.model_config.get('from_attributes'))
"
```

Expected:

- `response fields:` = all 10 ticket fields in order.
- `summary fields:` = `['id', 'filename', 'status', 'created_at']`.
- `response from_attributes: True`.

## What is deliberately NOT in this step

- Wiring `create_all` or creating the DB file → Step 5
- Any route handler using these schemas → later ticket
- `DocumentCreate` / `DocumentUpdate` schemas → later ticket (DOC-3+)
- `Literal` tightening on `status` → later ticket
- Validators (`@field_validator`) → no constraints beyond types yet

## Acceptance for this step

- `app/schemas/document.py` contains `DocumentResponse` (10 fields)
  and `DocumentSummary` (4 fields).
- Both schemas use `model_config = ConfigDict(from_attributes=True)`.
- `app/schemas/__init__.py` exports both.
- `from app.schemas import DocumentResponse, DocumentSummary` succeeds.
- Fields and types match the ORM model's shape.
- Server not yet booted — that's Step 5.

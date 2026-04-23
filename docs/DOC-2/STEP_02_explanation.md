# DOC-2 · Step 2 — `app/database.py`

## Goal

Replace the placeholder `app/database.py` with a real SQLAlchemy 2.x
wiring: an engine pointed at local SQLite, a session factory, a
declarative `Base` for ORM models, and a `get_db` FastAPI dependency.

After this step, nothing in the app *uses* the database yet — but the
foundation is in place for Step 3 (model), Step 4 (schemas), and Step 5
(`create_all` on startup).

## The four building blocks and why each exists

### 1. `engine`

The engine is SQLAlchemy's central hub — it owns the connection pool
and speaks the SQL dialect. One engine per process is the normal
pattern.

```python
engine = create_engine(
    "sqlite:///./docassist.db",
    connect_args={"check_same_thread": False},
)
```

Two things to unpack:

- **URL format:** `sqlite:///./docassist.db` — three slashes + a
  relative path = "SQLite file in the current working directory named
  `docassist.db`". Four slashes `sqlite:////abs/path.db` would be
  absolute. The ticket specifies this exact URL.

- **`check_same_thread=False`:** SQLite's default Python binding
  refuses to share a connection across threads. FastAPI runs request
  handlers in a thread pool, so SQLAlchemy sessions bound to the same
  connection will cross threads. Disabling the check is the standard
  fix for SQLite + any multi-threaded web framework. It is
  **SQLite-specific** — do not carry this over to Postgres. SQLAlchemy
  itself still serialises access per-session so we're not racing the
  underlying library.

### 2. `SessionLocal`

```python
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

A factory that produces `Session` objects. Calling `SessionLocal()`
gives us a new session bound to the engine. The two flags:

- `autocommit=False` — every write lives in an explicit transaction
  until we call `session.commit()`. Safer default than autocommit;
  aligns with how most production apps expect database work to behave
  (transactional units).

- `autoflush=False` — SQLAlchemy will not implicitly flush pending
  changes to the DB on every query. We flush explicitly when needed
  (almost always via `commit()`). Cleaner and avoids surprise
  round-trips mid-query.

These are the recommended defaults for FastAPI + SQLAlchemy per the
FastAPI docs and industry practice.

### 3. `Base`

```python
class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy ORM models."""
```

All ORM models in Step 3 onward will subclass `Base`. That makes them
part of the same metadata collection, which is what `Base.metadata
.create_all(engine)` (Step 5) walks to create all tables.

**Why subclass `DeclarativeBase`, not call `declarative_base()`?**

- `declarative_base()` is the legacy (SQLAlchemy 1.x) factory
  function. It still works in 2.x for backward compat but does not
  support typed model attributes.
- `DeclarativeBase` (2.x-native class) enables the new typed syntax:
  `name: Mapped[str] = mapped_column(...)`. This gives models proper
  type hints at class-definition time — IDEs, mypy, Pydantic, and
  Pyright all see real types instead of untyped `Column` instances.
- Modern code should use `DeclarativeBase`. That's what the
  SQLAlchemy docs recommend and what new projects use in 2024+.

### 4. `get_db`

```python
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a SQLAlchemy Session; closes on request end."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

This is a FastAPI dependency, not a business-logic function. The
`yield`/`finally` pattern is the canonical shape for a per-request
resource:

- `yield db` — FastAPI injects `db` into the route handler, handler
  runs.
- `finally: db.close()` — runs after the handler returns, whether it
  succeeded or raised. Closing the session returns its connection to
  the pool.

Routes that need DB access declare `db: Session = Depends(get_db)` and
FastAPI wires this up. Future tickets will use it.

**Type hint:** `Generator[Session, None, None]` from
`collections.abc` (Python 3.9+ stdlib). `typing.Generator` still works
but is deprecated in favour of the `collections.abc` version per
PEP 585. Three-arg `Generator[Yield, Send, Return]` — we only yield,
don't receive sends, don't return anything, so the second and third
args are `None`.

## Why we hardcode the DATABASE_URL (for now)

The ticket literally specifies `sqlite:///./docassist.db` as the URL.
Parking it as a module-level constant is the simplest correct thing.

A later ticket will move it into `app/config.py` (pydantic-settings
`Settings.database_url`, overridable by `DATABASE_URL` env var). We
don't do that now because:

- The ticket says "populated in a later ticket" for `config.py`.
- Introducing a Settings class just for one URL is YAGNI right now.
- Moving to env-based config is a trivial edit when that ticket lands.

## Why this step doesn't create the DB file

`create_engine(...)` is lazy — it does not connect or create the file
until a statement actually runs. So after this step, no
`docassist.db` appears on disk.

The file gets created in Step 5 when `Base.metadata.create_all(engine)`
runs during app startup. Keeping DB-file creation out of this step
means:

- Import errors in `database.py` (if any) surface cleanly as import
  errors, not mixed with "DB file wasn't created" noise.
- `uv run python -c "from app.database import Base"` works as a
  standalone syntax/import check.

## Verification

After writing the file:

```
uv run python -c "from app.database import engine, SessionLocal, Base, get_db; print('imports ok')"
```

Expected output: `imports ok`. No `docassist.db` yet.

## What is deliberately NOT in this step

- Any ORM model definition → Step 3
- Any Pydantic schema → Step 4
- Calling `Base.metadata.create_all` → Step 5
- Reading the URL from env vars / Settings → later ticket
- Alembic migrations → out of scope for DOC-2 (ticket uses `create_all`
  directly, which is fine for early-stage SQLite dev)

## Acceptance for this step

- `app/database.py` contains: `engine`, `SessionLocal`, `Base`, `get_db`.
- Imports succeed (`uv run python -c "..."` above).
- No `docassist.db` file created yet (lazy engine).
- No other files modified.

# DOC-1 · Step 4 — Create `app/`, `tests/`, `uploads/` tree

## Goal of this step

Create the directory skeleton the ticket requires, plus the minimum amount
of content in each file to make the skeleton *actually boot* (not just
exist on disk). After this step:

- `uv run uvicorn app.main:app` starts a live server.
- `curl localhost:8000/health` returns `{"status": "ok"}`.
- `uv run pytest` discovers the empty `tests/` dir without error.
- `uploads/` is a real tracked folder (via `.gitkeep`) but uploaded PDFs
  dropped into it will be ignored.

## The tree we're creating

```
app/
  __init__.py
  main.py              # minimal bootable FastAPI app + /health
  config.py            # docstring stub — real Settings class in a later ticket
  database.py          # docstring stub — real SQLAlchemy wiring in a later ticket
  models/__init__.py
  schemas/__init__.py
  routes/__init__.py
  services/__init__.py
tests/
  __init__.py
  conftest.py          # empty — fixtures added by later test tickets
uploads/
  .gitkeep             # tracked placeholder; ignore rule drops real PDFs
```

## Why each choice

### Why `app/` is a Python package (has `__init__.py`)

FastAPI is run via the import string `app.main:app` — `uvicorn` has to
be able to `import app.main`. That only works if `app/` is a package
(has `__init__.py`). Same reason applies to every nested folder
(`models/`, `schemas/`, etc.) — they become importable namespaces.

### Why `app/main.py` gets real content, not an empty stub

The ticket's acceptance criteria is "project structure created". A file
can exist and still be broken. The strongest proof the scaffold is
healthy is: boot it. So `main.py` will contain:

```python
"""FastAPI application entrypoint."""
from fastapi import FastAPI

app = FastAPI(title="DocAssist API")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns 200 once the app is up."""
    return {"status": "ok"}
```

Why a `/health` endpoint specifically:
- Industry standard — every deployed web service has one (load balancers,
  k8s liveness probes, uptime monitors all hit it).
- It's the cheapest possible integration test: if this route responds,
  routing, middleware, and the ASGI layer all work.
- Later tickets will add real routes under `app/routes/` — `/health` lives
  directly on the app because it has no dependencies.

### Why `app/config.py` and `app/database.py` are docstring-only stubs

They're called out in the ticket, so they must **exist** — but filling
them in now would mean guessing at env vars / DB URLs before a ticket
defines them. Stubs let future work land cleanly without creating the
file from scratch (which would be visual noise in review).

`app/config.py` content:
```python
"""Application configuration loaded from environment variables.

Populated in a later ticket using pydantic-settings.
"""
```

`app/database.py` content:
```python
"""SQLAlchemy engine, session factory, and Base class.

Populated in a later ticket.
"""
```

### Why the nested `__init__.py` files are empty

`app/models/__init__.py`, `app/schemas/__init__.py`,
`app/routes/__init__.py`, `app/services/__init__.py` — these are pure
namespace markers at this stage. Per the global CLAUDE.md:

> Use `__init__.py` exports intentionally — don't dump everything.

So we don't pre-populate re-exports. Tickets that add a model or route
will add its export to the right `__init__.py` at that time.

### Why `tests/` is a package (`__init__.py`) and has `conftest.py`

- `__init__.py` keeps `pytest` from import-mode collisions when test
  file names overlap (e.g. two `test_main.py` in different subfolders
  later). Safe default for FastAPI projects.
- `conftest.py` is pytest's fixture/plugin file. Empty now; later
  tickets will add fixtures like `client = TestClient(app)` here so
  every test file gets them for free.

### Why `uploads/.gitkeep`

Git doesn't track empty directories. The `.gitkeep` file (convention,
not a git feature) is a zero-byte file whose only purpose is to make
the directory show up in version control. Combined with the Step 1
ignore rule:

```
uploads/*
!uploads/.gitkeep
```

…real uploaded PDFs dropped into `uploads/` by the running app will
be ignored, but the folder itself is guaranteed to exist on every
clone — so `open("uploads/whatever.pdf", "wb")` won't fail with
`FileNotFoundError` in a fresh checkout.

## What we'll verify after

1. `tree app tests uploads` (or equivalent) matches the ticket's
   structure exactly.
2. `uv run uvicorn app.main:app --port 8000` starts without error.
3. `curl -s localhost:8000/health` returns `{"status":"ok"}`.
4. `uv run pytest` runs and exits cleanly with "no tests collected"
   (there are none yet — that's fine, we're verifying discovery).
5. `git status` shows the new tree as untracked. `.venv/` and
   `uploads/*` (except `.gitkeep`) stay ignored.

## What is deliberately NOT in this step

- Real `Settings` class → later ticket
- DB engine / `Base = declarative_base()` → later ticket
- Any SQLAlchemy models → later ticket
- Any Pydantic schemas → later ticket
- Any real routes → later ticket
- `.env.example` → later ticket (nothing reads env vars yet, so
  documenting them now would be premature)
- The first commit → Step 5

## Acceptance for this step

- Every file/folder listed in the ticket exists at the listed path.
- `uv run uvicorn app.main:app` boots and `/health` returns 200.
- `uv run pytest` exits 0 (no tests collected is fine).
- `uploads/` is tracked via `.gitkeep`; `uploads/foo.pdf` would be ignored.
- No commits made.

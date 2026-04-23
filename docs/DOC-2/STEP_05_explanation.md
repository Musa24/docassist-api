# DOC-2 · Step 5 — Wire `create_all` into `app/main.py` + boot check

## Goal

Make the Document table actually exist in SQLite when the app starts.
Verify by booting the server and inspecting `docassist.db`.

After this step, every previous file (database.py, Document model,
schemas) is wired up and observable at runtime — not just importable.

## The updated `app/main.py`

```python
"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.database import Base, engine
from app.models import Document  # noqa: F401  -- register model with Base.metadata

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DocAssist API")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns 200 once the app is up."""
    return {"status": "ok"}
```

## Why each line, in order

1. **`from app.database import Base, engine`** — pulls in the
   declarative Base (which owns `.metadata`) and the engine (the thing
   we'll issue DDL through).

2. **`from app.models import Document  # noqa: F401`** — the critical
   line. See "The unused-import-that-isn't" section below.

3. **`Base.metadata.create_all(bind=engine)`** — issues
   `CREATE TABLE IF NOT EXISTS` for every model registered with
   `Base.metadata`. Idempotent: safe to run on every boot. Does **not**
   alter existing tables (Alembic territory).

4. **`app = FastAPI(title="DocAssist API")`** — the ASGI object uvicorn
   imports. Module global so `uvicorn app.main:app` can find it.

5. **`@app.get("/health")`** — untouched from DOC-1. Still the cheapest
   end-to-end health check.

## The unused-import-that-isn't

```python
from app.models import Document  # noqa: F401
```

Looks useless at first read — `Document` is never referenced in this
file. But SQLAlchemy models register themselves with `Base.metadata`
at **class-definition time**. That only happens when the module
containing the class is imported.

- If this import is missing, `app.models.document` is never loaded,
  the `Document` class is never defined, `Base.metadata.tables` is
  empty, and `create_all` creates **zero tables**. The app boots fine
  but `docassist.db` will have no `documents` table.
- The `# noqa: F401` tells linters (flake8, ruff) "yes, this import
  looks unused, but keep it". Without the comment, an auto-formatter
  might remove it.

A reader encountering this for the first time will wonder why the
import is there — that's what the inline comment
`-- register model with Base.metadata` is for. One of the few places
where a comment passes the "would removing it confuse a reader?" test.

### Alternatives considered

- **Import `app.models` (the package), not the class.** Works
  equivalently because `app/models/__init__.py` imports `Document`.
  Chose the explicit class import because it reads more clearly —
  someone scanning the imports sees exactly which model got loaded.

- **Put `create_all` inside a FastAPI `lifespan` context manager.**
  This is the newer "correct" pattern and the one a production app
  would use. It looks like:
  ```python
  from contextlib import asynccontextmanager

  @asynccontextmanager
  async def lifespan(_app: FastAPI):
      Base.metadata.create_all(bind=engine)
      yield

  app = FastAPI(lifespan=lifespan)
  ```
  Downsides for DOC-2:
  - The ticket says "app/main.py creates a FastAPI app and calls
    create_all" — simplest reading is a module-level call.
  - Lifespan runs on app startup but not on `import app.main`, which
    means `uv run python -c "import app.main; ..."` wouldn't create
    tables. Slight surprise for anyone wiring tests later.
  - Extra ceremony for one line of DDL.

  Will revisit if/when we introduce Alembic or an async startup task.

- **Auto-discover models via `pkgutil`.** Walk `app.models` and import
  every submodule. Unnecessary for one model; reintroduces an import
  side-effect that's harder to reason about than the explicit line.

## Why `create_all` at module-import time is fine here (and its limits)

Safe because:

- SQLite file creation is fast and cheap.
- `CREATE TABLE IF NOT EXISTS` is idempotent — running on every import
  is wasteful but not destructive.
- No data loss risk: existing tables are untouched.

Not safe forever. Known limitations to revisit:

- **Schema changes aren't applied.** If we later add a column to
  `Document`, `create_all` does nothing. Alembic migrations take over
  at that point.
- **Production databases.** Running DDL against Postgres/MySQL on
  every boot is not how mature systems work — migrations run as a
  separate deploy step. SQLite + small app + early-phase development
  is the happy case where this shortcut is acceptable.
- **Test isolation.** Tests that import `app.main` will trigger table
  creation against whatever engine the test config points to. A later
  ticket that introduces `pytest` fixtures for the DB will likely use
  a separate in-memory SQLite engine or overrideable
  `get_db` dependency — both standard FastAPI test patterns.

## Why we don't change `.gitignore` for `docassist.db`

Acceptance criterion says "docassist.db added to .gitignore". The
scaffold from DOC-1 already has:

```
*.db
*.sqlite
*.sqlite3
```

`docassist.db` matches `*.db` — already ignored. Adding an explicit
`docassist.db` line would be redundant and slightly worse (two rules
that mean the same thing, one narrower).

Verification in this step includes running
`git check-ignore docassist.db` to **prove** the rule works. That is
the honest way to satisfy the acceptance criterion: not by adding a
redundant line, but by demonstrating the existing rule already meets
it. This deviation will be recorded in `docs/PLAN.md` during Step 6.

## Verification

```
# 1. Boot server (background)
uv run uvicorn app.main:app --port 8765

# 2. Sanity
curl -s localhost:8765/health        # expect {"status":"ok"}

# 3. DB file exists
ls docassist.db                      # expect the file

# 4. Table exists with the right schema
sqlite3 docassist.db ".schema documents"
# expect: CREATE TABLE documents (id INTEGER NOT NULL PRIMARY KEY, filename VARCHAR NOT NULL, ...)

# 5. File is ignored by git (existing rule, not a new line)
git check-ignore -v docassist.db     # expect rule .gitignore:<line> uploads→*.db

# 6. git status clean except for expected new/modified files
git status
# modified: app/main.py
# untracked: docs/DOC-2/STEP_*_explanation.md, app/database.py (already modified in Step 2), etc.

# 7. Shut server down
```

## What is deliberately NOT in this step

- A `.gitignore` change for `docassist.db` — already covered by `*.db`.
- Any route beyond `/health` — DOC-3+ adds upload/list/query routes.
- Dependency injection of `get_db` into a route — no route needs it
  yet.
- Alembic — later ticket.
- Switching `create_all` to `lifespan` — later ticket.
- `PLAN.md` update / commit / push / PR — that is Step 6.

## Acceptance for this step

- `app/main.py` calls `Base.metadata.create_all(bind=engine)` before
  `app = FastAPI(...)`.
- `app/main.py` imports `Document` (with `# noqa: F401`) so it
  registers with Base.
- Server boots on `uv run uvicorn app.main:app ...` without error.
- `/health` still returns 200.
- `docassist.db` is created on first boot; `documents` table has the
  10 expected columns.
- `git check-ignore` proves `docassist.db` is ignored.

# DocAssist API — Implementation Plan

Running log of completed and in-progress tickets. Updated at the end of
each ticket before opening its PR. Newest first.

---

## DOC-2 — Database connection and Document model

**Status:** In progress — PR open against `main`
**Branch:** feature/DOC-002-database-model
**Jira:** https://udemycourse2495.atlassian.net/browse/DOC-2

### What we did
- [x] Step 1 — create feature branch `feature/DOC-002-database-model` from `main`
- [x] Step 2 — `app/database.py` (engine, SessionLocal, DeclarativeBase, get_db)
- [x] Step 3 — `app/models/document.py` (10-field Document model, typed Mapped/mapped_column) + export from `app/models/__init__.py`
- [x] Step 4 — `app/schemas/document.py` (Pydantic v2 DocumentResponse + DocumentSummary) + export from `app/schemas/__init__.py`
- [x] Step 5 — wire `Base.metadata.create_all(engine)` into `app/main.py`; verified server boots, `documents` table created, `docassist.db` ignored by git
- [x] Step 6 — update PLAN.md, commit, push, open PR, transition Jira to In Progress

(Unchecked items = attempted but not finished. None this ticket.)

### Acceptance criteria (from ticket)
- [x] `app/database.py` contains SQLAlchemy engine (`sqlite:///./docassist.db`), `SessionLocal`, `Base`, `get_db`
- [x] `app/models/document.py` contains Document model with all 10 fields (id, filename, file_size, page_count, text_content, summary, status, error_message, created_at, updated_at)
- [x] `app/models/__init__.py` exports Document
- [x] `app/schemas/document.py` contains DocumentResponse (all fields, from_attributes) and DocumentSummary (id, filename, status, created_at)
- [x] `app/main.py` creates a FastAPI app and calls `create_all`
- [x] Server starts without errors
- [x] `docassist.db` added to `.gitignore` (covered by existing `*.db` rule — see deviations)
- [x] Work done on branch: `feature/DOC-002-database-model`
- [x] Commit message references ticket: `DOC-002: ...`

### Deviations from ticket
- `docassist.db` is **not** added as an explicit line to `.gitignore`. The scaffold's existing `*.db` rule already matches it — verified via `git check-ignore -v docassist.db` → `.gitignore:27:*.db`. Adding a redundant narrower rule was avoided.
- ORM uses SQLAlchemy 2.x modern style: `DeclarativeBase` subclass + `Mapped[T]` / `mapped_column(...)` typed columns. Ticket said "Base declarative base" — legacy `declarative_base()` would also satisfy the wording, but modern style gives real type hints and is the SQLAlchemy-recommended approach in 2026.
- `created_at` / `updated_at` use DB-side defaults (`server_default=func.now()`, `onupdate=func.now()`) rather than Python-side `default=datetime.now`. DB clock is authoritative and avoids timezone foot-guns.
- `status` kept as plain `String` (not a Python `Enum`). Ticket specifies `String`; value constraint can be tightened at the schema layer when the upload/processing flow (DOC-3+) defines state transitions.
- Pydantic schemas use v2 `model_config = ConfigDict(from_attributes=True)`, not the deprecated v1 inner `class Config`.

### Verification
- `uv run python -c "from app.database import engine, SessionLocal, Base, get_db; print('imports ok')"` → `imports ok`
- `uv run python -c "from app.models import Document; print(Document.__tablename__, list(Document.__table__.columns.keys()))"` → `documents ['id', 'filename', 'file_size', 'page_count', 'text_content', 'summary', 'status', 'error_message', 'created_at', 'updated_at']`
- `uv run python -c "from app.schemas import DocumentResponse, DocumentSummary"` → imports ok; `DocumentResponse` has 10 fields, `DocumentSummary` has 4
- `uv run uvicorn app.main:app --port 8765` → booted
- `curl /health` → `{"status":"ok"}`
- `ls docassist.db` → file created (8 KB)
- `sqlite3 docassist.db ".schema documents"` → CREATE TABLE with 10 columns, correct nullability, CURRENT_TIMESTAMP defaults
- `git check-ignore -v docassist.db` → matched by `*.db` rule (ignored as required)

### Next
- Await user review of the PR.
- On approval, merge with `gh pr merge --squash`, sync local `main`, delete feature branches, transition DOC-2 → Done.

### Known residual diagnostic
- Pylance shows a "Document is not accessed" hint on the metadata-side-effect import in `app/main.py`. The import is load-bearing (registers `Document` with `Base.metadata` so `create_all` sees it). Ruff/flake8 suppression `# noqa: F401` is present; Pylance's hint isn't tied to a named rule and ignores the suppression. Cosmetic — left as-is for this ticket; a later ticket that restructures startup (e.g. introducing `lifespan` or Alembic) will naturally dissolve it.

---

## DOC-1 — Initialize backend repo and project scaffold

**Status:** Done — merged directly to `main` (bootstrap commit; no PR)
**Branch:** feature/DOC-001-project-scaffold → promoted to `main`
**Jira:** https://udemycourse2495.atlassian.net/browse/DOC-1

### What we did
- [x] Step 1 — git init + feature branch + .gitignore + .python-version
- [x] Step 2 — uv init (pyproject.toml)
- [x] Step 3 — runtime + dev deps via `uv add`
- [x] Step 4 — app/, tests/, uploads/ tree
- [x] Step 5 — atomic commit on feature branch

(Unchecked items = attempted but not finished. None this ticket.)

### Acceptance criteria (from ticket)
- [x] Public GitHub repo "docassist-api" exists
- [x] Python .gitignore present
- [x] Project initialized with uv (pyproject.toml)
- [x] Project structure created (app/ tree, tests/, uploads/.gitkeep)
- [x] Dependencies added via uv: fastapi, uvicorn, sqlalchemy, pydantic, pydantic-settings, python-multipart, anthropic, pymupdf, httpx, pytest
- [x] .python-version file present
- [x] uv.lock committed
- [x] uploads/ directory exists with .gitkeep (actual files gitignored)
- [x] Branch: feature/DOC-001-project-scaffold
- [x] Commit message references ticket: "DOC-001: ..."

### Deviations from ticket
- `pytest` moved from runtime deps to `[dependency-groups.dev]` (PEP 735 — keeps prod install lean).
- Project placed inside umbrella folder `DocAssist/` (polyrepo layout: `docassist-api` + future `docassist-web`).

### Verification
- `uv run uvicorn app.main:app --port 8765` → booted
- `curl /health` → `{"status":"ok"}`
- `uv run pytest` → exit 5 (no tests collected — expected at scaffold stage)

### Next
- None for DOC-1. From DOC-2 onwards, normal feature-branch → PR → main workflow applies.

### Note on skipped PR
`main` did not exist when the feature branch was first pushed (GitHub auto-set the feature
branch as the default because the remote repo was empty). For a bootstrap commit, industry
practice is to land the initial scaffold directly on `main` rather than open an artificial PR
against an empty base. The feature branch was therefore renamed/promoted to `main` and set as
the default; the old feature branch was deleted from the remote.

---

<!-- Future tickets append new top sections above this line -->

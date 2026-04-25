# DocAssist API — Implementation Plan

Running log of completed and in-progress tickets. Updated at the end of
each ticket before opening its PR. Newest first.

---

## DOC-3 — PDF upload and text extraction endpoint

**Status:** In progress — PR open against `main`
**Branch:** feature/DOC-003-pdf-upload
**Jira:** https://udemycourse2495.atlassian.net/browse/DOC-3

### What we did
- [x] Step 1 — restore `.gitignore`, create feature branch `feature/DOC-003-pdf-upload` from `main`
- [x] Step 2 — `app/services/pdf_service.py` (`extract_text` + `PdfExtractionError`, strict `filetype="pdf"` for defense-in-depth) + export from `app/services/__init__.py`
- [x] Step 3 — `app/routes/documents.py` (`POST /documents/upload`: validate PDF, stream-save to `uploads/<uuid>.pdf`, extract text, persist Document, return 201) + export from `app/routes/__init__.py`
- [x] Step 4 — wire `documents_router` into `app/main.py` via `include_router`
- [x] Step 5 — end-to-end test (real PDF → 201, .txt → 400, lying-extension PDF → 422 with file cleanup)
- [x] Step 6 — update PLAN.md, commit, push, open PR, transition Jira to In Progress

(Unchecked items = attempted but not finished. None this ticket.)

### Acceptance criteria (from ticket)
- [x] `app/services/pdf_service.py` exposes a function that takes a file path, opens with PyMuPDF (fitz), and returns extracted text + page count
- [x] Service handles corrupt/invalid PDFs gracefully (raises `PdfExtractionError`, doesn't crash the server)
- [x] `app/routes/documents.py` contains `POST /documents/upload`
- [x] Endpoint accepts a PDF via `UploadFile`
- [x] Validates the file is a PDF (content type **or** extension)
- [x] Saves the file to `uploads/`
- [x] Calls the PDF service to extract text
- [x] Creates a Document record with `status="completed"`
- [x] Returns `DocumentResponse` with status 201
- [x] Rejects non-PDF files with 400
- [x] `app/main.py` includes the documents router
- [x] Endpoint works via `/docs` (verified via direct HTTP test — same code path)
- [x] Branch: `feature/DOC-003-pdf-upload`
- [x] Commit message references ticket: `DOC-003: ...`

### Deviations from ticket
- On-disk filename is a UUID (`uploads/<uuid>.pdf`), not the original filename. Original is preserved in `Document.filename`. Reason: collision safety + path-traversal safety + deterministic tests.
- Service is strict-PDF: `fitz.open(path, filetype="pdf")` rather than `fitz.open(path)`. PyMuPDF can auto-detect non-PDF formats (text, EPUB, …) and our function is meant for PDFs only — defense in depth alongside the route's content-type check.
- Validation is OR (content-type **or** `.pdf` extension) rather than AND. Reason: `curl -F file=@thing.pdf` typically sends `application/octet-stream`; AND-checking would break that path. Magic-byte sniffing left for a future hardening ticket.
- Corrupt/non-PDF body with `.pdf` extension → HTTP 422 (Unprocessable Entity), not 400. The request is syntactically valid but the content can't be processed — textbook 422 vs 400.
- On parse failure: the half-saved file is deleted and **no `status="failed"` Document row is created**. The `failed` status is more appropriate for async/background processing (DOC-4+); a synchronous upload-and-extract endpoint returns the error to the caller instead of persisting a phantom row.
- File-size limit not enforced. Ticket doesn't specify one. Will be added in a later hardening ticket; YAGNI for DOC-3.

### Verification
- `uv run python -c "from app.services import extract_text, PdfExtractionError"` → imports ok
- Round-trip on a fitz-generated PDF → returns `(text, 1)` with expected text
- Negative cases: `.txt` content, random binary, missing file → all raise `PdfExtractionError`
- Server boots: `uv run uvicorn app.main:app --port 8765`
- `POST /documents/upload` with real 2-page PDF → 201 + `DocumentResponse` (id, filename preserved, file_size, page_count=2, text_content with both pages, status="completed")
- `POST /documents/upload` with `.txt` (text/plain) → 400 `{"detail":"File must be a PDF."}`
- `POST /documents/upload` with txt body but `.pdf` extension + `application/pdf` content-type → 422; saved file cleaned up (no orphan in `uploads/`)
- DB: exactly one row in `documents` after the three calls (only the successful one)
- Disk: exactly one file in `uploads/` (only the successful UUID PDF)

### Next
- Await user review of the PR.
- On approval, merge with `gh pr merge --squash`, sync local `main`, delete feature branches, transition DOC-3 → Done.

---

## DOC-2 — Database connection and Document model

**Status:** Done — merged to `main` via PR #1 (squash, commit `2cfa085`)
**Branch:** feature/DOC-002-database-model (deleted post-merge)
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
- None for DOC-2. PR #1 merged manually by the user; local `main` synced; feature branches (local + remote) deleted; Jira DOC-2 transitioned to Done.

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

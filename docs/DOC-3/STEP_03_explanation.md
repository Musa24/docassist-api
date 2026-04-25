# DOC-3 · Step 3 — `app/routes/documents.py` (`POST /documents/upload`)

## Goal

The HTTP entry-point for getting a PDF into the system. This route ties
together everything DOC-1, DOC-2, and Step 2 set up:

- Accepts a multipart upload (`UploadFile`).
- Validates it's a PDF (content-type or extension).
- Streams the bytes to `uploads/<uuid>.pdf` on disk.
- Calls `pdf_service.extract_text` to get text + page count.
- Persists a `Document` row with `status="completed"`.
- Returns `DocumentResponse` with HTTP 201.
- On parse failure: deletes the half-saved file, returns 422.
- On bad content type / extension: returns 400.

## The file

```python
"""Document routes: upload + (future) listing/detail/query."""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document
from app.schemas import DocumentResponse
from app.services import PdfExtractionError, extract_text

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)


def _is_pdf(file: UploadFile) -> bool:
    """True if the upload looks like a PDF by content type or extension."""
    if file.content_type == "application/pdf":
        return True
    if file.filename and file.filename.lower().endswith(".pdf"):
        return True
    return False


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Document:
    """Accept a PDF, save it, extract text, persist a Document row."""
    if not _is_pdf(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF.",
        )

    saved_path = UPLOADS_DIR / f"{uuid.uuid4()}.pdf"
    with saved_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    file_size = saved_path.stat().st_size

    try:
        text, page_count = extract_text(saved_path)
    except PdfExtractionError as exc:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse PDF: {exc}",
        ) from exc

    document = Document(
        filename=file.filename or saved_path.name,
        file_size=file_size,
        page_count=page_count,
        text_content=text,
        status="completed",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
```

## Why each piece

### `APIRouter(prefix="/documents", tags=["documents"])`

The ticket calls for `POST /documents/upload`. Two ways to get that
path:

- (a) Hard-code the full path: `@router.post("/documents/upload")`.
  Fragile — every route in this file would have to repeat
  `/documents/...`.
- (b) Set the prefix at the router level: `prefix="/documents"`, then
  individual decorators just say `@router.post("/upload")`. (chosen)

Tags group the routes in the OpenAPI / Swagger UI. Reviewers/users
opening `/docs` will see a "documents" section. Tiny ergonomic win,
zero cost.

### `UPLOADS_DIR = Path("uploads")` + `mkdir(exist_ok=True)` at import

The `uploads/` folder is committed via `.gitkeep`, so it exists on a
fresh clone. But:

- A fresh CI runner may run tests against a temp working directory
  where it doesn't exist yet.
- Someone may delete it locally.

`mkdir(exist_ok=True)` makes the route resilient. `exist_ok=True`
skips the call if the directory already exists, so this is a no-op
on every boot after the first.

Module-level execution (not inside the route handler) means we pay
this once on app start, not per request.

### `_is_pdf(file)` — content-type OR extension

```python
def _is_pdf(file: UploadFile) -> bool:
    if file.content_type == "application/pdf":
        return True
    if file.filename and file.filename.lower().endswith(".pdf"):
        return True
    return False
```

Why **OR** instead of **AND**:

- Browsers (and `<input type=file>` form posts) reliably send
  `Content-Type: application/pdf` when the user picks a PDF.
- `curl -F file=@thing.pdf` typically sends
  `Content-Type: application/octet-stream` because curl doesn't
  guess MIME types unless told to.
- Picking AND would break the curl path. Picking OR accepts both
  while still rejecting clearly-not-a-PDF posts (a `.txt` file from
  a curl `-F` upload has neither the right content-type nor the
  right extension).

The function is private (`_` prefix) — it's only relevant to this
module. If the rule needs to harden later (e.g. magic-byte sniffing),
this is the single place to change.

`file.filename` can be `None` per the type stubs; the explicit
`if file.filename and ...` guards that.

### Save before validate-content?

Order in this handler:

1. Cheap content-type/extension check (`_is_pdf`).
2. Save to disk.
3. Open with `extract_text` (the real validation).

Why save *before* parsing rather than buffering in memory and
parsing first? Two reasons:

- `pymupdf.fitz.open` accepts a path or a stream, but the stream
  variant has historically been more memory-hungry and slightly more
  awkward (`fitz.open(stream=bytes_, filetype="pdf")`).
- For DOC-4 (summarisation), we'll likely re-open the file by path
  for whatever process turns text into a summary; having the file
  on disk from the start simplifies that.

The cost of "we wrote the file then realised it's invalid" is one
`saved_path.unlink(missing_ok=True)` in the error branch — cheap
cleanup, no orphans.

### `uuid.uuid4()` for the on-disk filename

```python
saved_path = UPLOADS_DIR / f"{uuid.uuid4()}.pdf"
```

Why not the original filename:

- **Collisions:** two users uploading `report.pdf` would clobber each
  other.
- **Path traversal:** filenames can contain `..` or `/` — UUID
  removes all attacker influence on the final path.
- **Filesystem weirdness:** spaces, unicode, very long names — UUID
  filenames are 36 chars of `[0-9a-f-]`, safe everywhere.

Why **keep** the original filename in the DB column `filename`:

- For UI display ("File: report.pdf"), search, and human reports.
- For downloads later: serve the file as `report.pdf` even though it
  lives at `<uuid>.pdf`.

Two concepts, two storage locations. The model already has the right
column for this (`Document.filename`).

### `shutil.copyfileobj(file.file, out)`

Two ways to read an `UploadFile`:

| Method | Memory profile |
|---|---|
| `data = await file.read()` then `out.write(data)` | Whole upload into RAM |
| `shutil.copyfileobj(file.file, out)` | Streamed, default 64 KB buffer |

We pick the streaming one. For a 100 MB PDF, that's the difference
between a 100 MB process spike and a 64 KB blip. Industry standard
for file uploads.

`file.file` (the underlying file-like object) works synchronously
because the route handler is `def`, not `async def`. FastAPI runs
sync handlers in a threadpool, so blocking on `copyfileobj` doesn't
block the event loop.

### `file_size = saved_path.stat().st_size`

After saving, ask the filesystem for the bytes-actually-written. Two
alternatives we don't use:

- `file.size` (attribute on `UploadFile`) — only set in some FastAPI
  versions and not guaranteed.
- Track a counter while streaming — extra book-keeping for no win.

`stat().st_size` is the source of truth and runs in microseconds.

### Error branch: delete the file, raise 422

```python
except PdfExtractionError as exc:
    saved_path.unlink(missing_ok=True)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Could not parse PDF: {exc}",
    ) from exc
```

Two design calls baked in here:

1. **Delete the saved file.** No row was created; leaving the file
   would be orphan data on disk. `missing_ok=True` so a race where
   the file was already gone doesn't itself error.
2. **422, not 400.** 400 ("Bad Request") means "we couldn't parse
   the request itself". 422 ("Unprocessable Entity") means "the
   request was syntactically fine, but its content cannot be
   processed". A bad PDF body sent as `multipart/form-data` is the
   textbook 422.
3. **Don't create a `status="failed"` Document row.** The ticket
   says successful uploads create a Document with `status="completed"`.
   "Failed" rows are useful when processing happens *after* the
   request returns (background jobs, async pipelines) — that's
   DOC-4+ territory. For a synchronous "upload-and-extract"
   endpoint, returning the error to the caller is the simplest
   honest behaviour.

### Persist with `status="completed"`

```python
document = Document(
    filename=file.filename or saved_path.name,
    file_size=file_size,
    page_count=page_count,
    text_content=text,
    status="completed",
)
db.add(document)
db.commit()
db.refresh(document)
return document
```

- `filename or saved_path.name` — `UploadFile.filename` can be
  `None` (per type stubs). Falling back to the on-disk UUID name
  keeps the column non-null.
- `summary` and `error_message` aren't passed — they're nullable in
  the model and stay NULL on a successful upload.
- `created_at` / `updated_at` populated by the DB defaults
  (`CURRENT_TIMESTAMP`).
- `db.refresh(document)` pulls the freshly-generated `id` and
  timestamp values back into the Python object so the response
  includes them.

### Returning the ORM object

The function declares `-> Document` and the route declares
`response_model=DocumentResponse`. FastAPI:

1. Sees the handler return a `Document` (ORM row).
2. Sees `response_model=DocumentResponse`.
3. Calls `DocumentResponse.model_validate(document)` (works because
   the schema has `from_attributes=True`).
4. Serialises the schema to JSON.

So we don't need to manually convert in the handler. Cleaner.

### `status_code=status.HTTP_201_CREATED`

Resource created → 201. The ticket says "Returns DocumentResponse
with status 201". Matches.

## Why `def`, not `async def`

PyMuPDF and SQLAlchemy ORM (in this configuration) are synchronous
libraries. `async def` would force us to wrap every blocking call in
`asyncio.to_thread(...)`, adding noise without changing performance:
under the hood FastAPI runs sync handlers in its threadpool, which is
the same place the wrappers would run.

When the codebase moves to async SQLAlchemy + an async file IO
library, this switches to `async def`. Today, `def` is the cleaner
choice.

## Verification (driven from Step 5, but worth previewing)

Manual:
```
uv run uvicorn app.main:app --port 8000 --reload
# open /docs, call POST /documents/upload with a real PDF → 201
# call POST /documents/upload with a .txt file → 400
# call POST /documents/upload with a corrupted .pdf → 422
sqlite3 docassist.db "SELECT id, filename, page_count, status FROM documents;"
ls uploads/
```

Programmatic (smoke test, can run from python -c):
```
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
# POST a real PDF and assert 201, etc.
```

## What is deliberately NOT in this step

- Wiring the router into `app/main.py` → Step 4.
- The end-to-end test → Step 5.
- A list/detail/query endpoint — not in DOC-3 scope.
- File size limit — not in ticket.
- Background processing / `status="failed"` rows → DOC-4+ territory.
- Magic-byte sniffing for content validation — current OR check is
  enough; can tighten later.

## Acceptance for this step

- `app/routes/documents.py` exposes a `router` named export with
  `POST /documents/upload`.
- Successful upload of a real PDF: returns 201, body is
  `DocumentResponse`, file lands at `uploads/<uuid>.pdf`, row in
  `documents` with `status="completed"`.
- Non-PDF (`.txt`, no PDF content type): 400.
- Corrupted/non-PDF body but with `.pdf` extension: 422 + saved file
  cleaned up.
- No registration with the FastAPI app yet — that's Step 4.

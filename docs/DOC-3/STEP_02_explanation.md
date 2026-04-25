# DOC-3 · Step 2 — `app/services/pdf_service.py`

## Goal

Provide a small, reusable function that turns a PDF file on disk into
a `(text, page_count)` tuple, and a typed exception that callers can
catch without knowing anything about PyMuPDF's internals.

This is the only module in DOC-3 that talks to `fitz`. The route
handler (Step 3) will import `extract_text` and `PdfExtractionError`
from here and nothing else.

## The file

```python
"""PDF text extraction using PyMuPDF (fitz).

Thin wrapper around fitz that returns a (text, page_count) tuple.
Route handlers catch PdfExtractionError and convert to HTTP 422.
"""

from pathlib import Path

import fitz


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be opened or parsed."""


def extract_text(path: str | Path) -> tuple[str, int]:
    """Open a PDF at `path` and return (all-pages-concatenated text, page count).

    Raises:
        PdfExtractionError: if the file is missing, not a valid PDF, or
            cannot be parsed. The original cause is chained via `from`.
    """
    try:
        doc = fitz.open(path, filetype="pdf")
    except Exception as exc:
        raise PdfExtractionError(f"Failed to open PDF at {path}: {exc}") from exc

    try:
        pages = [page.get_text() for page in doc]
    except Exception as exc:
        raise PdfExtractionError(f"Failed to extract text from {path}: {exc}") from exc
    finally:
        doc.close()

    return "\n".join(pages), len(pages)
```

Plus `app/services/__init__.py`:

```python
"""Service layer exports."""

from app.services.pdf_service import PdfExtractionError, extract_text

__all__ = ["PdfExtractionError", "extract_text"]
```

## Why a service layer at all

Routes and services play different roles:

- **Route** (`app/routes/documents.py`) — HTTP plumbing: parse
  request, enforce content type, convert to/from `HTTPException`,
  persist to DB, return a response model.
- **Service** (`app/services/pdf_service.py`) — domain logic: "given
  a PDF on disk, give me its text and page count". No HTTP, no DB, no
  FastAPI.

Keeping the service stateless and HTTP-agnostic means:

- It's trivially unit-testable (future ticket) — pass a file path,
  get a tuple. No `TestClient` needed.
- Future consumers (e.g. a CLI tool, a batch re-processor) can reuse
  it unchanged.
- Route handlers stay thin, which is the FastAPI recommended pattern
  (and the global CLAUDE.md rule: "Keep route handlers thin —
  business logic belongs in service modules").

## Why a custom `PdfExtractionError`

PyMuPDF's exception hierarchy is not a stable public contract. It has
changed across versions (e.g. `fitz.FileDataError` vs generic
`RuntimeError`). Worse, some parsing failures surface as the built-in
`ValueError` or `RuntimeError`.

The route handler should not care. It cares about two outcomes:
success, or "the input was unusable → return 422". A typed exception
owned by **our** code expresses that intent:

```python
try:
    text, pages = extract_text(path)
except PdfExtractionError as exc:
    raise HTTPException(status_code=422, detail=str(exc)) from exc
```

The route handler never imports `fitz` and never has to guess its
exception taxonomy.

### Why `raise ... from exc`

Exception chaining. When the route catches `PdfExtractionError` and
logs or re-raises, the traceback still contains the original `fitz`
failure as the cause. Debugging a real production issue means seeing
"corrupted xref at offset 1234" in the server log — that only
survives if we chain with `from`.

## Why two `try` blocks (not one big one)

```python
try:
    doc = fitz.open(path)
except Exception as exc:
    raise PdfExtractionError(f"Failed to open PDF at {path}: {exc}") from exc

try:
    pages = [page.get_text() for page in doc]
except Exception as exc:
    raise PdfExtractionError(f"Failed to extract text from {path}: {exc}") from exc
finally:
    doc.close()
```

Two different failure modes deserve different diagnostic messages:

- First block — opening failed. Usually: missing file, wrong
  format, permissions. Message starts with "Failed to open...".
- Second block — file opened fine but a page failed to render
  (corrupt xref table, encrypted page, etc). Message starts with
  "Failed to extract text...".

Collapsing them into one `try` would work functionally, but the
operator reading logs couldn't tell open-fail from parse-fail at a
glance. The two-block form is a small cost for meaningfully better
error signals.

`finally: doc.close()` only guards the second block because `doc` only
exists after the first `fitz.open` succeeds — there's nothing to close
if open itself failed.

### Why `filetype="pdf"` on `fitz.open`

PyMuPDF can open many formats (PDF, XPS, EPUB, plain text, …). With no
hint it tries to auto-detect — which means `fitz.open("not-a-pdf.txt")`
might happily parse the text file as a one-page text document. That's
not what we want: the service is named `pdf_service` and the contract
is "give me a PDF or fail".

Passing `filetype="pdf"` forces the strict-PDF parser. Anything that
isn't a real PDF — text files, JPEGs, missing files, garbage bytes —
fails fast and is wrapped in `PdfExtractionError`. Defense in depth:
even if the route's content-type check has a gap, the service still
rejects non-PDFs.

## Why catching `Exception` and not narrower types

Three options considered:

1. `except (fitz.FileDataError, fitz.EmptyFileError, ...)` — the
   precise set.
2. `except RuntimeError` — catches most but not all of fitz's ways to
   fail.
3. `except Exception` — what we use.

Chose (3) because:

- PyMuPDF's precise exception types have shifted across versions;
  pinning to a list risks silently missing a new variant.
- The *re-raise with our typed error chained* means nothing is
  swallowed — every caught exception becomes a `PdfExtractionError`
  whose `__cause__` points at the real thing. So "broad catch" here
  doesn't cause the usual "silent catch-all" smell.

`ruff`'s `BLE001` ("do not catch blind Exception") would complain if
we enabled it; we'd suppress with a per-line `# noqa: BLE001` + a
comment pointing at this doc. Small price.

## Why `"\n".join(pages)` for concatenation

The ticket says "extracted text (all pages concatenated)". Options:

| Separator | Effect |
|---|---|
| `""` | Words at end of page N run into start of page N+1 |
| `"\n"` (chosen) | Simple, readable separator, matches most LLM pre-processing expectations |
| `"\n\n"` | Paragraph-like. Slightly more readable for humans |
| `"\n--- page {n} ---\n"` | Preserves page boundaries — useful for citation/source-attribution features |

Chose `"\n"` because:

- DOC-3 is about getting the text into the DB. Downstream LLM
  tickets (DOC-4 summarisation) typically re-chunk the text anyway,
  using their own boundary heuristics.
- Page markers would be premature — we don't have a feature yet that
  cares *which* page a piece of text came from.

When a citation/source-attribution feature arrives, revisit this and
switch to page markers or store pages as a separate column/table.

## Why `tuple[str, int]` and not a `NamedTuple` / dataclass

A `NamedTuple` (or small dataclass) would read slightly nicer at the
call site:

```python
result = extract_text(path)
doc.text_content = result.text
doc.page_count = result.page_count
```

versus:

```python
text, page_count = extract_text(path)
doc.text_content = text
doc.page_count = page_count
```

Both are fine. Chose the plain tuple because:

- There's exactly one caller today (the route handler).
- Tuple unpacking is idiomatic Python and no less readable at this
  scale.
- Introducing a container type now would be premature abstraction —
  the global CLAUDE.md rule: "Three similar lines is better than a
  premature abstraction."

If a second caller appears, or if we start carrying more than two
fields (per-page text, per-page bbox, etc.), switch to a `NamedTuple`
at that time.

## Why `path: str | Path` (union)

`fitz.open` accepts either. Callers might have:

- A `str` from a config / route (likely).
- A `Path` from a test or a service that reasoned about the path with
  `pathlib`.

Accepting both means no `str(path)` dance at any call site. Zero
runtime cost — the union is pure type hint.

## Why synchronous (no `async def`)

PyMuPDF is a synchronous C-library binding. There is no async variant.
FastAPI's route handlers are declared `async def` by default, but
FastAPI runs **sync** dependencies and handlers in a threadpool — so
calling `extract_text` from either an async or sync route is fine.

Wrapping this in `asyncio.to_thread(extract_text, path)` would be
technically more correct *if* the route were declared `async def`.
The route in Step 3 will be plain `def` for simplicity (FastAPI puts
it in a worker thread automatically), so no wrapping is needed.

## `app/services/__init__.py` export

Re-export `extract_text` and `PdfExtractionError` so callers write:

```python
from app.services import extract_text, PdfExtractionError
```

Consistent with how `app/models` and `app/schemas` expose their
members. Intentional and narrow — no wildcard re-exports.

## Verification

After writing:

```
uv run python -c "
from app.services import extract_text, PdfExtractionError
print('imports ok')
"
```

Plus a round-trip using a PyMuPDF-generated PDF (one page, known
text):

```
uv run python -c "
import fitz
from pathlib import Path
from app.services import extract_text

tmp = Path('/tmp/probe.pdf')
doc = fitz.open()
page = doc.new_page()
page.insert_text((72, 72), 'hello from pdf_service test')
doc.save(tmp)
doc.close()

text, pages = extract_text(tmp)
assert 'hello from pdf_service test' in text, text
assert pages == 1, pages
print('round-trip ok; pages=', pages)

tmp.unlink()
"
```

Expected: `round-trip ok; pages= 1`.

Also verify the error path with a non-PDF:

```
uv run python -c "
from pathlib import Path
from app.services import extract_text, PdfExtractionError

fake = Path('/tmp/not-a-pdf.txt')
fake.write_text('hello')
try:
    extract_text(fake)
except PdfExtractionError as exc:
    print('correctly raised:', type(exc).__name__, '| cause:', type(exc.__cause__).__name__)
finally:
    fake.unlink()
"
```

Expected output like: `correctly raised: PdfExtractionError | cause: FileDataError` (exact cause class depends on PyMuPDF version).

## What is deliberately NOT in this step

- The upload route — Step 3.
- Saving the uploaded file to disk — Step 3.
- Creating a Document row — Step 3.
- Any HTTP concern — stays in the route layer.
- Unit tests — a later dedicated test ticket will add `tests/services/test_pdf_service.py`.
- Async wrapper — not needed; route is sync.

## Acceptance for this step

- `app/services/pdf_service.py` exports `extract_text` and
  `PdfExtractionError`.
- `extract_text(valid.pdf)` returns `(str, int)` with correct page
  count.
- `extract_text(nonsense.txt)` raises `PdfExtractionError`, original
  cause preserved via `__cause__`.
- `from app.services import extract_text, PdfExtractionError` works
  (package re-export wired).

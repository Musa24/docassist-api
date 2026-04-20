# DOC-1 · Step 3 — Add dependencies via `uv add`

## Goal of this step

Populate `pyproject.toml` with the project's dependencies, produce
`uv.lock` for reproducible installs, and have `uv` create the project's
`.venv` for us. After this step, `uv run <cmd>` works.

No app code is written yet — that's Step 4.

## Why `uv add` instead of editing `pyproject.toml` by hand

Three things happen when you run `uv add <pkg>`:

1. `uv` resolves the latest compatible version given `requires-python`
   and any existing deps. This is smarter than hard-coding a version.
2. It writes the dep into `pyproject.toml` under `[project.dependencies]`
   with a sensible version spec (e.g. `fastapi>=0.115`).
3. It updates `uv.lock` with the **exact** resolved versions — including
   transitive deps. That lock file is what gives us reproducibility.

Editing `pyproject.toml` by hand skips steps 2 and 3 and leaves us
without a lockfile.

## Runtime vs dev dependencies — why it matters

`pytest` is a testing tool. It's not imported by `app/main.py` in
production. Installing it on a prod server just bloats the image and
gives an attacker more code to poke at.

The modern, PEP 735 way (supported by `uv` natively) is to put dev-only
deps in `[dependency-groups.dev]`:

```toml
[project]
dependencies = [
    "fastapi>=0.115",
    # ... other runtime deps
]

[dependency-groups]
dev = [
    "pytest>=8",
]
```

In deployment:
- `uv sync` in dev → installs everything (runtime + dev).
- `uv sync --no-dev` in prod / Docker → installs only runtime.

This is why we split the two `uv add` calls, even though the ticket
groups them.

## The commands

### Runtime deps — one call

```
uv add fastapi uvicorn sqlalchemy pydantic pydantic-settings \
       python-multipart anthropic pymupdf httpx
```

All nine in a single call so `uv`'s resolver sees them together and
picks mutually compatible versions. Running them one at a time can
cause avoidable re-resolution churn.

### Dev deps — second call

```
uv add --dev pytest
```

`--dev` is the short flag that puts `pytest` into
`[dependency-groups.dev]`.

## What each dependency is for (short version)

**Runtime:**

| Package | Purpose |
|---|---|
| `fastapi` | Web framework — the API itself |
| `uvicorn` | ASGI server that runs FastAPI in dev/prod |
| `sqlalchemy` | ORM for the database layer (`app/database.py`) |
| `pydantic` | Data validation (transitive of FastAPI, but pinning explicitly protects us) |
| `pydantic-settings` | Env-var based `Settings` class (`app/config.py`) — user CLAUDE.md mandates this pattern |
| `python-multipart` | Needed for FastAPI to accept multipart file uploads (PDFs) |
| `anthropic` | Claude API client — DocAssist's core AI calls |
| `pymupdf` | PDF parsing (extracting text from uploaded documents) |
| `httpx` | Async HTTP client. FastAPI's `TestClient` uses it under the hood, and we'll use it for any outbound HTTP from the service |

**Dev:**

| Package | Purpose |
|---|---|
| `pytest` | Test framework. The global CLAUDE.md mandates it |

## What gets created / changed

- `pyproject.toml` gains `[project.dependencies]` entries and a
  `[dependency-groups]` table with `dev`.
- `uv.lock` is created (first time). This is **committed** — the ticket
  requires it, and that's industry-standard for apps (libraries are
  different).
- `.venv/` is created by `uv`. It's **not** committed (`.gitignore`
  from Step 1 blocks it).

## What we will verify after

1. `cat pyproject.toml` — deps and dev-deps present, versions look
   reasonable, Python 3.12 still pinned.
2. `uv.lock` exists at repo root.
3. `uv run python -c "import fastapi, sqlalchemy, anthropic, pymupdf, httpx"`
   imports without error.
4. `git status` shows `pyproject.toml` changed and `uv.lock` untracked
   — `.venv/` should **not** appear (if it does, `.gitignore` has a
   bug and we fix it before moving on).

## What is deliberately NOT in this step

- `app/`, `tests/`, `uploads/` trees → Step 4
- Any Python source → Step 4
- Committing → Step 5

## Acceptance for this step

- Runtime deps present in `[project.dependencies]`.
- `pytest` under `[dependency-groups.dev]`.
- `uv.lock` exists.
- `.venv/` exists but is git-ignored.
- `uv run python -c "import fastapi"` succeeds.
- No commits made.

## Small deviation from the ticket, flagged

The ticket text lists `pytest` inside the same bullet as runtime deps.
This step puts it under `--dev` instead (PEP 735 dev group) for the
production-hygiene reason above. The package is still installed and
usable locally — it's just tagged as dev-only so prod installs can
skip it.

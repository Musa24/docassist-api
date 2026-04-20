# DocAssist API — Implementation Plan

Running log of completed and in-progress tickets. Updated at the end of
each ticket before opening its PR. Newest first.

---

## DOC-1 — Initialize backend repo and project scaffold

**Status:** Complete — ready for PR
**Branch:** feature/DOC-001-project-scaffold
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
- Push branch to origin
- Open PR against main
- Move DOC-1 to "In Review"

---

<!-- Future tickets append new top sections above this line -->

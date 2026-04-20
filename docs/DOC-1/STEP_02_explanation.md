# DOC-1 · Step 2 — `uv init` (create `pyproject.toml`)

## Goal of this step

Generate the project's `pyproject.toml` using `uv`, so that:
- The project has a canonical Python package config file.
- `uv` picks up `3.12` from `.python-version` (written in Step 1).
- Step 3 can start adding dependencies into `[project.dependencies]` via
  `uv add`, instead of us hand-editing the file.

No dependencies are added in this step. No app code is written. Just the
minimal `pyproject.toml` scaffold.

## Why `uv` (and not plain pip / poetry / hatch)

The global CLAUDE.md mandates `uv` as the package manager (fast, lockfile-
based, handles Python version management). Every later step uses `uv run` /
`uv add` / `uv sync`, so `uv init` has to come first to produce the file
those commands read from.

## Why this is its own step, separate from Step 3

Two reasons to split init from adding deps:

1. `uv init` produces a few files by default (`pyproject.toml`, a README, a
   sample `hello.py` / `main.py`). We want to inspect what it generates and
   clean up anything we don't want **before** we start adding dependencies
   and churning `uv.lock`.
2. If Step 3 fails (e.g., a dep name is wrong, network issue), we want to
   fail on the `uv add` step — not mixed together with `uv init` — so the
   error is isolated and easy to retry.

## The command

```
uv init --name docassist-api
```

What the flags mean:
- `--name docassist-api` — sets the project name in `pyproject.toml` to
  match the ticket / GitHub repo. Without this, `uv` would use the folder
  name (`DocAssist`), which doesn't match the repo.

No `--package` flag: this is an application (runs `uvicorn app.main:app`),
not a library we publish to PyPI. `uv init` defaults to app style, which is
what we want.

No `--python 3.12` flag: `uv` reads `.python-version` from Step 1
automatically. Passing it would be redundant.

## What `uv init` generates (expected)

On current `uv` versions, `uv init` typically creates:

- `pyproject.toml` — keep and edit over time.
- `README.md` — keep (useful; Step 5 commit references the repo README).
- `main.py` (or `hello.py`) — **delete**. This would clash with
  `app/main.py` we create in Step 4, and we don't want a top-level
  `main.py` competing with the package entry point.
- `.python-version` — `uv` may try to (re-)write this. We already wrote
  `3.12` in Step 1; if `uv` overwrites it identically, fine. If it writes
  a different version, we reset it to `3.12`.

We will **not** let `uv init` run `uv sync` or create `.venv` yet — the
`.venv` gets created lazily when Step 3 runs `uv add`. Keeping Step 2 to
"just the config file" keeps the diff small and reviewable.

## Post-init cleanup

After running `uv init`:

1. Delete `main.py` (or `hello.py`) if present at project root.
2. Verify `pyproject.toml`:
   - `name = "docassist-api"`
   - `requires-python = ">=3.12"` (or similar — `uv` picks the lower
     bound from `.python-version`)
   - `[project.dependencies]` is empty (deps come in Step 3)
3. Verify `.python-version` still reads `3.12`.
4. `git status` should show new untracked files (`pyproject.toml`,
   `README.md` if new). Still no commits — first commit is Step 5.

## What is deliberately NOT in this step

- Adding any dependencies → Step 3
- Creating `app/`, `tests/`, `uploads/` → Step 4
- Writing any Python source code → Step 4
- `uv sync` / creating `.venv` → happens implicitly when Step 3 runs `uv add`
- Committing → Step 5

## Acceptance for this step

- `pyproject.toml` exists at repo root.
- `name = "docassist-api"` inside it.
- `requires-python` reflects 3.12.
- No stray top-level `main.py` / `hello.py` left behind.
- `.python-version` still pinned to `3.12`.
- No commits made.

# DOC-1 · Step 1 — Git init, feature branch, `.gitignore`, `.python-version`

## Goal of this step

Get the working directory under version control with the right ignore rules
and a pinned Python version, on a feature branch, pointed at the GitHub remote
`https://github.com/Musa24/docassist-api.git`. No Python code, no dependencies,
no project tree yet — that comes in later steps.

## Why this is Step 1 (and not combined with anything else)

Every later step writes files. If we ran `uv init` or created `uploads/`
before `.gitignore` existed, those paths would be tracked by default. Putting
ignore rules in place *first* means the very first `git status` is already
clean of noise (`.venv/`, `__pycache__/`, uploaded PDFs, `.env`, etc.), and we
can't accidentally commit them later.

Similarly, pinning the Python version up front means when `uv` creates its
virtualenv in Step 2, it uses the version we want — not whatever happens to
be the interpreter default.

## What will happen

### 1. `git init`

Turns this directory into a git repo. Local only — nothing pushed yet.

### 2. Feature branch

Rename the default branch to `feature/DOC-001-project-scaffold` (the ticket
requires work to be done on this branch). We do this *before* any commits
exist so the initial commit lands on the feature branch directly, not on
`main`/`master`.

### 3. Add `origin` remote

Point the repo at `https://github.com/Musa24/docassist-api.git`. We don't
push in this step — push happens after Step 5's commit, and only when you say
so.

### 4. `.gitignore`

A Python-focused ignore file. The entries and their reasons:

| Pattern | Reason |
|---|---|
| `__pycache__/`, `*.py[cod]`, `*$py.class` | Python bytecode, regenerated on every run |
| `.venv/`, `venv/`, `env/` | Virtualenvs — `uv` creates `.venv` by default |
| `.env`, `.env.*` (except `.env.example`) | Secrets never get committed |
| `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/` | Tool caches |
| `*.egg-info/`, `build/`, `dist/` | Python packaging artifacts |
| `.DS_Store` | macOS Finder metadata |
| `.idea/`, `.vscode/` | IDE settings (personal, not project) |
| `uploads/*` and `!uploads/.gitkeep` | Ignore uploaded PDFs, keep the folder tracked via `.gitkeep` (added in Step 4) |
| `*.db`, `*.sqlite`, `*.sqlite3` | Local SQLite files — not shared between dev environments |

Note: `uv.lock` is **not** ignored. The ticket requires it to be committed
(that's how reproducible installs work across machines).

### 5. `.python-version`

One line: `3.12`. Tools that read this file (including `uv`) will
automatically use Python 3.12 for this project without us having to pass
`--python 3.12` to every command.

## What is deliberately NOT in this step

- `pyproject.toml` → Step 2
- Any dependencies → Step 3
- `app/`, `tests/`, `uploads/` trees → Step 4
- The first commit → Step 5

## Acceptance for this step

- `git status` works (repo initialized)
- Current branch is `feature/DOC-001-project-scaffold`
- `git remote -v` shows `origin` pointing at the GitHub URL
- `.gitignore` and `.python-version` exist at repo root
- No commits yet — we stage and commit only at Step 5

## Commands that will run (for reference, not executed yet)

```
git init
git symbolic-ref HEAD refs/heads/feature/DOC-001-project-scaffold
git remote add origin https://github.com/Musa24/docassist-api.git
# then: write .gitignore and .python-version via the editor, not the shell
```

Using `git symbolic-ref` instead of `git branch -m` because the repo has no
commits yet — there's no branch to rename, only `HEAD` to point.

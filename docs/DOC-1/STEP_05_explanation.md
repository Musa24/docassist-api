# DOC-1 · Step 5 — First commit on `feature/DOC-001-project-scaffold`

## Goal of this step

Land the scaffold as a single atomic commit on the ticket's required
branch, with a commit message that starts with the ticket key (as the
ticket demands). No push — that is a separate decision you confirm after
the commit is clean locally.

## Why one commit and not many

User CLAUDE.md: "Small, atomic commits — one logical change per commit."
The entire ticket is *one* logical change: "scaffold the backend repo".
Splitting it into five commits (one per step we did) wouldn't improve
`git log` readability — it would flood it with half-built states. Each
of those intermediate states couldn't even boot the app, so none of
them are useful to bisect back to. One commit is the honest unit of
review here.

## Why `git add <files>`, not `git add .` / `git add -A`

User CLAUDE.md:

> When staging files, prefer adding specific files by name rather than
> using "git add -A" or "git add .", which can accidentally include
> sensitive files (.env, credentials) or large binaries.

We list each path explicitly. If anything stray is on disk (a renamed
file, a local experiment), it won't slip into this commit.

## The paths we stage

```
.gitignore
.python-version
README.md
pyproject.toml
uv.lock
app/
tests/
uploads/.gitkeep
docs/
```

Reasons per item:

- `.gitignore`, `.python-version` — Step 1
- `README.md`, `pyproject.toml` — Step 2 (readme is empty, still worth
  tracking so later tickets edit it instead of creating it)
- `uv.lock` — Step 3 (ticket mandates commit; reproducibility)
- `app/`, `tests/`, `uploads/.gitkeep` — Step 4
- `docs/` — the four `STEP_0*_explanation.md` files we wrote. This
  project's CLAUDE.md defines the Explain-then-Code workflow and puts
  the explanations in `docs/<TICKET>/`, so they are part of the
  deliverable, not scratch work.

## What we deliberately leave out

- `.venv/` — blocked by `.gitignore`, would be large and
  machine-specific.
- Anything inside `uploads/` except `.gitkeep` — blocked by
  `uploads/*` rule.
- Any `__pycache__/` from running the server earlier — blocked.
- The remote repo — no `git push` in this step. Pushing publishes work
  to a remote branch, which is not reversible the same way a local
  commit is. The user confirms push separately.

## The commit message

Ticket requirement: "Commit message references ticket: 'DOC-001: ...'"

Full message (subject + body):

```
DOC-001: initialize backend repo and project scaffold

- Init uv project targeting Python 3.12 (pyproject.toml, uv.lock)
- Add runtime deps: fastapi, uvicorn, sqlalchemy, pydantic,
  pydantic-settings, python-multipart, anthropic, pymupdf, httpx
- Add dev deps: pytest (in PEP 735 dependency-groups.dev)
- Create app/ package with main.py (FastAPI app + /health) and
  empty model/schema/route/service subpackages
- Create tests/ package with empty conftest.py
- Add uploads/.gitkeep; .gitignore keeps real uploads out
- Python-focused .gitignore; .python-version pinned to 3.12
```

Subject line notes:
- Starts with the ticket key — acceptance criterion.
- Under ~72 chars — fits in `git log --oneline` and GitHub's PR view
  without truncation.
- Imperative mood ("initialize"), matches the convention in user
  CLAUDE.md ("docs", "fix", "feat" — all imperative).

Body notes:
- Bullet list, each line ≤ ~72 chars.
- Explains *what* was scaffolded (the body answers "what's in this
  commit?"). The *why* — why scaffold now — is in the Jira ticket
  itself; the commit links to the ticket via `DOC-001:`.
- No trailer lines (no `Co-Authored-By:`, no `Signed-off-by:`) —
  those are added by project policy if needed; the ticket doesn't
  require them.

## How this step will be executed

```
git add .gitignore .python-version README.md pyproject.toml uv.lock \
        app/ tests/ uploads/.gitkeep docs/
git commit -F <heredoc with full message>
git log -1 --stat   # verify
```

Using heredoc for the commit message (via `-F -` or `-m "$(cat<<EOF)"`)
rather than a single `-m` string keeps newlines intact for the bullet
body.

## What we verify after

1. `git log -1` shows the commit, subject starts with `DOC-001:`.
2. `git status` is clean (`nothing to commit, working tree clean`),
   aside from any still-ignored `.venv/` which does not appear in
   status anyway.
3. `git log --stat -1` shows all nine expected paths touched.

## What comes next (not this step)

After this commit:

- **Push decision.** `git push -u origin feature/DOC-001-project-scaffold`
  — I'll ask before running it. Push publishes the branch; once pushed,
  force-push or branch deletion become the only ways to undo.
- **PR decision.** Separately after push: open a PR on GitHub against
  `main`. I'll ask first.
- **Jira transition.** DOC-1 can move from "To Do" to "In Progress" or
  "In Review". I'll ask before touching the ticket status.

## Acceptance for this step

- Exactly one new commit on `feature/DOC-001-project-scaffold`.
- Subject starts with `DOC-001:`.
- `git status` clean.
- All acceptance items from DOC-1 satisfied in the committed tree.

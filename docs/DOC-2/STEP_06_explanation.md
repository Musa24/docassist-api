# DOC-2 · Step 6 — Update PLAN.md, commit, push, PR, Jira transition

## Goal

Close DOC-2 cleanly: capture the outcome in `docs/PLAN.md`, land the
work as a single atomic commit on the feature branch, push, open a PR
against `main`, and transition Jira. Merge itself pauses for your
approval in a later round.

## Step 6 sub-actions (in order)

### 1. Update `docs/PLAN.md`

Prepend a new DOC-2 section at the **top** of the file (above the
`<!-- Future tickets append new top sections above this line -->`
marker). Do not touch existing sections.

The new section mirrors DOC-1's shape: heading, status/branch/Jira,
what-we-did checklist, acceptance criteria (ticked only for what was
actually done), deviations, verification, and next steps.

Per the authoritative rule in `docassist-api/CLAUDE.md`:

> Do **not** open the PR until `docs/PLAN.md` reflects the final state
> of the ticket.

So PLAN.md is committed **before** the PR is created.

### 2. Delete the local SQLite file

```
rm docassist.db
```

It's already git-ignored via `*.db`, so this is cosmetic — but it:

- Keeps the working tree tidy at commit time (no mystery files sitting
  around).
- Doubles as a sanity check that the scaffold regenerates the table
  cleanly on the next boot.

Skip this if you'd rather keep the local file. Either way, it cannot
end up in the commit.

### 3. Stage files explicitly

No `git add -A` / `git add .` (user CLAUDE.md rule). The explicit list:

```
app/database.py
app/main.py
app/models/__init__.py
app/models/document.py
app/schemas/__init__.py
app/schemas/document.py
docs/DOC-2/
docs/PLAN.md
```

### 4. One atomic commit

One logical change ("DB connection + Document model + schemas +
create_all wiring") → one commit. Ticket-prefixed subject
(`DOC-002: ...`) to satisfy the acceptance criterion.

Commit message (heredoc):

```
DOC-002: add database connection and Document model

- app/database.py: SQLAlchemy 2.x engine (sqlite), SessionLocal,
  DeclarativeBase, get_db FastAPI dependency.
- app/models/document.py: Document ORM model with 10 fields,
  Mapped/mapped_column typed style, DB-side timestamps via
  server_default=func.now() / onupdate=func.now().
- app/schemas/document.py: Pydantic v2 DocumentResponse (full detail)
  and DocumentSummary (list view), both with
  ConfigDict(from_attributes=True).
- app/main.py: imports Document for Base.metadata registration side
  effect; calls Base.metadata.create_all(engine) on module load.
- .gitignore already covers docassist.db via *.db (verified with
  git check-ignore); no redundant line added.
```

### 5. Push the feature branch

```
git push -u origin feature/DOC-002-database-model
```

`-u` sets the upstream so future `git push` / `git pull` work
without an explicit ref. First time we push this branch, so the
remote gets created.

### 6. Open the PR

```
gh pr create --base main --head feature/DOC-002-database-model \
  --title "DOC-2: Database connection and Document model" \
  --body "<heredoc with Summary / What changed / Test plan / PLAN.md link>"
```

Body structure (matches project convention from `init` / existing
template):

- **Summary** — 2-3 bullets, what this PR adds.
- **What changed** — file-by-file. Reviewer's map.
- **Test plan** — the verification commands from Step 5, plus any
  new post-merge checks.
- **Planning log** — link to the DOC-2 section in `docs/PLAN.md` so a
  reviewer can read the ticket context without opening Jira.

**Title ≤ 70 chars** so `git log --oneline` and GitHub's PR list stay
readable.

### 7. Transition DOC-2 in Jira to "In Progress"

Three states available: To Do / In Progress / Done. While the PR is
open, "In Progress" is the honest status — the work is mid-flight.
Moving to Done on PR *creation* (some teams do this) misrepresents
state; Done means merged and working in main.

### 8. Stop

Step 6 stops after the Jira transition. Merge itself is a separate
decision in a later round:

- You review the PR.
- On your go-ahead, `gh pr merge --squash` collapses the feature
  branch into a single commit on `main`, deletes the remote feature
  branch, and I'll transition DOC-2 → Done, sync local `main`, delete
  the local feature branch.
- Until then, Jira stays In Progress.

## Why squash (default) for the merge

Three merge methods GitHub offers:

| Method | History | Our case |
|---|---|---|
| `--merge` | Preserves feature commits + adds a merge commit | Noise — we have 1 feature commit; merge commit adds nothing |
| `--squash` | Collapses all feature commits into one on main | 1 clean `DOC-002: ...` commit on main |
| `--rebase` | Replays feature commits onto main linearly | Same as squash here (we have 1 commit anyway) |

For multi-commit feature branches, squash produces the cleanest `main`
history. For this PR (one commit), squash and rebase are
interchangeable. Squash is our default.

## What is deliberately NOT in this step

- The actual merge — paused for your approval.
- Syncing / deleting local branches — happens post-merge.
- Any new ticket work — DOC-3 starts in a new session branch.

## Acceptance for this step

- `docs/PLAN.md` prepended with a DOC-2 section above the HTML marker.
- Single new commit on `feature/DOC-002-database-model` whose subject
  starts with `DOC-002:`.
- Branch pushed to `origin`.
- PR open against `main` with title, body, and PLAN.md link.
- Jira DOC-2 status = "In Progress".
- Local workdir clean; `docassist.db` deleted (cosmetic); server still
  boots if we re-run.

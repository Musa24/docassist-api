# DOC-2 · Step 1 — Create feature branch

## Goal

Branch off `main` onto `feature/DOC-002-database-model` before any
files are written, so that everything DOC-2 produces is isolated from
`main` and reviewable as a single unit in Step 6.

## The command

```
git switch -c feature/DOC-002-database-model
```

`-c` creates-and-checks-out a new branch. We run this from `main` (current
HEAD), so the new branch starts from the scaffold's HEAD commit
`d001a6a`.

`git switch` is the modern replacement for the historically overloaded
`git checkout -b`. Same effect, clearer intent (`switch` for branches,
`restore` for files).

## Why before any other step

If we skipped this and wrote `app/database.py` straight onto `main`:

- `main` would contain half-written, un-reviewed work.
- Rolling back would require `git reset` / `git restore`, which is
  noisier than `git switch main && git branch -D feature/...`.
- It would violate the ticket's "work done on branch" acceptance
  criterion.

## Why no push yet

Pushing creates `origin/feature/DOC-002-database-model` on GitHub and
starts a visible state. We push only at Step 6 when there's a complete,
reviewable diff. Between Steps 1–5, the branch lives only on this
machine — cheap to discard if we change direction.

## Verification

After the command:

- `git branch --show-current` prints `feature/DOC-002-database-model`.
- `git log --oneline` shows the same two commits from DOC-1 (no new
  ones — we only switched branches).
- `git status` is clean (no uncommitted work).

## Acceptance for this step

- Current branch = `feature/DOC-002-database-model`.
- Branch starts at `main`'s HEAD.
- No files created, modified, or staged.
- Remote untouched (branch is local-only).

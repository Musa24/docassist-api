# DocAssist API — Claude Code rules

FastAPI backend for DocAssist (document Q&A over uploaded PDFs using
Claude). Python 3.12, managed with `uv`.

## Ticket Workflow (Explain-then-Code)

Implement Jira tickets one chunk at a time:

1. Announce the chunk (file, purpose, why now).
2. Wait for explicit approval.
3. Write an explanation doc first at `docs/<TICKET>/STEP_NN_explanation.md`.
4. Wait for approval of the explanation.
5. Only then write code for that chunk.
6. Pause, announce the next chunk, repeat.

Never combine steps. Never write code before the explanation is approved.

## Per-ticket planning log — MUST UPDATE at end of every ticket

`docs/PLAN.md` is a single running log across **all** tickets (newest
first). It is the deliverable that accompanies each PR.

**Mandatory update at the end of every ticket, before opening its PR:**

1. Prepend a new section at the top of `docs/PLAN.md` (above the HTML
   comment marker) for the ticket just finished. Never overwrite or
   reorder previous ticket sections.
2. Each ticket section contains:
   - Heading: `## <TICKET-KEY> — <ticket summary>`
   - **Status** (Complete / In progress / Blocked), **Branch**, **Jira link**
   - **What we did** — checklist of the step-by-step chunks. Use `[x]`
     for finished, `[ ]` for attempted-but-not-finished. Do **not** tick
     items that were not actually done.
   - **Acceptance criteria (from ticket)** — copy the ticket's acceptance
     list verbatim; tick `[x]` only what is genuinely met.
   - **Deviations from ticket** — any deliberate divergence, with reason.
   - **Verification** — concrete evidence (commands run, outputs).
   - **Next** — push, PR, Jira transition, follow-up tickets.
3. Do **not** open the PR until `docs/PLAN.md` reflects the final state
   of the ticket. The PR description for each ticket should link back to
   its section in `docs/PLAN.md`.

`docs/<TICKET>/STEP_NN_explanation.md` files complement `PLAN.md` — they
capture the reasoning *during* the work; `PLAN.md` captures the summary
*after* the work.

## Running locally

- `uv sync` — install deps (including dev group).
- `uv run uvicorn app.main:app --reload` — dev server.
- `uv run pytest` — test suite.

## Branch and commit conventions

- Branches: `feature/<TICKET-KEY>-short-slug` (e.g. `feature/DOC-002-pdf-upload`).
- Commit subject must start with the ticket key: `DOC-002: ...`.
- Small atomic commits — one logical change per commit.
- Stage files explicitly; avoid `git add -A` / `git add .`.
- Never push without explicit user confirmation.

# Writing a plan file

Plans go in `.agents/plans/`. One plan is one session's worth of work for
one agent. If the work is bigger than that, split it: `<feature>-00-overview.md`
for the shared context, then `<feature>-01-...`, `-02-...` for each chunk.
Every chunk must stand on its own given the overview, because the
implementer reads the overview plus their one plan and nothing else.

## Write for a reader who will disagree with you

The implementer is told to believe the code over the plan
(see [`implementing-plans.md`](implementing-plans.md)).
Write so they can tell *which* parts to push back on:

- **Mark how you know each claim.** Say plainly when something is a
  proposal versus **verified by experiment on this machine** — and for the
  latter, include the command and its output so it can be re-run.
- **Mark decisions the user made** as such ("the user chose X"). Those are
  not up for renegotiation, and only you can label them.
- **Say why, not just what.** A step whose reason is recorded can be
  adapted when the code disagrees; a bare instruction can only be followed
  or abandoned.
- **Don't invent precision you don't have.** Guessing at exact file paths,
  function names, or line numbers reads as researched fact. Either check
  it or say it's a guess.

## Required sections

- **Context** — what problem this solves, and what the reader needs to know
  that isn't obvious from the code.
- **The work** — the steps, in an order that keeps the suite green if possible.
- **Done when** — acceptance criteria. This is what the implementer checks
  themselves against. Include any manual verification that a test can't
  cover, and say what a passing result looks like.

## Keep it short

A plan is a briefing, not a specification. Link to code and to the guides
in `.agents/docs/` instead of restating them, and leave out anything the
implementer can read off the codebase faster than off your prose.

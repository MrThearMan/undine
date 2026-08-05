# Working from a plan file

Plans live in `.agents/plans/`. A multi-plan feature has an overview
(`<feature>-00-overview.md`) holding the shared context, plus one file
per chunk of work. **Read the overview plus the one plan you're
executing — not the other files.** They're sized so a single plan is one
session's worth of work.

## Plans are evidence, not orders

**The codebase wins. If reality contradicts a plan, follow reality and change the plan.**

A plan is written from research and reasoning, by someone who had not
yet built the thing. Some of it is wrong. Expect to find errors in the
parts nobody has exercised yet — that is normal, not a sign the plan was
bad or that you have misunderstood it.

So when the code disagrees with the plan:

- **Believe the code**, and prefer a quick experiment over an argument from the plan.
- **Don't contort an implementation to satisfy a plan step.** If a step
  is awkward to implement, that's evidence the step is wrong. If a named
  function, field, or file doesn't fit where the code actually is,
  rename or relocate it.
- **Don't get stuck.** A plan step that can't be made to work is not a
  blocker to escalate — it's a finding. Solve the underlying problem and
  note what changed.
- **Update the plan file in the same commit** as the code that
  contradicted it, and say *why* in a sentence, marked so a later reader
  can tell it apart from the original text (`**Corrected during
  implementation.**` reads well). The next agent reads the plan, not the
  conversation that produced it. A plan that quietly diverged from the
  code is worse than no plan.
- **Tell the user** in your summary when you deviated on anything load-bearing.

## What is not up for renegotiation

Two things are *not* engineering judgement, and changing them needs the user:

- **Decisions the user settled.** A plan that records "the user chose X" is reporting a preference,
  not a technical constraint. Implement X or ask.
- **The house rules in [`AGENTS.md`](../../AGENTS.md)** and the detailed guides it links to.

## What to trust over your instincts

A plan section that says its claims were **verified by experiment on
this machine** outranks reasoning, including yours. If you think you've
contradicted one, re-run the experiment before concluding the plan is
wrong. If the experiment agrees with you, update the section and say so.

Everything else in a plan — file layouts, function names, orderings,
edge cases — is a proposal.

## Finishing

A plan's "Done when" list is the acceptance criteria. Manual
verification steps are there because a unit test can't prove the thing
they prove; do them, and report the result rather than assuming.

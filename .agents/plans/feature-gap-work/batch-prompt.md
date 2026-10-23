You are working in the Undine repository at /home/matti/Projects/undine. Undine is a batteries-included GraphQL library for Django.

Context: we researched 47 GraphQL frameworks. Each has a findings file in .agents/plans/findings/<name>.md. This step compares the findings against Undine and lists features Undine could implement.

Inputs:
- .agents/plans/feature-gap-work/undine-inventory.md: what Undine offers today. Read it fully first.
- CONTEXT.md in the repo root: Undine's domain language.
- The findings files for your batch (listed below). Read each one fully.

Task: for every feature in your batch's findings, decide if Undine already has it. If Undine does not have it, or has only part of it, add it as a candidate. When the inventory is unclear, check the Undine source (undine/) and docs (docs/) with grep before you decide. Do not list a feature as missing if Undine has it under another name.

Include features even if they seem a weak fit. Use the "Fit" column to say how well they fit a Django GraphQL library. Skip only features that are clearly language-specific mechanics with no meaning in Python (for example, Rust macro syntax or Java annotation processing details).

Output: write to .agents/plans/feature-gap-work/candidates-<N>.md. Write after each findings file, so work survives an interruption. Use this format, grouped under "## <Area>" headings (use the same area names as the inventory where possible):

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |

- "Feature": a short neutral name.
- "What it does": one short sentence.
- "Seen in": framework name plus the real API name, for example `strawberry-django: strawberry_django.mutations.create`. If several frameworks in your batch have it, put them all in one row.
- "Undine today": `missing` or `partial: <what exists>`.
- "Fit": `high`, `medium` or `low`, with a few words of reason in Notes.
- "Notes": short. Say "I think" when you did not verify a claim in the Undine code.

Rules:
- Do NOT start any subagents.
- Do not modify any file in the repository except your output file. Do not touch other files in feature-gap-work/.
- Do not run git write commands. Do not delete anything.
- Write in short, simple sentences. Do not use em dashes or semicolons.
- When finished, reply with a short summary: the number of candidate rows (count them with grep, do not estimate) and the 5 to 10 candidates you think matter most.

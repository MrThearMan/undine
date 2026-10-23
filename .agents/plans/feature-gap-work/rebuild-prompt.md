Your job is to recover a lost file from a subagent session transcript.

A previous subagent wrote the file /tmp/undine-gap/candidates-<N>.md. A reboot erased /tmp, so the file is gone. The transcript path and N are given in your task message. The transcript is a JSONL file. Each line is one message. The lines are long.

Steps:
1. If the Skill tool has an `excavate-transcript` skill, load it first and follow its guidance.
2. Write a python3 -I script outside the repo, in /tmp/rebuild-scripts/. It reads every line of the transcript, in order, and finds every tool call that changed /tmp/undine-gap/candidates-<N>.md. This includes Write, Edit (with or without replace_all), MultiEdit, and Bash commands that wrote to it (heredocs with any delimiter, `cat >`, `cat >>`, `tee`, relative paths after `cd /tmp/undine-gap`, python scripts, sed -i).
3. Replay those changes in the same order, to the new path:
   /home/matti/Projects/undine/.agents/plans/feature-gap-work/candidates-<N>.md
   Take the exact strings from the JSONL. Do not retype anything by hand.
   Also check each tool call's result in the transcript. If the original call failed (for example an Edit whose old_string was not found), do not replay it.
4. Completeness check: separately list every tool call whose input mentions `candidates-<N>` or `/tmp/undine-gap`. For each one, say if it was replayed, or why it does not change the file (read-only, other file). If any call changed the file and cannot be replayed exactly, stop and report it. Do not guess.
5. Verify the result. Compare against any later Read, cat, wc or grep output of the file inside the transcript. Report the final line count and whether it matches the last state the transcript shows.

Rules:
- Do NOT start any subagents.
- Do not modify any other file in the repository. Do not run git write commands. Do not delete anything.
- Write in short, simple sentences. Do not use em dashes or semicolons.
- Reply with: the replayed tool calls (count and kind), the completeness list in short form, any problem, the final line count, and how you verified it.

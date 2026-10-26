## Check 3 (contain) counters orthogonal damage

Models change or remove comments and code they don't fully understand, as side effects, even when
that code has nothing to do with the task (Karpathy, 2026).

- **The diff contains only what the interpretation named.** The diff may grow, but name each
  addition in the interpretation first. Only growth you didn't name first is banned.
- **Touch only what you know the reason for.** Comments, error handling, imports, names and
  formatting stay when you don't know why they are there.
- **Write down unrelated problems you notice, and never fix them in this diff.** They go in the
  Reply and the merge commit's message, and nowhere else, in attended and unattended runs alike
  (`references/judgment.md`, The five buckets). pstack's orchestrate:
  "Mid-run discoveries fix only what blocks the frontier. Everything else parks in follow-ups."
  (pstack, `skills/poteto-mode/playbooks/orchestrate.md`, l. 109) A problem that blocks this
  change is not unrelated. Name it in the interpretation, and fix it in a diff of its own.
  pstack's autonomous-run makes every mid-run discovery the run's own work, "Mid-run discoveries
  are yours" (pstack, `skills/poteto-mode/playbooks/autonomous-run.md`, l. 9). *(kstack: here that
  holds only for a blocking one, so one rule covers every run.)*
- **Never restructure and change behaviour in the same diff.** A study measures more bugs in
  restructuring done alongside other changes, and the bugs appear as soon as the first later
  change touches the restructured code (Ferreira et al., 2018). Make two diffs, the subtraction
  first (pstack, `skills/poteto-mode/playbooks/refactoring.md`, l. 14). When a cleanup turns up
  the behaviour change, the structural diff ships first (`references/refactor.md`).

**Satisfied when** every hunk of the diff traces to an item the interpretation named, and every
unrelated problem you noticed is written down outside the diff.

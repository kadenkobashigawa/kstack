# Queue

Proven findings that would not block a real PR, waiting for a change of their own. The gate files
each one here right after the merge (`skills/build/references/judgment.md`,
queue). An unattended build run takes the worst item that still holds as its one task, and its
fix deletes the line (`skills/build/references/long-run.md`, When no task is handed over).

One line per item: what is wrong, where, and the commit it was found at.

- A retired skill whose folder lingers with git-ignored files (`__pycache__/`, `.DS_Store`) keeps
  its live link in `~/.claude/skills`, and install.sh's closing count includes it.
  `hooks/install.py` (`prune`, `live`). Found at 2fadb9d.
- write-report: `references/design.md` restates `theme.css`'s values with nothing checking they
  agree, and `report.py` builds figure markup that belongs in `theme.py`.
  `skills/write-report/`. Found at 3d6320b.
- write-report: a link in a `##` or `####` heading prints as literal text; a report with no chapter
  is accepted; more than 26 appendices run past Z. `skills/write-report/scripts/`. Found at 222157e.
- write-report tests: S1's temp-folder check fails when another render runs at the same time, and
  the L1 leak check scans git-ignored files such as `.ruff_cache`.
  `skills/write-report/tests/test_report.py`. Found at 8c284d5.

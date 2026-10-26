# upstream

These folders are imported unmodified, each with its own MIT license:

- `pstack` by Lauren Tan, and `cursor-team-kit`, `continual-learning`, `ralph-loop` and
  `orchestrate` by Cursor, from [cursor/plugins](https://github.com/cursor/plugins) at commit
  `ccb5507` (2026-10-07).
- `mattpocock-skills` by Matt Pocock, from [mattpocock/skills](https://github.com/mattpocock/skills)
  at commit `5beb35b` (2026-10-19). Only part of that repository is here, at its original paths: the
  improve-codebase-architecture skill, the codebase-design, grilling and domain-modeling skills it
  calls, grill-me (a one-line wrapper around grilling), their docs pages, the two out-of-scope notes
  on how grilling asks its questions, and the repository's README and LICENSE.

kstack's skills adapt parts of them, and each adapted skill names its source in its own files. They
are kept here so every adaptation can be compared with the original, and so a part set aside for
later is ported from the source rather than rewritten from memory.

## Parked, and what would bring each back

| Part | Bring it back when |
|---|---|
| hillclimb | a single metric needs pushing over many iterations |
| eval | skill changes need blind proof that they change behavior |
| runtime-forensics, trace-forensics | there's a live leak or spin, or a captured profile to read |
| arena | a second model family becomes reachable from Claude Code |
| benny | bug reports start arriving from outside (Slack, users) |
| visual-parity | a styling-system migration needs pixel-exact equivalence |
| control-cli | an interactive command-line tool needs driving |
| grilling, grill-me | an interview is wanted outside an architecture review |

## Left out

- The always-on router (`poteto-mode`) and model routing.
- The pull-request and stacked-PR machinery, since kstack merges locally. autopilot-full's review
  and merge rule live on in build's `references/gate.md`.
- The comment strippers, which delete required docstrings.
- pstack's teach workflow, whose writing rules `teach` carries. pstack's `unslop` and
  `technical-writing` are carried verbatim as skills of their own.
- The TypeScript and Grok Bot pieces, and the principles kstack's skills already state.

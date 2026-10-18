# upstream

These folders are imported unmodified from [cursor/plugins](https://github.com/cursor/plugins) at
commit `ccb5507` (2026-10-07), each with its own MIT license:

- `pstack` by Lauren Tan
- `cursor-team-kit`, `continual-learning`, `ralph-loop` and `orchestrate` by Cursor

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

## Left out

- The always-on router (`poteto-mode`) and model routing.
- The pull-request and stacked-PR machinery, since kstack merges locally. autopilot-full's review
  and merge rule live on in build's `references/gate.md`.
- The comment strippers, which delete required docstrings.
- pstack's writing and teaching skills that duplicate `teach`.
- The TypeScript and Grok Bot pieces, and the principles kstack's skills already state.

## Check 2 (simplify) counters over-complication

Models overcomplicate code and APIs, bloat abstractions, and leave dead code behind. They write a
thousand lines where a hundred would do (Karpathy, 2026).

Work in this order, because the classic error is simplifying something that should be deleted
(`skills/elon/SKILL.md`, ll. 8–9):

1. **Should this exist? Run `/elon`**, which answers this question. It gives every requirement a
   named owner. Delete a requirement whose owner is "the system" or "good practice" instead of
   building it. Run anything that outputs a design through `/elon`, small ones included.
2. **Can existing code already do this?** Check for reuse before writing, so one decision lives in
   one place (pstack, `skills/principle-laziness-protocol/SKILL.md`, l. 13). If you replace working
   code anyway, name each thing the old code could do that the new code can't. Keep each one, or get
   its loss approved. The person who asked can approve it. The operator's grant is their standing
   permission to merge on a clean gate verdict. Under it, that verdict approves the loss too, if its
   review lanes were told of it. A capability dropped without anyone saying so is a regression
   reported as "done" *(kstack: reasoning, not measurement)*.
3. **Size the change to the code's condition.** Sound code takes the minimal change. When the
   change would sit *on top of* a defect rather than *in* it, make the change at the defect's
   layer. Patching around bad structure is the same error as optimizing a part that should
   have been deleted (pstack, `skills/principle-fix-root-causes/SKILL.md`, l. 9).
4. **No bloat, and code size is the warning sign.** Make the smallest change that solves the problem
   (pstack, `skills/principle-laziness-protocol/SKILL.md`, l. 14). Measure what you wrote against
   what the job needed before you judge it. Then cut any feature beyond the request, any abstraction
   with one call site, any configurability nobody asked for, and any wrapper that only forwards a
   call.
5. **Leave nothing orphaned.** If this change leaves code dead, removing that code is part of
   this change (pstack, `skills/principle-laziness-protocol/SKILL.md`, l. 11;
   `skills/principle-subtract-before-you-add/SKILL.md`, l. 16).

**Satisfied when** the requirement has a named owner, reuse was checked and taken or refused
with a reason, the change sits at the layer its defect lives in, every new abstraction has two
call sites or a written reason, and nothing orphaned remains.

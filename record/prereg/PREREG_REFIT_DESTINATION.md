# PREREG — A DESTINATION FOR THE REBINDING BIN (2026-08-19)

**AUTHORITY: Seat 3, ruling 1 —** *"BROKEN·rebinding is meant to be live. This is a rule, not
a verdict… Order stands as you set it — `refit_queue` needs a destination before the switch is
thrown, because a diagnosis that dies with the process is not a diagnosis. Prereg it, build it
singly, falsifier attached."*

## SCOPE — THE DESTINATION ONLY. THE SWITCH IS NOT THROWN IN THIS BUILD.
`binding_stale` remains unset in production after this change, so **the rebinding bin still
cannot fire.** That is deliberate and it is the ruled order. This build makes the diagnosis
*survivable*; a later, separate build makes it *possible*.

**Which means the expected effect of this change on today's running system is EXACTLY NOTHING,
and that is a stated prediction, not an excuse.** See F2.

## THE DEFECT THIS CLOSES
`engines/egocentric/router.py:70` appends to `self.refit_queue`, an in-memory list
**referenced nowhere else in the tree.** Its two siblings both drain to the fabric:
`import_queue` (NOVEL) at `cognitive_loop.py:1931-1945`, `mint_queue` (BROKEN·mechanism) to
the mint. **The rebinding bin is the only one of the four with no destination**, so its
diagnosis dies with the process.

## THE BUILD — mirror the sibling, do not invent a second pattern
Drain `refit_queue` to the collective stream `refit_queue`, **copying the `import_queue` drain
verbatim in shape**: same `while … pop(0)` loop, same record keys (`slot`, `residual`, `game`,
`level`), same **A3-2 PLAYING-level convention** (`_ego_level + 1`), same
`_wfab.append("collective", …)` call, its **own** `try/except` with its own swallow code so a
refit failure cannot kill the import drain.

*This is the SITE-SCOPED KNOWLEDGE lesson applied to my own hands: the correct pattern already
exists 60 lines away, and the failure mode being avoided is writing a second one.*

## FALSIFIERS — three, and one of them must fail loudly if I am wrong about today
**F1 · IT PERSISTS.** Route a settlement with `binding_stale=True`, run the drain: the record
appears on the collective `refit_queue` stream with `slot`, `residual`, `game`, `level`.
*Fails if:* the stream is absent, empty, or the record loses a field.

**F2 · IT CHANGES NOTHING TODAY — THE PREDICTION THAT CAN EMBARRASS ME.** With `binding_stale`
never set, the drain is a no-op: **no `refit_queue` stream is created in any box, and
`import_queue` / `mint_queue` / `atom_bin` counts are unchanged.** *Fails if:* an empty stream
appears, any sibling count moves, or any gate that passed now fails.

**F3 · KNOWN-NEGATIVE.** A settlement routed `NOVEL` or `BROKEN_MECHANISM` must **not** appear
on the refit stream. *Fails if:* the drain is indiscriminate. **Without F3, F1 would pass on a
drain that copies everything.**

## UNDO
Delete the drain block. The stream is append-only JSONL and no reader exists yet, so nothing
depends on it; readers of other streams ignore an unknown topic. **No schema change, no
migration, nothing destroyed.**

## WHAT THIS DOES NOT CLAIM
It does not fix the routing defect. **It does not make one rebinding record exist.** The 64%
re-derivation rate in the mint ledger is untouched by this and stays untouched until the
switch build. This is the precondition, and it is worth exactly what a precondition is worth.

## LIVE-SYSTEM NOTE
25 workers are running now. Python has already imported the module in each, so **running
workers are unaffected**; the change reaches them at the next recycle (bounded lifetime, 120
min) or restart. F2 is therefore checkable against boxes on both sides of a recycle.

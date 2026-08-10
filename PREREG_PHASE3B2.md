# PRE-REGISTRATION — PHASE 3b2: the click-side economy (credit the acted-on cell)

**Written 2026-08-10 BEFORE the build, at `631bfc8`+log. 3b's trial: a real click-game level-up
produced zero mints because credit requires a self-centroid that click games never have.**

## THE CHANGE THAT IS AUTHORISED
> Credit attribution generalises to THE ACTED-ON CELL: when `level_changed` fires and the last
> action was a click at (x, y), credit/mint `{"kind": "CLICK_AT", "cell": [x, y]}` (no
> self-centroid needed); the movement path (BE_AT via centroid) is unchanged. The spine gains
> the symmetric drive: a CONFIRMED CLICK_AT goal yields `drive_click() -> (x, y) | None` under
> the IDENTICAL wheel rule (confirmed price only; falsified-on-clicked-without-reward closes it
> and pariah-marks); the loop's pre-empt site consults movement-drive first, then click-drive
> (action 6 + coords). Seeding/echo/falsify handle CLICK_AT symmetrically.

## THE GATE — binding
1. TESTS FIRST, SHOWN TO FAIL: credit-at-clicked-cell; CLICK_AT mint/seed/echo/falsify
   symmetry; drive_click gated (None without confirmation; fires after; closes on falsify);
   wiring scans.
2. ⭐ FALSIFIER (containment): the four stored control shas byte-identical (no level-ups, no
   confirmed goals in those episodes).
3. ⭐ FALSIFIER (the wire is live): rerun the 3b population trial; CONDITIONAL: if ≥1
   cognitive-path level-up occurs, ≥1 `[EGO-MINT]` must fire and the fabric must materialise
   (if no level-up occurs, rerun — the falsifier needs its precondition).

## THE UNDO
`git revert` of the 3b2 commit(s).

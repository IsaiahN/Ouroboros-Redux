# PRE-REGISTRATION — 3d-i: frontier pariah paths (the first compounding lever)

**Written 2026-08-11 BEFORE the build, at `f42074b`. Three sealed eras, zero L2 in 5400
episodes; residual obstacle: L2 attempts start from scratch every time. v3's blueprint
(recovered frontier-checkpoint doc) adapted to the fabric.**

## THE CHANGE THAT IS AUTHORISED

> `engines/egocentric/frontier.py` — `FrontierBook(fabric)`: fabric-backed (collective scope,
> topic "frontier_paths"). `record_fatal_opening(game, level, cell)` — called when an episode
> that stood at frontier level N dies (GAME_OVER before budget) : the FIRST post-frontier click
> cell is banked as a fatal opening. `avoid_set(game, level)` — the union of banked fatal
> openings for that game+level, read from seeds+local (population-wide compounding).
> Wiring: (a) the loop tracks its post-handoff first click + current level (getattr-guarded);
> (b) on episode end via the existing result path, fatal openings are recorded; (c) in the
> cycle pre-empt block: a chosen CLICK whose cell is in the avoid-set for the current game+level
> is remapped deterministically to the nearest non-avoided cell (ring scan, spine-side helper) —
> exploration ORDERING, not goal-claiming: the wheel rule is untouched (avoidance of a known
> death is not a goal; the death book's re-entry conditions hold — real deaths only, and the
> avoid-set is per-level, so clock/budget ends charge nothing).

## THE GATE — binding
1. TESTS FIRST, SHOWN TO FAIL: FrontierBook round-trip + seed-overlay union + determinism; the
   remap helper (identity off-list; nearest non-avoided when on-list; everything-avoided →
   original); wiring scans (record on fatal end; veto in the pre-empt block only; `[EGO-FRONTIER]`
   logs).
2. ⭐ FALSIFIER (containment): all six stored control shas byte-identical (fresh boxes: empty
   fabric, no handoffs, no frontier deaths).
3. ⭐ FALSIFIER (capability, next population run): frontier_paths records appear after frontier
   deaths, AND `[EGO-FRONTIER] avoid` lines show vetoed repeats on ≥2 games. Records without
   vetoes or vetoes without records → the loop is open → fix or revert.

## THE UNDO
`git revert` of the 3d-i commit(s).

# PRE-REGISTRATION — the replay observation feed (the frontier amnesia fix)

**Written 2026-08-11 BEFORE the build, after the sealed verdict (ZERO L2 in 20 gens; mechanism:
post-handoff `established=[]` — replayed actions bypass all learning).**

## THE CHANGE THAT WILL BE AUTHORISED
> During `_replay_winning_sequences`, after each successful `env.step`, feed the loop's
> egocentric machinery OBSERVE-ONLY: `loop._ego_observer.observe(frame, action)` and the spine's
> `note_move` on the resulting centroid delta (the same code path record_result uses), plus the
> seed-load at replay start. NO decisions, NO credits from replayed level-ups (the no-synthetic-
> credit rule stands — replayed levels are not this episode's discovery; the handoff already
> initialises prev_levels). The handoff then delivers a named body + established delta map.

## THE GATE
1. Tests first: an observe-only feeder helper (no credit path reachable from it); wiring scan.
2. ⭐ FALSIFIER (capability): in a population run with handoffs, post-handoff `[EGO-GOAL]`
   status lines show non-empty `established` on ≥3 handoff episodes (vs today's universal []).
3. ⭐ FALSIFIER (containment): the four stored control shas byte-identical (fresh boxes never
   replay).

## THE UNDO
`git revert`.

# UNREACHED — built, correct, and not called

A **priced ledger**, not a TODO list: each entry is a mechanism that exists, works, and cannot fire — with the reason
it cannot. Six mechanisms were hand-rebuilt this session that were already in this tree. This file is the countermeasure.

## RESOLVED

### `footprint.py` — FREED. Live, causal, no reset. `[LIVE]`
`discriminative()` probed each action **from reset** so every probe shared a start state; that control is what buys
`ambient` (what changes no matter what you do). RESET is hard-banned mid-game, so the experiment was unavailable —
and `causal_marker_color()` returned ONE dominant colour, which is the controllable-ID wall the docstring promised
to avoid.

**`self_signature(inducer)`** buys the same answer for free: the object whose CONFIRMED law is `translate` under a
directional action is, by construction, what my action choice steers. That is the discriminative test, run on real
play, at zero action cost — and it returns a **frozenset**, not a colour.

```
LIVE: self_signature() -> {9, 12}  (support 65)
SELF  body := colours [9, 12]  [BECAUSE that object type is the one whose CONFIRMED law is TRANSLATE
      under my directional actions -- derived from my own play, not from a colour I was handed]
```
The reset-based functions remain, marked **offline-only**.

### `proprioception.py` (509) — NOT a duplicate. Do not blend.
> *"Step 3: ONE self/world service, **replacing the two parallel self-ID mechanisms** (v18's motion SelfModel and the
> composer's discriminative_agency)."*

**The module written to unify two duplicate self-ID mechanisms is unreachable — so it became a third.** But it is not
a duplicate of `objective_validator:4313`: that is two-frame **move reconciliation** (egocentric vs allocentric);
this is **self-identification**. Same word, different jobs. A blend would have merged two things that must not merge.

**The real finding is the census.** Self-ID now lives in: `proprioception` (509) · `discriminative_agency` (191) ·
`self_model` (60) · `self_recognition` (37) · `_self_footprint()` · `footprint.self_signature()`. **Six.** The causal
one is now primary and the rest are candidates for retirement — but `avatar` (colour 12) is still the composer's
identity everywhere else, so **the footprint is fixed and the IDENTITY is not.** That is the next cut.

## SHOULD be reachable — BLOCKED, blocker named

### `refutation_ledger.py` (196) — persists refutations ACROSS episodes
Honest selection needs a memory of what has already been killed. Nothing calls it. **Useful and unblocked** — the
cheapest remaining win in this file.

### `molecule_prediction.py` (136) · `match_abduction.py` (124)
**Candidate 2, unchanged since July 8:** the molecules exist; abduction does not route to them.
`residual_router._atomics()` now bridges the causal map and the object inducer; these two are the rest of the bridge.

## TRIAGED — the eight, against what ls20 needs

| module | verdict |
|---|---|
| `persistent_model.py` (110) | **WANTED.** "cross-level component model that accumulates understanding." The agent re-learns every level from zero; this is the memory it lacks. |
| `active_test.py` (152) | **WANTED.** "The agent does NOT wait for the environment to reveal the rule." The trigger probe already does this by hand — this is the general form. |
| `validation.py` (161) | **MAYBE.** "turns articulate + course-correct into a mechanism." Overlaps the residual router. Check before wiring. |
| `self_recognition.py` (37) | **SUPERSEDED** by `footprint.self_signature()` — induced, causal, multi-colour. |
| `delay_operator.py` (215) | **NOT ls20.** `DELAY(M,k)` lifts a molecule over time. ls20 has no delayed effects. Dormant, correctly. |
| `temporal.py` (160) | **NOT ls20.** "the controllable is your position in a navigable HISTORY." Not this game. |
| `ui_planner.py` (109) | **NOT ls20.** "COMMAND games (no self avatar)." ls20 has an avatar. |
| `coast.py` (118) | **NOT ls20.** "score-proof exploit/recompose economy." No score to exploit. |

**Four are for other games and are correctly dormant. Two are wanted. One is superseded. One needs a check.**

## CORRECTLY not imported — do not "fix"
Entry points (`run_evolve`, `submission_agent`, `ouro_trial`) · harness (`online_harness` imports the agent, not the
reverse) · tests · offline tools (`frame_delta`, `level_segmenter`, `primitive_ledger`).

## REMOVED
`joint_state_push.py` · `slot_cycle.py` · `dynamics_forecast.py` — 276 lines, superseded by `model_search.py`.
Recoverable from the `molecules` snapshot.

## The rule
> **Unreachable is not dormant.** Dormant means a route exists and the board has not asked. Unreachable means no route
> exists, so it will not fire when the board DOES ask. The first is design; the second is a defect, and it must be
> named and priced rather than rediscovered by hand a seventh time.


---

## RESOLVED — `_apos()` is CORRECT. The bug was my reading of the number.

`_apos()` returns the centroid of colour 12 — the top two rows of a five-row composite body — and 28 call sites use
it. It looks exactly like the composite-avatar bug. **It is not, and three measurements say so.**

**1. The cost was never here.** Instrumented INSIDE the composer thread (it runs in a background thread, so cProfile
on the main thread shows only network I/O — which is why this was invisible):

```
                        calls   total s   ms/call   % wall
segment_objects           191      0.16    0.8145     2.4%
self_footprint_live       540      0.04    0.0689     0.6%
self_signature            592      0.04    0.0619     0.6%
instrumented total: 0.23s of 6.6s wall (3.5%)      60 actions in 6.6s = 0.11 s/action
```

**3.76 ms/step against a "3400 ms/action regression" that never existed.**

**2. `actions=49` was the composer STOPPING, not slowing.** `epochs=0` said so plainly and I read past it twice.
The run was never slow. It ended.

**3. The offset does not move the cell.** Navigation quantises by 5; on the full frame the colour-12 centroid and the
whole-body centroid land in the SAME logical cell (6,7). A 1.5px offset inside a 5px quantum. (An earlier "100%
differ" measurement was mine, taken on `g[2:56]` — a different grid, shifting every row by 2 across the ÷5 boundary.
My error, not a finding.)

**4. What DOES change is the colour under the centroid: 12 -> 9.** And `_apos()` is not only a position — it is an
**identity claim**. The whole-body centroid sits on colour 9, which IS me but is not what `avatar` names, so every
colour-keyed self-check answers "not me", and the composer concludes after 49 actions.

> **The contract of `_apos()` is "a position that is ON me, keyed by the colour I identify myself by."
> Under that contract the colour-12 centroid is CORRECT and the whole-body centroid is a violation.**

**The real defect is upstream and unchanged:** `avatar` names ONE colour of a two-colour body. Fixing it means making
the IDENTITY a signature ({9,12}) **everywhere at once** — not moving this centroid underneath 28 call sites that
still believe the old identity. `footprint.self_signature()` already supplies the signature, causally, live.

## THE REAL BUG FOUND ON THE WAY — `except Exception: pass`

```python
def _run_composer(self):
    try:    validate_multilevel(...)
    except Exception:  pass          # <- every composer crash looked like a quiet, early finish
    finally: self._done = True
```

**Two full diagnoses were spent theorising about CPU cost for runs that had simply stopped.** Nothing anywhere
printed a traceback. Now loud (`OURO_LOUD=1`, default on) and the traceback is kept on `self._composer_error`.
A silent failure costs exactly the time it takes to find it.

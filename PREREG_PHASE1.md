# PRE-REGISTRATION — PHASE 1: the self (perception substrate, read-only)

**Written 2026-08-10 BEFORE the build, on `v4-cold` at `068f57e` + log/harness commits.
Baseline: 6 games L1, ZERO L2 in 1800 episodes / 20 generations.**

## 1. THE CHANGE THAT IS AUTHORISED

> Verbatim port of `perception.py`, `self_locus.py`, `agency.py` from `Nexus:src/newhorse/` into
> `engines/egocentric/` (imports adjusted only). A small new `EgoObserver` wrapper: holds the
> previous frame internally; per observation segments the frame, updates the `ObjectTracker`,
> feeds `SelfLocus.observe(action, before_objs, after_objs)`, and returns a dict (controllable
> colour or None, its centroid, object count). ONE wiring point in the cognitive loop's result
> path: call the observer with the post-frame + executed action, print an `[EGO]` line. The
> result feeds NOTHING — no decision path reads it in Phase 1 (the wheel rule: no signal, no
> wheel; Phase 1 is not even signal yet, only sensing).

**HARD CONSTRAINTS:** deterministic, no RNG; observer failures swallowed to a counter, never
crash the loop; no thresholds tuned away from the newhorse originals; `cognitive_loop.py` gets
the call site and nothing else.

## 2. THE GATE — binding

1. **TESTS FIRST, SHOWN TO FAIL** (`tests/gate/test_egocentric_substrate.py`): segmentation on a
   synthetic frame; tracker identity across a move; **the contingency guard** — a colour moving
   DIFFERENTLY per action beats a colour moving identically under every action (the autonomous
   drifter must NOT be named self); cold start → None; the observer contract; the wiring scan
   (call site exists in the result path; `[EGO]` logged; nothing in the decision path reads it).
2. **⭐ FALSIFIER (containment):** wired arm byte-identical (`seq_sha`) to the pre-wire control
   shas (`.runs/p1_controls.json`, 4 games, seed 5). Any diff → the observer is not read-only →
   revert.
3. **⭐ FALSIFIER (capability):** on ≥4 movement-capable games (fresh seed), the `[EGO]` log
   names a stable controllable colour by the final third of the episode. Fewer than 4 → the
   substrate is blind on the games Phase 2 needs it for → fix or revert before Phase 2 opens.

## 3. THE UNDO

`git revert` of the Phase-1 commit(s); baseline `068f57e`.

## 4. WHAT THIS DOES NOT CLAIM

Nothing about levels, nothing about behaviour (there must BE no behaviour change — that is the
containment falsifier). Phase 1 only buys the loop eyes for its own body.

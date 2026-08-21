# PREREG — THE PERSISTENCE MONITOR: THE ACHIEVEMENT GAP (2026-08-21)

**AUTHORITY:** `record/findings/F1_VERDICT_AND_SHADOW_TEST.md` Part 2, GAP 2 (approved): *"persisting in
what isn't working is a TREND no single-event bin can express — a counter over narration, not a fifth
bin."* `REFACTOR_PLAN_AND_READ.md` R5 (affect: book-computed modulators of risk, never a price).
**STATUS: PREREG, no code.** Mechanics only; no game specifics.

## WHAT IT IS
A read-only CONSUMER of the narration stream (`PREREG_W1_NARRATION.md`; `engines/egocentric/narration.py`'s
record grammar) that detects the same residual recurring under an unchanged strategy for k consecutive
steps, emits ONE named finding — a PERSISTENCE record — and exposes a bounded channel to the two
book-computed risk modulators. It classifies no event. It counts.

## THE UNIT (fixed tokens from the stream; nothing inferred)
Per step, from the records that close against that step's BET:
- the **RESIDUAL ρ** = (ROUTE.bin, ROUTE.why_not.fact), restricted to the FAILURE bins BROKEN_REBINDING
  and BROKEN_MECHANISM — a staked bet that missed. NOVEL is not failure (nothing staked, nothing to be
  wrong against); TRANSFERRED is success. A step with bin=None (no bet — every [REPLAY] step, by F3) has
  no ρ.
- the **STRATEGY σ** = (ACT.rung, BET.bin, the sorted slot-key shape of BET.slots — `last_bet` already
  stores exactly this — PLAN.mode, PLAN.gate).
A **RUN** is a maximal sequence of consecutive steps of one game with identical (ρ, σ) and ρ ≠ None. The
run length resets to 0 when ρ changes or is None (a TRANSFERRED settle included), σ changes, or the level
changes. For the level reset the BET record gains an additive `level` field from the loop's `_ego_level`;
records without it cannot reset on level, and the readout says so. The monitor's own records never count:
it reads the BET / ACT / PLAN / ROUTE points and nothing else.

## k — DERIVED FROM THE PER-GAME STEP DISTRIBUTION
**k_g = the median number of steps between successive level crossings in THIS agent's own history on game g**
([OWN] range: the `level` field on BET records, per game). Meaning: persisting in one failing strategy for
as long as it typically takes to cross a level in this game is persistence by the game's own yardstick,
not by a number. k_g ≥ 2 by definition — one failure is an event (a bin); repetition is the trend.
Fallbacks, stated: no crossing in OWN history → the population median of per-level step counts over games
with ≥ 1 crossing ([COL]); no crossing anywhere → k undefined: the monitor counts, never fires, and its
readout says `unarmed`. k_g is recomputed at each level crossing and FROZEN within a level — the run being
measured must not move its own bar.

## THE RECORD
When a run reaches exactly k: ONE record on the narration topic, point=PERSISTENCE (a new fixed token in
POINTS — a schema event, stated as such), side=`monitor`, range = the run's BET range, ref = the first BET
id of the run, payload {k, run, rho, sigma, first_step, last_step, game}. Gloss, NSM primes as
connectives only: "I DID THE SAME THING MANY TIMES; THE SAME BAD THING HAPPENED; I KNOW THIS NOW". One
record per run (fires at k, not again at k+1); the live state `persisting` holds until the run resets.
W1's F1 (exactly one BET per step) is untouched: the record is side=`monitor`, never a bet.

## THE CONSUMER — a modulator, never a price
`affect.AffectGains.gains()` gains a third channel, **`persist = min(1, run/k)`** (0 with no live run;
bounded in [0, 1]; a pure function of the stream prefix like its two siblings, so it replays). It feeds
exactly two sinks: the explore-effort steer (the `explore_boost` path STARVE_STEP already uses — it
reorders explore candidates the loop already had) and the goal stuck/abandonment measure (`goal.py`: being
stuck, not elapsed time). It feeds NOTHING that ranks, prices or selects: not the mint's MDL terms, not
reputation, not breeding, and NOT `PREREG_STANDING_HALF_LIFE_ATOMS`' S — persistence is the agent's trend,
not an atom's record. Structural: the channel value is never written to any stream a price reads, and a
gate test scans the price modules for any reference to the channel or the PERSISTENCE token.

## HOT PATH + REPLAY + THE ALLOWLIST
O(1) per record: the spine hands each emitted record to the monitor in memory (one observer hook; no
JSONL read on the hot path — arm C's precedent). Offline, the monitor replayed over the narration JSONL
yields byte-identical PERSISTENCE records: a pure function of the stream prefix. The `narration` entry
in `tests/gate/test_consumers.py`'s ALLOWLIST DELETES in the same change — the offline replay is the
stream reader the entry promised, and the gate's stale-entry test forces the deletion.

## THE GATE DEPENDENCY — stated honestly
This monitor counts over narration. If W1's shared falsifier fires (all three pre-named statistics inside
their shuffled bands: narration decorates), then: (i) the records remain true descriptions — bet-side
precedes act by construction, and bins and rungs are the loop's own state — so the COUNT stays valid;
(ii) W2+ redesigns around instruments, so the CARRIER changes: the same unit (ρ, σ), the same k, read from
the router's and the wheel's outputs directly rather than from the stream; (iii) the monitor's own wire
inherits W1's discipline — its channel must FLIP a decision in a constructed run (the wire check) before
any claim that detecting persistence changes behaviour. A PERSISTENCE record that changes nothing is
itself decoration, reported as such, never absorbed.

## FALSIFIERS (tests/gate/test_persistence.py, house style)
- **F1 · EXACTLY k:** a constructed stream with identical (ρ, σ) for 2k steps fires ONE PERSISTENCE record
  at step k — none before, none after within the run.
- **F2 · RESET:** the same stream with σ changed at step k−1 (rung, bet shape, plan gate — each separately)
  never fires; resumed identity counts from 1.
- **F3 · NON-REPEATING:** a stream alternating bins or rungs every step never fires at any k.
- **F4 · CONSUMER ONLY:** the monitor's input is the record sequence; replay over the JSONL equals the
  online emission; the ALLOWLIST entry is gone and the gate's scanner sees the reader.
- **F5 · NO PRICE READS IT (structural):** the scan over `mint.py`, the standing module, reputation and the
  tournament weighting finds no reference; `persist` moves `explore_boost` and the stuck measure and
  nothing else — asserted by identity of the sinks, not by name-alike.
- **F6 · WIRE CHECK:** a constructed run at k flips at least one explore choice with the channel wired vs
  unwired — sensitivity of the wire itself, per W1's amendment.
- **R4:** TRANSFERRED at step j < k resets; NOVEL steps never start a run; a [REPLAY] step resets (bin None).
- **Known-negative:** k undefined → counts, never fires, readout `unarmed`.

## UNDO
Remove the observer hook, the PERSISTENCE token, and the `persist` channel; RESTORE the `narration`
ALLOWLIST entry (the stream is unconsumed again and the gate would otherwise fail). PERSISTENCE records
and the `level` field on BET records remain readable history. Nothing stored is destroyed.

## SEAT 3 RULING (2026-08-21): APPROVED (the schema event reviewed, the rule worked).

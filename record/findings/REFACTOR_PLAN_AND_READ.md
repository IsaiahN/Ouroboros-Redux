# THE REFACTOR: PLAN AND READ (2026-08-20)

Seat 3's directive: agents that beat ARC-AGI-3 **whitebox, transparent, aligned** — the ladder
(priors ≠ primitives), the derived library index, and the network economy, as **one design**.
This is **a plan and a read, not a build.** Nothing below was built.

---

# PART I · THE READ

## I.1 What v3/v4 actually implemented (from code, not memory)

Every named mechanism **exists in this repo, byte-identical to the sibling** — the network
layer was carried forward whole and is largely idle, not lost.

| mechanism | file | what the code actually does |
|---|---|---|
| **HGT** | `horizontal_transfer_engine.py` | **Pairwise donor→recipient transfer of GENOME TRAITS** — gated by an emotional-compatibility score, adaptive per-layer rates tuned by past transfer success, all logged to `horizontal_transfer_events`. **It moves constitution, not behaviour.** |
| **Viral packages** | `engines/social/viral_package_engine.py` | Pool-spread **behaviour patterns** (positive selection), with cohort wisdom and a sequence-reputation layer. |
| **Pariahs** | `engines/social/pariah_manager.py` | Negative selection with **decay as a formula**: `toxicity(t) = initial × (1 − decay_rate × generations_since_trigger)`, and the rationale in its own docstring: *"without decay, ancient pariahs accumulate infinitely and agents become paralyzed."* |
| **Prestige** | `engines/social/prestige_engine.py` | Dual currency **enforced in code**: `assert_no_budget_effect()` raises `PrestigeBudgetViolationError`. Prestige buys breeding_priority (1–3×), survival_protection (0–80%), bonus slots; **never actions.** |
| **Mastery** | `mastery_system.py` | Replay is a **privilege**: Diversity 30 + Robustness-under-ablation 30 + Consistency 20 + Efficiency 20; Novice = **no replay**, Apprentice = study-only. |
| **Roles/modes** | `agent_operating_mode_system.py` | Phase-switched distributions, Pioneer = 5× mutation. |
| **Reputation** | `viral_package_engine.update_sequence_role_reputation` | **Per-role** success columns, updated **by the consumer after use**, carrying the consumer's frustration/satisfaction. |
| **Primitives** | `seed_primitives.py` (~4,000 lines) | A registry of executable primitives in **hand-authored categories** (ARC-perceptual, relational, structural, abstract-physical, symbolic-mechanics). |
| **Retrieval half-built** | `engines/social/primitive_suggester.py` | The `PrimitiveSuggesterRung` — registry-loaded today. |
| **Also present, not in the summary** | `engines/social/` | `network_contributor.py`, `package_compressor.py`, `execution_trace_miner.py`, `remote_effect_learner.py`, `resonance_detector.py`, `hypothesis_system.py` — six more network organs, unread in depth; listed so the inventory is honest about its edge. |

### Answers to the specific check-questions
- **HGT vs viral: TWO mechanisms, genuinely different.** Different object (traits vs patterns), different topology (pairwise vs broadcast), different gate (compatibility vs success). Not one thing with two names.
- **Voting: the consumer writes the vote.** `update_sequence_role_reputation` is called *"after an agent uses a sequence"* by that agent's own outcome — **self-vote by construction**, and votes pool into per-role columns, so **same-role votes are the correlated pool counted as if independent.** Both of Seat 3's suspicions confirmed: it is a popularity measure over a pool that already agrees.
- **Ranking decay, scoped precisely: BOTH halves of the designed decay policy EXIST** — prestige decays 3%/generation (`prestige_engine.py:214-231`, *"prevent coasting"*) and the youth bonus exists (`evolutionary_engine.py:42`, 1.5× newborn → 1.0, wired into tournament selection at :666). **What lacks decay is sequence/package REPUTATION** — the viral ranking — a score earned early stands forever there. So the restoration scope is narrow: extend the existing decay policy to reputation, under the ruled names.
- **The affect leak, unasked but found:** the consumer's `frustration_level`/`satisfaction_level` enter the reputation update — **affect is priced into the ranking**, exactly what the held convention (*affect is a derived readout, never a price*) forbids.
- **A memory-vs-code divergence:** the summary's mode tables say 60/30/10 and 70/15/15; **the code says EXPLORATION 60/10/20/10 and OPTIMIZATION 10/50/25/15.** The code is the fact; the summary mis-remembers.
- **Role self-determination: FOUND — my earlier "not found" was wrong** (bad search tokens, corrected same day). `agent_operating_mode_system.py:1028+`: per-role fit scores from performance history, `preferred_role`, `role_locked`, `request_role_change` with cooldown (:1480), and wA/wB reset hooks in `i_thread`/`episodic_memory`. **It exists and is rich.** One boundary case: fit scoring consumes frustration/satisfaction — affect entering an allocation gate; flagged under the affect ruling for Seat 3's call.
- **The macro mechanism EXISTS:** `effects.compose()` memoises id-sequences into `COMPOSITE` atoms with structural/lexical typing. Seat 3's hunch was right — it needs **indexing and naming**, not a second mechanism.

## I.2 Each mechanism against the framework

| mechanism | filter or verdict? | what it prices / gameable? | residual still live? | membrane |
|---|---|---|---|---|
| **HGT** | filter (proposes a recipient) | compatibility — gameable only if agents shape their profiles to attract donors (not observed) | **live** (diversity maintenance) | **traits are generators** — constitution transfers, acquisition still has to happen. CLEAN. |
| **Viral packages** | **verdict in practice** — a consumed package IS the behaviour | success-rate — **gameable by the correlated pool that votes on itself** | live | **carries recordings today** (sequences). VIOLATES unless re-scoped to methods. |
| **Pariahs** | filter (avoidance pressure, decaying) | failure, with expiry | live | negative knowledge is inherently a method ("not this") — CLEAN, **keep the decay formula untouched** |
| **Prestige** | filter (a hearing, not a verdict) — enforced | contribution; **gameable via breeding**: prestige → 1–3× breeding weight with no counterweight = rich-get-richer | live | n/a (currency, doesn't cross) |
| **Mastery** | **filter, exemplary** — it prices *regeneration*, which cannot be gamed by replaying the thing it gates | robustness under ablation | **live — THE model** | **it IS the membrane**, written before the membrane was stated |
| **Reputation** | verdict-shaped (below threshold = disabled) | popularity of the already-agreed; **no decay** | partly — per-role success is worth knowing | the ranking itself doesn't cross; what it ranks does |
| **Roles/streams** | filter (allocation) | w_B is **the population's independence distributed across members** — unmonitored aggregate | live | n/a |
| **Seed primitives** | — | — | live as INVENTORY | **the registry itself is handed, which is fine for priors and forbidden for capabilities — the sort in II.4 is the fix** |

**Survivors as-is:** pariah decay, prestige decay (3%/gen), youth bonus (renamed `newcomer_handicap`), mastery gate, prestige-vs-actions separation, HGT, role self-determination (ported, with its affect input flagged).
**Survive re-scoped:** viral packages (methods only), reputation (gains `standing_half_life` + de-correlated outcomes + affect removed), streams (re-classified by contact).
**Excluded entirely (directive):** prestige in breeding/survival (removal site: `evolutionary_engine.py:666` tournament weighting), consumer-voted rank, the single A/B dial.
**Must be built new:** the visible catalogue (see RULINGS §L), the library-know-how channel.

## I.3 The current agent on the ladder — earned, handed, missing

**EARNED (real rungs, receipts in the fabric):**
- **Perception → binding → EFFECT atoms**: `learn_effect` proposes from observed transitions; the mint applies gates + the MDL bargain; nothing enters Γ without paying. 1,829 structural atoms, all earned.
- **Goal abduction**: predicates extracted from its **own** level-up frames (the link-3 hook, ground-settled at 37 firings).
- **Frontier avoidance**: banked fatal cells from its own deaths.

**HANDED (the ladder's forbidden moves, live today):**
1. **`seed_primitives.py` — ~4,000 lines of executable capability seeded at birth.** Not dispositions: `detect_hole`, `is_container`, `object_permanence` *as functions*. The worked case says object permanence is **acquired** through surprise-at-violation; here it is a subroutine. **The exact thing the claim forbids, at scale.**
2. **`OURO_FABRIC_SEEDS` — every worker boots with 25 other agents' fabrics cross-mounted.** Inherited library at birth: **Stream B wearing Stream A's clothes**, in the launcher.
3. **`winning_sequences` replay** — recordings replayed into the environment at startup. Mastery-lite gating exists (`engines/egocentric/mastery.py`), but the replay corpus itself is a recording crossing downward.

**MISSING RUNGS (residuals the agent cannot currently perceive):**
- **The plan rung has never fired** (g7 = 0, both branches): no plan has ever driven an action, so every residual that only *acting on a plan* can generate — plan-vs-outcome error — **does not exist for this agent.** Figure 3's "a reading below the break is a reading of nothing," in production.
- **The rebinding discriminator is spent** (binder knows staleness, forgets it in the same statement) → the mint is fed repairs → **65% of all verdicts are rederivations.** The library's index failure, measured.
- **Retrieval is name-lookup only**: NOVELTY checks a canonical key; nothing can find an atom by what it was composed from or what it affords. **D-5 (progress buys ~100× slowdown) is what un-indexed retrieval costs**, and link-3's vocabulary-pointed-away-from-the-domain is the same defect's first receipt.
- **Narration is absent** — the whitebox requirement is currently unmet: decisions are logged, reasons are not.

## I.4 The falsifier for the ladder — designed, and partly answerable today
**Claim at risk:** *if a handed capability performs identically to an earned one, the ladder
is developmental history, not a constraint.*
**Design:** matched-game arms. Arm E plays with fabric seeds OFF (earns from nothing); arm H
receives arm E's banked routes as seeds. Score **not performance but extension**: does H
generate the *next* rung's residuals (new-level crossings, novel-atom rate *above* the seeded
level) at E's rate? **Ladder predicts H extends at a deficit; identical extension kills the
ladder.**
**Existing evidence, suggestive not decisive:** the 8 L1+ games (banked routes, replay-heavy)
have produced **zero** L1→L2 extensions since the flip while running 100× slower — consistent
with handed-cannot-extend, **but confounded by D-5**, which is why the arm must be run after
the index work, not before.

---

# PART II · THE MERGED PLAN

One design, six workstreams, ordered by dependency. **W1 gates everything** — it is the
measurement the rest is judged against.

## W1 · Baselines and the whitebox spine
1. **D-5 timing read** *(absorbed from the old queue — was queued build #1)*: per-action cost
   breakdown on one slow L1+ worker. The index work's before/after number.
2. **Loop narration + memory-at-three-ranges** *(absorbed — was queued build #4, Seat 3's own
   two items, one build)*: the agent narrates per step, in the loop's grammar + NSM primes —
   slot, bin **and why not the neighbour bin**, candidate offered, which guard was the zero,
   did the bargain pay, what settled — and names its memory source: *this episode / my history
   / the collective*. **Shared falsifier stands: if narration names sources and behaviour does
   not change, the framework describes rather than drives.** This is also the transparency
   deliverable — the whitebox is the narration stream.

## W2 · The library index (provenance, not classification)
- **Tags are facts about construction, written at composition time**: an atom's tags = the
  transition signature it was learned from + the primitives/priors its derivation consumed; a
  COMPOSITE's tags = its parts. *Recorded at the event or unavailable* — the origin-stamp rule
  extended (`PREREG_DRAIN_ORIGIN` machinery already stamps origin; this widens the stamp).
- **Two edge types, never conflated**: `composed_from` (provenance) and `reached_by`
  (retrieval history) — separate fields, separate consumers.
- **The mint's NOVELTY guard becomes an index consumer**: rederivation stops being a string
  re-derived and becomes an index hit that *strengthens* the entry — **turning the 65%
  rederivation flood from waste into reinforcement signal.**
- **Checkability**: a capability claiming primitives it does not use is a findable mismatch —
  the index inherits provenance's audit property. Gate: sample N atoms, re-derive, compare tags.
- *Absorbed salvage*: `_extract_rungs` (rung inventory feeds the index), `scan_context_keys`
  (the produced-vs-consumed check, repointed at index fields).

## W3 · Priors vs primitives — the sort, derived not authored
- **The derived test**: a **prior** is consumed by acquisition machinery (it shapes search,
  salience, or retention — `curiosity_drive`, `imitation_bias`, surprise weighting); a
  **primitive** is invoked by action selection. **Sort `seed_primitives.py` by consumer**, not
  by the hand-authored category headers — the categories are replaced by the derived index.
- **Handed capabilities get an earn-through gate** (the mastery pattern, applied at the
  library): a seeded primitive is **study-only** (Apprentice tier) until the agent regenerates
  its effect under ablation on its own board; only then does it tag as available-for-
  composition. **The seed registry becomes a curriculum, not a capability grant.**
- **Fabric seeds stop auto-loading**: cross-mounted fabrics become a *lookup target* (the
  collective range in W1's narration), not birth-inherited contents. That is the Stream-B
  reclassification, enforced at the loader.

## W4 · Composition, macros, and the proposer
- **Macros = extend `effects.compose()`**, not a new mechanism: add **name, composition-time
  tags, and an episode-scoped retrieval cache**. Improvement on the sketch (as invited): a
  macro is **(part-set, ordering constraint, applicability guard)** — the guard is the
  predicate (from goal-abduction vocabulary) under which the macro is worth attempting, so
  retrieval is *by situation*, not by name. Compression is the claim; MDL already prices it.
- **Composition-to-new-primitive, disambiguated per the three routes** *(absorbs the guard-
  triple ruling — standing item #6)*: **composed** = inside closure, product is a *name*
  (COMPOSITE), guards SUPPORT×NOVELTY + bargain; **observed** = `learn_effect`'s route,
  already sound; **genuinely new primitive** = only via instrument-extension or import, never
  via composition — REACHABILITY guards *only* the composed route, resolving the triple:
  **three gates are route-specific, the bargain is universal.** The verdict `reason` field
  ships after this lands, encoding the resolved semantics.
- **The proposer**: today observation-only. With W2 it gains lookup — **propose = observe,
  then triangulate the index** (effect-shape → candidate atoms/macros → guard check), with
  `reached_by` recorded. Its narration (W1) states which route each candidate came by.
- *Absorbed*: **binding_stale retention** *(was queued build #3)* — the rebinding bin is the
  route by which "repair, don't mint" reaches the proposer; without it the index inherits the
  rederivation flood.

## W5 · The network economy, re-scoped to the membrane
- **The crossing rule, one sentence: METHODS CROSS, RECORDINGS DO NOT — and the mastery gate
  is the checkpoint for both directions.** A viral package carries: the method-pattern
  (macro + guard + provenance tags), never the action sequence. The receiver **earns through**
  (W3's gate) before the content tags as its own.
- **The new channel Seat 3 asked for — library know-how — is W2's tags in transit**: *"these
  two primitives compose for oscillating objects"* is exactly a `composed_from` + guard
  record. **It is a generator by construction**, and it is the only channel where the
  membrane question is unambiguous. Design it as the *primary* viral payload; game-tips become
  the legacy payload.
- **Reputation: consumer-voting is NOT PORTED** *(Seat 3 directive)*. Packages ranked by
  votes from agents that consumed them is agreement priced as evidence, and it does not come
  across in any form. Consumption writes **usage telemetry only** (counts, contexts), never
  rank; rank derives from **independently-earned outcomes in low-correlation channels**
  (cross-role, provenance-verified convergence), with the pariah decay formula applied
  symmetrically so no score outlives its evidence. Affect moves to narration and never
  enters any price.
- **Prestige: the breeding link is NOT PORTED** *(Seat 3 directive, 2026-08-20)*. The old
  `breeding_priority 1-3x` and `survival_protection` multipliers are correlation defects, not
  features to counterweight. **Prestige buys a hearing only** — read-order and attention —
  never breeding weight, never survival immunity, never actions. Breeding selection draws
  from RLVR fitness plus a uniform lottery floor; prestige is absent from the draw entirely.
  *(Note: the directive named breeding; survival_protection is excluded here by the same
  standing-buys-outcome logic — flagged for confirmation.)* Retired-never-deleted stays
  until full games are won.
- **Streams: the single A/B dial is NOT PORTED** *(Seat 3 directive)* — one ratio pooling
  shared and direct sources is the defect itself. Replaced by **per-source weights classified
  by CONTACT** (this-episode / own-history / inherited-library / role-pool / cross-role /
  prescription), so "how much do I trust the pool" is never one number hiding six. The
  population-aggregate inherited-material weight becomes a standing beat vital.
- **Roles**: implement **label-follows-behaviour** (it does not exist): relabel when a
  measured source-weight range holds across k games. Mode-table divergence fixed to
  whichever Seat 3 rules is intent — code and summary currently disagree.

## W6 · Selection and measurement
- Split-half improvement read stays the counter *(unchanged from the old queue)*; the ladder
  falsifier arm (I.4) runs **after W2** so D-5 stops confounding it; cross-domain convergence
  weighting requires the provenance check — **same atom by convergence corroborates, by
  adoption does not** — which W2's tags make mechanical.

## EXCLUDED BY DIRECTIVE — the three correlation defects, named so they stay dead
Seat 3, 2026-08-20: *"prestige buying breeding weight, the stream ratio treating shared and
direct sources as one thing, packages ranked by votes from agents who consumed them — all
three are correlation problems... do not port those into your plans or the build."*
**None is ported, none is counterweighted — they are absent from the design.** The common
root, stated once: **each priced AGREEMENT as if it were EVIDENCE.** Any future mechanism
whose rank, weight, or breeding draw can be moved by parties that consumed, inherited, or
already agree with the thing being ranked inherits this exclusion by default.

## Absorbed from the suspended queue — named, per instruction
1. **D-5 timing read** → W1 (baseline). 2. **Loop-narration + memory ranges** → W1 (the
whitebox spine). 3. **binding_stale retention** → W4. 4. **Guard-triple ruling** → W4
(resolved as route-specific gates; supersedes the standalone ruling). 5. **Verdict `reason`
field** → W4, after the triple. 6. **Salvage trio** (`_extract_rungs`, `scan_context_keys`,
`PrimitiveSuggesterRung`) → W2/W4. 7. **Split-half read** → W6 (unchanged). 8. **v3-mechanism
review** → Part I (done). **Not absorbed, still standing:** D-1/D-2 dispositions, the
standing-red test ruling, memory profile of the five L0 workers, D-6 probe removal, rotation.

## Queued on acceptance
**Review all 33 PREREG files for continued relevance** — W4 alone supersedes at least
`PREREG_EMPTY_PLAN_ATTRIBUTION` and touches `PREREG_REFIT_DESTINATION`; each gets kept /
amended / retired-with-note, per the hygiene rule.


---

# RULINGS APPLIED (2026-08-20, Seat 3) — supersede the matching plan text above

## R1 · Survival protection: excluded, confirmed
Worse than the breeding case — breeding weight biases the next generation; **survival immunity
prevents selection from operating at all** on exactly the agents whose standing is highest.
Both leave the design; the removal site for the pair is the tournament weighting at
`evolutionary_engine.py:666`.

## R2 · The innateness line, ruled in the framework's own terms
> **A prior is a primitive that can produce a QUESTION. A capability is one that can only
> ever be an ANSWER.**

`detect_motion` produces a gap (*something changed, unexplained*) — it may seed.
`object_permanence` is a conclusion drawn from gaps — it must be earned. **W3 sorts
`seed_primitives.py` on this test**: source-of-residual → prior, may seed; resolution-of-
residual → capability, earn-through required.

## L · The library, redesigned: TWO OBJECTS, not a market
**The agent's own library is SILOED** — earned content only; its closure is its entire
composition space. **The visible CATALOGUE is population-wide** — every agent sees *what
exists*: that a capability of this kind is held somewhere, what it affords, roughly what it
was composed from. **Content never crosses; the fact of existence does.** Knowing people can
play piano vs playing piano.

**Catalogue entry shape (the design asked for):**
`{kind, affordance-predicates (goal-abduction vocabulary), composed_from tag summary
(provenance, no parameters), prior-base, holder count + roles (never holder content),
mastery tier of best holder, first-existence generation}` — everything a target needs,
nothing a playback could use.

**Aiming:** an agent aims at an entry by adopting its affordance-predicates as a goal
hypothesis (the abduction machinery already consumes exactly this shape) and requesting the
METHOD from a holder via the know-how channel — a `composed_from` + applicability-guard
record, which is a generator by construction.

**Earn-through verification, not assertion:** the mastery pattern at library grain — the
earner must regenerate the capability's effect under ablation on its own board (its own
obstacle), and only then does the entry tag as *earned* in its silo. Consumption of the
method alone leaves it *studied*, usable for aiming, not for composition.

**The aggregate reading it still needs (Seat 3's addition):** a population **library-overlap
monitor** — if every agent's earned silo converges on the same entries, the population is one
frame regardless of route. Per-agent weights cannot show this; the monitor reads pairwise
silo overlap per generation and joins the standing beat vitals.

## R3 · Vampire/youth: RESTORATION, not invention — and renamed
Found in code (correcting this document's first draft): **prestige decay exists**
(3%/generation) and **the youth bonus exists** (1.5×→1.0, tournament-wired). The missing
half is decay on **package/sequence reputation** only. Work: extend the decay policy to
reputation; rename mechanism-first per ruling — **`standing_half_life`** (standing expires
unless re-earned) and **`newcomer_handicap`** (not age — not being outranked by history you
had no chance to accumulate).

## R4 · The SECOND ROOT, added to the exclusions
> **Pricing a past outcome as a present one.** Any mechanism whose weight is earned once and
> never re-tested inherits this. Standing is a stake that survives the outcome it was earned
> on — which is why it decays or is handicapped, and never simply accumulates.
Distinct from root one (agreement priced as evidence); both now guard future mechanisms.

## R5 · Affect, corrected to the ruling
**Keep:** the two book-computed modulators — risk tolerance (exploration temperature, hold
time, abandonment) computed FROM the books, per the Anthropic result (desperation changed
what corner-cutting was tolerable, not any option's estimate).
**Drop:** affect in any price — reputation, ranking, credibility, breeding.
**Keep as `[BELIEVED, unrun]`** with its falsifier attached, not foreclosed: *frustration
opens the proposer and tightens the mint* — a risk modulation, not a price. **The falsifier
runs before it is wired to anything:** is there a residual today that frustration predicts
and actions-since-last-settlement does not? If not, it is the same number with a better name
and is not minted.

## R6 · The ladder-falsifier arm gains a THIRD arm
Arm H (handed another agent's routes) confounds the ladder with cross-agent transfer.
**Arm S: handed its OWN earlier routes.** Ladder-only failure predicts S extends better than
H; transfer-only failure predicts S ≈ E. Without S the experiment tests a transfer claim
while reporting a ladder claim.

## R7 · Mode tables: code is intent
60/10/20/10 exploration, 10/50/25/15 optimization stand as written in code; the summary's
memory is noted as divergent, not reconciled to. **Truncation guard mandatory**: role counts
computed with a floor (`max(1, …)` or largest-remainder), because `int(6 × 0.15) = 0`
produced zero of two role classes once already.

## Confirmed right, kept verbatim
Mastery as the template for every crossing · the library-know-how channel as the primary
viral payload · I.3 as the finding of the read (the ladder's three forbidden moves, all live
in production — the strongest evidence the ladder describes something real).


## R8 · Affect-in-role-fit: STRIPPED (Seat 3, 2026-08-20) — and PLAN ACCEPTED
Frustration/satisfaction feeding role-fit scoring is affect entering an allocation gate, and
**allocation is a price** — it decides assignment and budget. The convention holds cleanly:
affect modulates how much risk this agent tolerates now; **it does not decide what this agent
is.** A role follows measured behaviour (source weights holding across k games), never how the
agent felt producing it. **The specific failure mode, named:** an agent frustrated *because
its assignment is wrong* scores badly on fit for a role it might be good at — affect in the
gate makes the assignment self-confirming. The port of role self-determination therefore
carries the fit machinery MINUS its affect inputs.

**Surgical note on the removal site:** `evolutionary_engine.py:666` carries *"prestige and
youth weighting"* together — **prestige comes out of the breeding draw, youth stays. Same
line, opposite dispositions.**

**STATUS: ACCEPTED AS AMENDED (Seat 3, 2026-08-20).** The PREREG review fires first; the
swarm stays held until the review says what is still relevant.

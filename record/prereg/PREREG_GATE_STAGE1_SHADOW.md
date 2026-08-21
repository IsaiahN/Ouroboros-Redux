# PREREG — REASONING GATE STAGE 1: SHADOW MODE (2026-08-21)

**AUTHORITY:** PROPOSAL_REASONING_GATE.md (approved through stage 1, all amendments); stage 0
(`engines/egocentric/action_book.py`) live. **STATUS: PREREG + BUILDER BRIEF**, mechanics only.
This stage builds the grammar and the gate and **blocks nothing**: every non-replay action is
evaluated and logged; no verdict reaches the action path. Stage 2 is Seat 3's, on this evidence.

**The one hook.** One void call beside the spine's `act()` in `cognitive_loop._narr_bet`, inside
its existing containment, receiving the opener frame the cycle already holds (`_pframe`, passed
in at the existing call if not in scope; never a second site). The gate retains the previous
opener frame itself — its only cross-step state. Module `engines/egocentric/reasoning_gate.py`
(grammar + builder + checks); stream: one JSONL record per utterance on a new personal topic
`gate`. The spine, book and composer are NOT modified; the gate's BET carries `ref` = the spine's
BET id so the streams join by data.

**The builder/gate split (load-bearing):** the shadow UTTERANCE-BUILDER translates the loop's
existing decision state into utterances and reads ONLY the agent's own state (bank slots and
residuals, the plan's atoms, the frontier book, action and rung, fabric standings). The GATE
reads the world (`apply_effect`, `compute_d`, frames) and the ledger (fabric, book, composite
records). Neither reads the other's sources — so CHANGED is built from what the agent's
perception tracked and checked against the mechanical diff, and "unreported change" on live
play measures perceptual coverage, not the builder's access to `compute_d`.

## 1 · The utterance grammar — a typed extension of the salvaged primes
Salvaged as-is from `origin/new-horse:src/newhorse/grammar.py`: the five types
(OBJECT/ATTR/REGION/PRED/OBJ), the 13 typed primes with signatures, `compose()`'s discipline
(ill-typed raises with its reason, never silently), the bare-type typed hole. Molecules and
counters are not carried. Authored new — the speech-act layer:
- **Types:** `RECORD` (a citable id: a gate PERCEIVE/BET utterance, a Γ atom, a composite) and
  `PRICE` (a cost claim: a number with its evidence count, or an explicit null). Terminals
  PERCEIVE / BET / ACT each PRODUCE a `RECORD` when emitted — precedence becomes type-checkable
  because a later terminal can only consume what an earlier one produced.
- **Heads, signature → type, check-kind** (one kind per head, riding the head):
  - `SEE (OBJECT, REGION, ATTR) → PRED` — per-slot state claim. *Executable*: exact lookup on
    the opener frame.
  - `CHANGED (REGION, ATTR, ATTR) → PRED` — a region went a→b since the previous opener.
    *Completeness*: the terminal's CHANGED set is checked as a SET against
    `compute_d(prev_opener, opener)` — every differing cell in some clause (complete), every
    clause in the diff (true). The terminal itself asserts "nothing else changed"; no separate
    closing head. Scope `cited ∪ changed` per the cost pin.
  - `SETTLE (RECORD[bet], PRED) → PRED` — the previous step's bet by id: held or broke, by d.
    *Ledger + executable*: the id resolves to this agent's step-N−1 BET, unsettled; the verdict
    equals the recomputed per-slot residual (the function ROUTE already bins on — named by
    identity at build time, as stage 4 named g7).
  - `STAND (RECORD[atom|composite], ATTR) → PRED` — strengthened / weakened / died. *Ledger*:
    equals the fabric's standing change for that id this step; an id cited in a bet that
    broke cannot strengthen in the same PERCEIVE.
  - `WANT (OBJ) → PRED` — consumes the salvaged `OBJ`. *Executable*: compiles to a Discrepancy
    (§5) non-zero on the opener frame; a satisfied WANT refuses as vacuous. Typed holes are
    permitted (a template) but a holed WANT composes with a probe only — DERIVE against a
    hole is ill-typed.
  - `GROUND (RECORD[perceive], RECORD[atom|composite]*) → PRED` — pure citation. *Ledger*: the
    perceive is this step's, earlier in sequence; every slot DERIVE uses appears in its
    SEE ∪ CHANGED; every atom is held in this agent's fabric under the tag `memory_range`
    resolves for it; a composite passes `composer.citation_allowed(rec, "GROUND")` — settled only.
  - `DERIVE (PRED[ground], RECORD[atom]+, PRED[bet]) → PRED` — three forms, one head:
    *positive* (`apply_effect` of the cited atoms in order on the opener frame equals the bet
    on the cells it names); *inverse* (the two actions' recorded deltas compose to identity,
    evidence n from `action_book.inverse_of` stated verbatim); *negative* (`NOT` over a cell
    the [OWN] frontier book records fatal for that action). A typed hole in the bet position
    is the PROBE (§3).
  - `PAY (PRICE) → PRED` — *Ledger*: equals `action_book.cost_of(game, action)` with its n; for
    a composite, `applicability.composite_signature`'s derived price; where the book's cost is
    an explicit null PAY must state the null — a number without evidence refuses as invented.
  - `NEED (RECORD[bet], ACTION) → PRED` — *Ledger*: the bet is this step's, earlier in sequence
    (W1's F1 rule, identical); the action is the one DERIVE ran or the probe names; anchor as
    data.
- **Terminals:** `PERCEIVE(SEE*, CHANGED*, SETTLE?, STAND*) → RECORD`; `BET(WANT, GROUND,
  DERIVE, PAY) → RECORD`; `ACT(NEED) → RECORD`. Links: BET's GROUND consumes a PERCEIVE-
  produced RECORD; ACT's NEED consumes a BET-produced RECORD.
- **The basis rule applies to this layer**: heads grow or merge only on a composition failure
  surfaced as a refusal with a named head. Nine is a hypothesis this stage tests.

## 2 · The three checks per clause — and what each refuses
Every clause pays in exactly one currency; every refusal names the failing head and a fixed
reason token (never prose):
- **Ledger** (fabric, narration/gate streams, action book, composite records): `not-held`
  (atom absent or tag wrong), `not-earlier` / `wrong-step` (precedence), `not-in-perceive`,
  `unsettled-composite` (GROUND), `price-mismatch` / `price-invented` (PAY), `false-ignorance`
  (probe), `standing-mismatch` (STAND).
- **Executable** (`apply_effect`, delta composition, frame lookup, residual recompute):
  `mismatch` — well-formed-and-false dies here; the interpreter is the world's.
- **Completeness** (`compute_d` once per step — the call the loop already makes):
  `unreported-change` (a differing cell no clause covers), `false-change` (a clause outside
  the diff). Never economised: a cost overrun is a finding (§6).
- **Parse** precedes all three: `compose()` raises → `ill-typed` at the offending head; it
  never reaches a currency.
Verdict per terminal: pass / refuse(head, token); a triple passes iff all three pass. The first
refusal is the named one; later clauses are still checked and logged (shadow wants the whole
picture, not the first cut).

## 3 · The probe — the only fallback, and its own ledger check
Form: a BET whose DERIVE carries a typed hole in the bet position and names one action — "I do
not know what action N does here; I want to see" — WANT holed or concrete, GROUND citing the
perceive, PAY as for any action. Check: ledger against the book AND applicability here — valid
iff `effect_summary(game, N)` is the explicit-null shape, OR no held atom for N matches an
anchor in the opener frame (`apply_effect` None for every held atom of N). A held atom that
applies here makes "I don't know" false: `false-ignorance` at DERIVE. **No loaded book →
`book-absent`**, a named non-verdict counted apart — absence of the ledger is not evidence of
ignorance, and an unverdicted probe is never counted valid. Probes also carry (shadow-only,
gating nothing) the salvaged `discrimination()` score over the book's recorded effect
distribution for N — the value reading the curve lacks; rank never confers validity (§5).

## 4 · The rollout ladder and what shadow logs
`REASONING_GATE` ∈ off / observe / active — primitive_ledger's ladder, resolved once at loop
init and narrated once (like the ARM record). **Default `observe`** (an inert default would
measure nothing). `off`: no evaluation, no records. `observe`: evaluate, log, never block.
`active`: NOT BUILT in stage 1 — resolves to observe and emits one downgrade record; the value
exists so stage 2 is a flip, not a rename. Counters, separate by construction: `evaluated`,
`pass`, `would_refuse` (observe), `refuse` (active; structurally zero here), `unverdicted`,
`unbuildable`, `replay`, `errors`. Per non-replay action, one record per terminal plus a
summary: step, gate ids, spine BET `ref`, class ∈ {derivation, negative-derivation, probe,
unbuildable}, rung, the action's book evidence stratum (`floor(log2(n+1))`, n = atoms+traces —
doubling = one stratum up, so the hard floor's "doubled" is the stratum's own unit), verdicts
with head+token, completeness counts (differing / reported / unreported), gate wall-clock ms.
Class is assigned by what the loop held: a plan's atoms → derivation; a frontier-book exclusion
→ negative; an exploration rung or nothing held → probe; a state the builder cannot render →
`unbuildable` with the missing clause named (how the 45% unlabeled decomposes). Replay steps
are not evaluated, counted `replay` (F3's law, inherited).

## 5 · Salvage with citations, and the SEAMS (each a constructed case)
Salvaged: grammar.py primes + `compose()` + typed hole (new-horse); `no_posthoc.py`'s
import-time AST wall; `primitive_ledger.py`'s off/observe/active ladder with its would-revert /
revert split; `objective_validator.py`'s `Discrepancy(measure, active)`; `question_tropism.py`'s
`discrimination()` + ladder (all main); `action_book` reads and `composer.is_citable` /
`citation_allowed` (this tree). Each seam is new code with its own constructed case:
- **wall × utterance-builder**: the gate module carries its own GUARDED list (the WANT/GROUND/
  DERIVE/NEED builders) and AFTER_NAMES extended with the loop's outcome names (`post_array`,
  `after`, `observed`, `_narr_settle`), checked at the gate module's import. Case: a builder
  variant whose DERIVE reads `post_array` fails import; the shipped builder passes; the SETTLE
  builder, which legitimately reads the opener frame (last step's outcome under its opener
  name), passes — the wall guards predicates by name; labels are exempt.
- **ladder × verdicts**: one constructed false clause under all three values — off: nothing
  recorded; observe: `would_refuse`=1, `refuse`=0, action unchanged; active: identical to
  observe plus exactly one downgrade record. `refuse`=0 asserted across the whole suite.
- **Discrepancy × compute_d**: WANT compiles to `Discrepancy(measure = compute_d["differing"]
  on the cited cells, active = those cells)`. Seam: `compute_d` returns −1 on shape mismatch (a
  non-answer) while Discrepancy's measure is non-negative with 0 = holds. Case: a mismatched
  reference refuses WANT `misaligned` (never read as satisfied or as a magnitude); differing=0
  refuses `vacuous`; differing>0 passes with active = the cells.
- **tropism × probe-validity**: rank and validity are independent. Case: a high-score probe on
  a rich-evidence action refuses `false-ignorance`; a score-0 probe on a null-shape action
  passes. The score is a recorded field, never a verdict input; the question generator is not
  transferred — the "questions" are actions in contexts, supplied by the builder.
- **composer-utterances × gate-requests** (composer design amendment 4, the shared line): a
  COMPOSED `compose_attempt` result renders to a BET — WANT = the composer's, GROUND = the
  perceive + each part (settled composites only), DERIVE = the chain re-applied seam by seam
  with the same `apply_effect`, PAY = the derived price (None → explicit null, never a number).
  Case: one constructed composed result renders and passes with the gate's predicted frame
  equal to `frames[-1]`; a `want-underivable` result renders to a named WANT refusal, not a
  silent drop. Either design changing its WANT shape alone breaks this case — the seam defect.
- **is_citable × GROUND**: `citation_allowed(rec, "GROUND")` is GROUND's ledger for composites;
  the same record in DERIVE's bet position (the driven chain IS the bet) is accepted. Case: an
  unsettled composite refused at GROUND (`unsettled-composite`), accepted as the bet; settled
  flips exactly the former (stage 4's F2, re-asserted at the gate's head).

## 6 · Falsifiers (`tests/gate/test_reasoning_gate_stage1.py`, house style)
- **F1 · wire checks, per head**: for each of the nine heads a constructed TRUE clause passes
  and a constructed FALSE clause refuses with THAT head named — 18 cases, no head exempt. A
  head whose false case cannot be constructed is reported "no check" and the stage fails.
- **F2 · precedence type-checks**: GROUND citing a non-RECORD → `ill-typed` at GROUND (parse,
  not ledger); BET citing a later-sequence or other-step PERCEIVE → `not-earlier`/`wrong-step`;
  NEED citing a PERCEIVE (right type, wrong kind) → ledger refusal at NEED.
- **F3 · completeness**: a frame pair with k differing cells and a PERCEIVE reporting k−1 →
  `unreported-change`; all k passes; an extra unchanged cell → `false-change`. Cost: gate
  wall-clock per step under W1's ≤5% cap against the live baseline; an overrun is REPORTED as
  a cost finding — the check is never trimmed to meet it.
- **F4 · probe-ignorance**: a probe for an action with a held, applicable atom → `false-
  ignorance`; the same probe with that atom absent → passes; no book → `book-absent`.
- **F5 · shadow-no-block (structural)**: an AST assertion that the hook's return is unbound
  and `action_num` is not assigned after it in `_narr_bet`; plus a constructed episode whose
  action sequence is byte-identical under off and observe. `refuse` = 0 by identity.
- **F6 · the three-number report**: per game, derivations : negative derivations : probes as
  three numbers, never folded, with `unverdicted`/`unbuildable`/`replay` beside them, each
  stratified by evidence stratum. A constructed stream with known class counts reproduces
  them exactly (R4 on the gate stream).
- **Known-negatives**: replay steps produce no gate record; a step with no spine BET (W1's
  refused act) records `unbuildable: no-bet`, not a refusal; an unloaded book yields
  `book-absent` on PAY and probes, never a pass; the downgrade record appears exactly once.
- **Calibration read** (reported, not a falsifier — the repurposed permutation null): pass
  rate by rung class. Pre-named: plan-driven rungs pass as derivations at the highest rate;
  exploration rungs passing as derivations above them = the builder misclassifying — a
  builder finding, reported before any coverage number is believed.

## 7 · The question this stage answers — and what it does not claim
Answers: **true coverage on live play** — derivations : negative derivations : probes per game
as a curve over action-book evidence stratum, plus the would-refuse rate per head (which heads
refuse, how often, with which tokens — the layer's own composition-failure signal). Read per
the probe-share pin: probes high only in thin strata = library young; flat-high across rich
strata after circulation = grammar/coverage failing, localised by context; the hard floor
(richest stratum's probe share not below its start after moving up one stratum) reported by
name when it trips. Side effect: today's 45% unlabeled decomposed into the four classes.
Does NOT claim: enforcement (no path blocks; stage 2 is Seat 3's); that a pass is rationality
(a pass is a request the world and the ledger could not refute); that nine heads are the right
nine (a head that never composes or always refuses is a finding); that the builder's translation
is the agent's voice (it is ours; the calibration read watches it); that SETTLE's recompute is
exact for every slot kind (bound by identity at build time; any kind it cannot recompute is
`unverdicted`).

## 8 · UNDO
Remove the one call site in `_narr_bet`; delete the gate module (its wall goes with it); drop
the `gate` allowlist entry and the WIRING_REGISTRY rows. The `gate` stream stays as readable
history. narration.py, action_book.py, composer.py, discrepancy.py, effects.py are untouched by
this stage (asserted by diff). Nothing stored is destroyed; no decision ever depended on a
verdict, so there is no behaviour to unwind.

## SEAT 3 RULING (2026-08-21): ACCEPTED — with the stage-2 deadline as a MECHANISM
PERCEIVE-not-relocated is right for shadow. The deadline lives at the cause's site: the
gate topic's own code carries a marker (a constant + a gate test that FAILS if stage 2's
enforcement flag is enabled while the opener-side PERCEIVE still lives on the `gate` topic
rather than in the agent's spine). A convention that decides outcomes is not a convention.

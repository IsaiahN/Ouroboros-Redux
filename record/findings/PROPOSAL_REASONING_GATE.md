# PROPOSAL — GATING ACTIONS BEHIND REASONING (2026-08-20, requested by Seat 3)

**A proposal, not a build.** The idea: no action emits without a reasoned derivation the
gate accepts. Bet-before-act extended one step — the ACT already refuses without a BET;
this makes it refuse without a derivation. No second channel, so decoration becomes
structurally impossible.

## 0 · The coverage number (measured first, from 20,952 live ACT records)

| class | share | statable today as… |
|---|---|---|
| `controlled_movement_planning` + `smart_action_selection` | **2.1%** | a full derivation ("primitives X,Y,Z, so action 5 next") |
| `wall_aware_navigation` | **19.2%** | a **negative derivation** — "this cell is one I know kills ([OWN] frontier book), so NOT action X." A real because-clause invoking an earned prior. |
| `weighted_random` / `survey` / `explore` / `grid_exploration` / `exploration_phase` | **33.7%** | only a **probe** — "I do not know what this does; I want to see" |
| unlabeled | **45.0%** | undecomposed (replay, drive pre-empts, older writer) — must be split before any total is trusted |

**Honest headline: ~2% of actions are positively derivable in today's grammar; ~21% counting
negative derivations; a third are probes; nearly half need decomposition first.** The gap is
real and it is exactly where g7=0 predicted it would be: derivations require plans and an
action vocabulary, and neither exists as something the agent HOLDS.

## 1 · What an action request contains

One utterance, four clauses, three vocabularies composing (NSM connectives in fixed tokens,
exactly as narration already does):

```
WANT      : the goal — a diff target (compute_d names the cells) or an abduced predicate
GROUND    : "this one" observations (slots) + invoked atoms/primitives BY ID with
            provenance tags ([EP]/[OWN]/[COL] — already in narration)
DERIVATION: the executable step — atoms applied to ground → predicted state (BECAUSE);
            or an inverse-pair claim for repairs (action 4 undoes action 3, evidence n=k)
PRICE     : the acknowledged cost, from the action book (budget delta; what undo forfeits)
ACTION    : the action number + anchor (SO I NEED)
```

Seat 3's two target utterances render directly: the repair = WANT(restore prior state) +
GROUND(prior ACT record by seq — exists since W1) + DERIVATION(inverse-pair evidence) +
PRICE(undo cost) + ACTION(4). The composition = WANT(goal) + GROUND(primitives X,Y,Z held)
+ DERIVATION(composed application) + ACTION(5, position-in-subroutine).

## 2 · What the gate checks — the answer to the design problem

> **The gate is an EXECUTOR and a LEDGER, never a JUDGE.** It holds no authored rule set.

Every clause is one of two checkable kinds:
- **Ledger claims** → looked up in the agent's own earned fabric: *do you hold primitive X*
  (provenance tags), *is that your prior action 3* (narration seq), *is the price you
  acknowledge the recorded price* (action book, derived from traces).
- **Executable claims** → run through the world's own mechanics: apply the stated atoms to
  the stated ground with `apply_effect` — **does the output equal the stated bet?** An
  inverse claim is checked by composing the two actions' recorded deltas to identity.

**This is how "the conclusion follows" avoids checking-against-us:** the rule set is Γ
(earned from the world) plus the interpreter (the world's mechanics). We author neither.
*Well-formed-and-false dies at execution* — a fluent wrong derivation fails when its stated
premises are run; a claimed primitive the agent never earned fails the ledger; a price
misstated fails against the recorded schedule. The trap Seat 3 named (a grammar rich enough
to state a rational request states a fluent wrong one) is closed by making every clause pay
in one of those two currencies. REJECTS name the failing clause and are narrated — a
refusal is data.

## 3 · The thinnest vocabulary, and what is missing

**The action vocabulary is the thinnest — it does not exist as anything the agent holds.**
But it is DERIVABLE, not authorable: every atom already carries its action int, so per
action we can derive: observed effect distribution, inverse pairings (delta composition to
identity, with evidence counts), observed costs (the traces' budget columns — currently
produced-and-unread). **THE ACTION BOOK is stage 0 of this proposal**: derived from Γ and
traces, per-game, held as data the agent can cite. Authored action semantics would be
checking-against-us; derived ones are the agent's own history made citable.

Primitive/prior inventory for the two utterances: reference-to-prior-action **EXISTS** (W1
narration seq), sequence-position **EXISTS**, direction **PARTIAL** (translate ttypes,
colour_delta), reversal/inverse **MISSING as held data — derivable** (stage 0), cost-of-
action **MISSING as held data — derivable** (stage 0). The NSM grammar **EXISTS** (new-horse
primes; narration's fixed tokens are already a subset).

## 4 · When an agent cannot produce a valid request

**One fallback utterance and only one: the epistemic probe** — *"I do not know what action
N does here; I want to see."* And the gate checks THAT claim too: **a probe is valid
exactly where the action book shows insufficient evidence for this action in this context.**
A false "I don't know" fails the ledger like any other false clause. So exploration becomes
the rational statement of true ignorance — priced, narrated, and impossible to use as a
bypass where knowledge exists. No third channel.

The coverage finding is then a ratio the beat can watch: **derivations : probes**. A
healthy learner's probe share falls as its action book fills. If most actions remain
underivable after the action book exists, that is a finding about the grammar or the
library — reported, never patched by weakening.

## 5 · Relation to the falsifier arms — supersedes the question, reuses the machinery

The arms ask *does narration change behaviour?* The gate makes narration the only route, so
the question transforms into the better one Seat 3 named: **what fraction of behaviour can
survive the gate?** Migration path:
- **Stage 0**: derive the action book (a read + a derived artifact; no behaviour change).
- **Stage 1 — SHADOW MODE**: the gate evaluates every action and logs pass/refuse-with-
  failing-clause, **blocking nothing**. This measures true coverage continuously on live
  play (decomposing today's 45% unlabeled as a side effect), debugs the gate against the
  world before it holds power, and reuses the arms build directly — the consumption wires
  ARE the gate's ledger reads, and the wire check is the gate's own sensitivity test.
- **Stage 2 — enforcement**, flipped per-worker once shadow coverage is stable and the
  refusal rate is a finding rather than a surprise. A refusal storm at flip = the grammar's
  coverage finding, reported with the gate at full strength.

The pinned permutation null is repurposed, not discarded: shadow-mode agreement between
gate verdicts and actual behaviour, by rung class, is the calibration read.

## Recommendation
Stage 0 is cheap and pays regardless of every later decision (the action book also feeds
W2c's retention and the persistence monitor). Stage 1 costs one builder and answers Seat
3's coverage question with a continuous number instead of today's proxy. Stage 2 is the
constitutional change and stays at Seat 3's word, taken only on shadow evidence.


---

# AMENDMENT (2026-08-20, Seat 3): THREE UTTERANCES, NOT ONE — PERCEIVE STANDS ALONE

**The chain: PERCEIVE → BET → ACT, two precedence links** (W1's ACT-cites-earlier-BET rule
extended one link, enforced identically). The BET's GROUND becomes pure citation — a
perceive-record id + atom ids — and the request loses its heaviest clause. The spine's
existing outcome-side PERCEIVE relocates: **one record settles bet N−1 and grounds bet N**
— the opener of the next step rather than the closer of the last.

**PERCEIVE in the grammar:**
- `SEE` — per-slot state claims ("this one is at (x,y), colour c")
- `CHANGED` — per-slot deltas since the last frame ("this one moved left" / "nothing here")
- `SETTLE` — the previous bet BY ID: held or broke, and by how much ("I thought X; it is
  not so, by d cells")
- `STAND` — hypothesis standings: strengthened / weakened / died this frame

**PERCEIVE is the most checkable utterance of the three** — every clause executable or
ledger-bound: SEE verifies against the actual frame (exact, cheap); CHANGED must equal the
mechanical diff (`compute_d`, one call); SETTLE must cite an existing bet AND state the
verdict the mechanical comparison produces; STAND must be consistent with the settle (a
hypothesis whose prediction just broke cannot strengthen). *Proving it looked is a real
check: an agent that assumed states a stale feature and fails against the grid.*

**The completeness rule (closes selective perception):** the gate diffs the frames itself;
**any unreported change is a violation**. PERCEIVE must be complete-on-changes, not merely
true. You cannot ground on what you did not report, and you cannot omit what changed.

**Gate checks added:** BET cites a same-step earlier-sequence PERCEIVE; the BET's GROUND
appears in that perceive's reported content; the previous bet is settled in this perceive
(loop-closure checked, not assumed). **And the new capability: a PERCEIVE with no following
BET is a first-class record — the agent looked and declined, and that produced a residual.**
Today, no request means no record of having looked; under the split, step 1 of the loop
exists as evidence in the agent's own voice.

Stage structure unchanged (action book → shadow → enforcement); the shadow gate now scores
all three utterances and their two links.


## THE PERCEIVE-COST PIN (2026-08-20, Seat 4's question answered before any build)

**SEE scopes to `cited ∪ changed` — it scales with what happened, never with the board.**
- The agent reports: every slot that CHANGED since the last frame, plus every slot its BET
  will CITE, plus **one closing clause — "nothing else changed" — which the gate verifies
  mechanically** with the same frame diff it already computes. Unchanged-and-uncited slots
  are covered by that single verified clause, not enumerated.
- **Reporting cost**: O(changed + cited) — median change is 26 cells at 3.9% density, so
  typical perceives are tens of claims, not 4,096. **Checking cost**: `compute_d` once per
  step — which the loop ALREADY computes for routing, so the gate's completeness check has
  ~zero marginal cost — plus per-cited-slot lookups.
- W1's ≤5% wall-clock narration cap GOVERNS this utterance like the others, measured
  against live baseline at the shadow stage. If a game's change density blows the budget,
  that is reported as a cost finding, not absorbed by trimming the completeness rule —
  completeness is load-bearing (it closes selective perception) and is the one clause that
  may never be economised.

Both halves scale with events, not area — pinned before the third profile window has to
discover it.


## THE PROBE-SHARE PIN (Seat 3's addition 2 — named before stage 2, so a high rate at flip
## gets read instead of argued)

The probe is the pressure valve: honest, valid, and capable of carrying everything if
coverage is thin. What a given share MEANS is pinned now:

- **The number alone decides nothing. The TRAJECTORY against the action book's fill does.**
  Probe share is read jointly with action-book evidence density (per action, per game):
  - **Library-young (healthy)**: probe share high WHERE evidence is thin, and falling as
    evidence accumulates — the learning curve. Expected on new games and fresh workers.
  - **GATE-FAILING (the finding)**: probe share high WHERE THE ACTION BOOK IS RICH — the
    agent holds the evidence to derive and routes through "I don't know" anyway. Since the
    gate rejects false ignorance (the ledger check), a high probe rate in evidence-rich
    contexts that PASSES the gate means the book's evidence is not composable into
    derivations — a grammar/coverage failure, localised to the contexts where it happens.
- **The pinned discriminator**: probe-share stratified by action-book evidence density,
  reported as a curve, not a scalar. Flat-high across rich strata after circulation =
  gate/grammar failing. High only in thin strata = library young. The stage-2 flip
  decision cites this curve, and no scalar threshold is invented at flip time.
- **One hard floor, stated so drift is visible**: if fleet-wide probe share in the RICHEST
  evidence stratum has not fallen below its own starting value after the stratum doubled
  its evidence, the gate is failing there regardless of any other argument.

## THE THREE-NUMBER RULE (Seat 3's addition 3)
The beat reports **derivations : negative derivations : probes** as three numbers, never
folded. Negative derivations (earned-prior exclusions — 19.2% today) are real
because-clauses and the 2.1% headline undersells what is already statable; folding them
either way hides the thing the gate is supposed to grow.

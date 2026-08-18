# THE KNOB REGISTRY — what may be tuned, what may never be

LAW (Isaiah, 2026-08-14): knobs are tuned ALL AT ONCE, GLOBALLY, FOR ALL GAMES — never
per-game ("25 small defensible adjustments later you have a system fitted to 25 games").
NOTHING touching what counts as success is in scope. A knob change is a prereg'd arm
(the three-arm mechanism) judged on evidence-per-budget ACROSS ALL GAMES vs control.
The OOD lint enforces the deeper rule mechanically: no game-conditioned knob values.

## REGISTER F — FROZEN (defines success; changing these changes what "winning" means;
## Isaiah + prereg + explicit waiver required; agents NEVER touch)
F1  Mint MDL acceptance: cost < 0.9*R, R = 2*changed+1; bbox < 0.5*board  (mint.py)
F2  Verification bar: 2x TRANSFERRED before any DRIVE (the wheel rule)   (cognitive_loop)
F3  Level wins as the only currency; the pariah rule (d->0 without level advance)
F4  Affect replay purity (pure fn of ledger prefix); desperation RAISES the mint bar
F5  The write-contracts: affect/starvation/swallow/LP steer ONLY, never price
F6  Membrane law (playback never crosses into fabric)
F7  Kin-echo exclusion in reputation; imported-witness law; the answer firewall
F8  Frontier dead rule: >= 2 independent reports (evidence semantics, not a dial)
F9  Evidence-preserving cleanup (wins/levels/score>0 rows kept forever)
F10 win_detected / level_completions semantics; scoreboard derivation

## REGISTER G — GLOBAL-TUNABLE (one value for all games; tuned via prereg'd arms only)
Exploration & attention:
G1  affect seed_bias FLOOR=1.0 CEIL=3.0 WINDOW=20                        (affect.py)
G2  starvation_steer: +0.25/code, cap 2.0; SWALLOW_STEP=0.1              (affect.py)
G3  LP drive: CEIL=4.0, windows 32 (queue) / 64 (verdicts); ARM assignment (lp_drive.py)
G4  mute-probe candidate cap 5 -> <=10 under starvation                  (cognitive_loop)
G5  movement bias: MOVE_NOOP_MIN=3, MOVE_NOOP_RATE=0.8, MOVE_BIAS=3      (frontier/loop)
G6  salient prefix: SALIENT_K=3, replay p=0.2; mastery-lite 0.2+0.6*succ (player)
Vocabulary & learning:
G7  mint surprise: weight 1/(1+seen), SEEN_CAP=4096 LRU                  (mint.py)
G8  mint bar range (the affect mint_bar channel bounds) — gates OFFERS, never acceptance
G9  ConditionalMiner: per_key=8, max_keys=16, max_condition_cells=4      (effects.py)
G10 class fission: min_obs=3, purity=0.75                                (bank.py)
G11 agent motion: min_evidence=3, adjacency Chebyshev<=1, history 16     (bank.py)
G12 goal abduction: credibility threshold >=2 co-occurrences             (goal_abduction)
Search & import:
G13 planner: MAX_DEPTH=8, MAX_NODES=2000                                 (planner.py)
G14 consumer: budget_n=8/episode; near-miss = all-but-one; 1 retry       (consumer.py)
G15 rho: RHO_COLLAPSE=0.9                                                (rho.py)
G16 starvation thresholds: PLAN_N=50, BOOK_N=10                          (starvation.py)
G22 CORPSE GUARD: CORPSE_GUARD=True [GUESSED] — the salient-prefix death guard
    (never bank a terminal step; refuse selecting a prefix whose LAST RECORDED
    OUTCOME was `died`). Env CORPSE_GUARD outranks the class flag
    CognitiveGamePlayer.CORPSE_GUARD; =0/false/no/off restores pre-guard banking AND
    selection byte-identically. Amendment 11. (cognitive_game_player.py)
G23 DEAD DEDUP: DEAD_DEDUP=True [GUESSED] — the frontier dead-cell counting UNIT:
    DISTINCT RECORDS (one episode = one report per cell) instead of list entries, at
    BOTH ends (record_harvest dedups before banking; load_harvest counts per record,
    correcting already-banked history at READ time). Env DEAD_DEDUP outranks the module
    flag frontier.DEAD_DEDUP; =0/false/no/off/empty restores per-entry counting
    byte-identically on BOTH ends. NOT F8: the >=2 THRESHOLD is untouched — this fixes
    what counts as ONE report. Amendment 12. (engines/egocentric/frontier.py)
G21 RANKED DRAIN: DRAIN_WINDOW=512 [GUESSED] newest pending records ranked per pass;
    key [GUESSED] = (1) CHARACTERIZED FIRST (all 5 INVARIANTS present)
    (2) LARGEST RESIDUAL (3) RECENCY. Toggle DRAIN_RANKED (env outranks the
    module flag); =0 restores FIFO byte-identically. Amendment 10. (consumer.py)
Economy:
G17 role multipliers: pioneer 1.5 / generalist 1.2 / optimizer 1.0 / exploiter 0.8
G18 handoff funding: allowance*(1+levels_replayed)-replay_cost           (player)

## REGISTER O — OPS (infrastructure; proctor-tuned freely; no cognitive content)
O1 supervisor: MEM_CAP=1200MB, RECYCLE=120min, VACUUM=200MB, DB_CAP=600MB, POLL=60s
O2 janitor: 2MB stream threshold; settlements fold window 100
O3 population shape: 25 pinned workers, pop 6, agents/gen 4, max-gen 50

## SELF-TUNING (the later mechanism, principle fixed now)
Agents may eventually tune REGISTER G ONLY, by the mechanism already live for the LP
drive: a proposed knob value is an ARM, assigned across a worker subset spanning many
games, judged on evidence-per-budget vs control ACROSS ALL games, adopted swarm-wide or
rejected. One value for all games is preserved BY CONSTRUCTION (the arm sets a global,
never a per-game override). Register F is not reachable by this mechanism: the tuner
is priced by F and a market cannot price its own currency.

## AMENDMENT 1 (2026-08-14, six-point review — four derived, two imported)
A1 (F11) SIG_CLASS IS FROZEN: the sigma-projection defining atom identity (rho.py
   sig_class + consumer INVARIANTS) is REGISTER F — identity decides the NOVELTY guard
   (phi not-in atoms(Gamma)), rho, collapse-4, and bracket matching. A free identity is
   a free guard.
A2 (REGISTER L — MEASURED LATENTS, new): quantities that are PER-REGIME MEASURABLES,
   never constants and never knobs — estimated online from the ledger by a GLOBAL
   estimator (the estimator is the socket, the estimate is content; latents are learned
   state, not game-conditioned tuning). L1: planner cost_per_action (currently 1.0 —
   measured non-monotonic 1,2,2,1,2,1,2 across one game's levels; must become a per-
   game+level ledger estimate). AUDIT OPEN: anything keyed to board scale, action cost,
   or level structure. A latent misfiled as a knob is invisible to the arm mechanism.
A3 (G8 SPLIT): the mint-bar CEILING is F (an unbounded bar = acceptance-by-starvation,
   SUPPORT -> 0 kills the guard product); the VALUE within the ceiling stays G.
A4 (G17/G18 -> G*, self-tuning-excluded): role multipliers + handoff funding decide
   WHICH EVIDENCE EXISTS — a tuner moving them edits the books it is judged on (the
   market-currency law one step earlier). They remain arm-testable by the proctor with
   Isaiah's sign-off; the agent self-tuning mechanism can NEVER reach them.
A5 (PROVENANCE COLUMN): every G row is marked MEASURED / DERIVED / GUESSED.
   GUESSED today (will read as settled in a month if unmarked): RHO_COLLAPSE=0.9,
   LP CEIL=4.0, fission purity=0.75, MOVE_NOOP_RATE=0.8, SALIENT_K=3, replay p=0.2,
   starvation +0.25/cap 2.0, probe cap 10, consumer budget_n=8, PLAN_N=50/BOOK_N=10.
   DERIVED: n_eff formula, window laws, Chebyshev adjacency. MEASURED: MAX_NODES=2000
   (hang repro), SEEN_CAP=4096 (soak), MEM_CAP/RECYCLE (live ops).
A6 (SELF-TUNING NULL + RATE LIMIT): the mechanism REQUIRES (a) a losing condition —
   an arm that fails to beat control REVERTS and is logged; adoption criteria without
   a null move the anchor one way; (b) ONE knob-arm at a time swarm-wide with a
   cooldown (>= one full arm-experiment window) — 25 workers cannot host concurrent
   interfering arms; an uncooled proposer is a random walk charged to throughput.

## AMENDMENT 2 (2026-08-14): THE IDENTITY LADDER (F11 resolved) + honest rho
The rho_bar=0.000 x153-pairs reading was a PARTITION ARTIFACT, not a measurement —
n_eff=18 is an upper bound under a grain where correlation is undetectable. VERIFIED
live: cn04 holds 64 rederivation verdicts for ka59's atom key (cross-mount recognition)
while atom-set rho reads 0 — two sameness notions in play, only one frozen.
F11 IS NOW THE LADDER, frozen as a whole, each ROLE pinned to a rung:
  rung 0 KEY (canonical content hash, position-free) — the novelty guard, the bracket
  rung 1 SIG_CLASS (sigma + ttype + params) — consumer matching, atom-set rho
  rung 2+ COARSENED SIGMA (the redescription rungs) — near-miss retry, cross-game lookup
RHO REPORTING (queued build): rho at rungs 0/1/2 + the REDERIVATION-TRAFFIC channel
(cross-mount verdict recognition counts) — a distribution, not a partition; a
measurement of independence must be capable of reading nonzero.

## AMENDMENT 3 (2026-08-14): THE GRAIN AUDIT — same class as the identity ladder
Audited: every concept operationalized by 2+ components. Findings:
A3-1 "VERIFIED" HAS TWO STORES, ONLY ONE CONSULTED (DEFECT, fix queued): settlements
   now persist atom_key + atom_bin (TRANSFERRED...) but the planner's DRIVE gate reads
   ONLY the in-memory _atom_verified, which RESETS every episode. Consequence: any atom
   — imported atoms especially — must earn 2x TRANSFERRED within a single episode or
   never drives; cross-episode verification evaporates. FIX: hydrate verified counts
   from the books (settlements, game+level-scoped) at loop init; "verified" becomes
   book-derived — one definition, persistent, auditable. The import verdict is
   handicapped until this lands.
A3-2 "LEVEL" HAS TWO CONVENTIONS, UNDECLARED (register): bare _ego_level (harvest/
   frontier context: the completed level; level-up click belongs below) vs
   _ego_level+1 (mint/bank/consumer/goal: the playing level). Both intentional, never
   registered. REGISTERED NOW: streams atoms/verdicts/settlements/import*/goal_
   hypotheses carry PLAYING level; frontier streams carry COMPLETED level. A gate test
   should pin each stream's declared convention.
A3-3 "GAME" HAS TWO GRAINS, BOTH VALID (declare): 4-char prefix (config/role sites,
   game_id[:4]) vs full version id (all knowledge streams). Suffix VERIFIED stable per
   game (ar25-0c556536 across all sessions) — no reset bug. Declared: prefix = ops
   grain, full id = knowledge grain; never compare across grains.
A3-4 "WHEN" (already routed): no shared episode key across streams — verdicts need
   episode id + sigma (the bracket's MISSING). Rides the maintenance pass.

## AMENDMENT 4 (2026-08-14): review riders
A4-1 (G19) HYDRATION READ BOUND: N=500 records/scope (cognitive_loop _hyd_ver).
   Provenance: DERIVED-from-janitor-retention (100 raw survivors) x safety factor 5 —
   but the factor is GUESSED. Register G, arm-testable.
A4-2 WINDOW DEBT (queued maintenance): the .credit/.route char-window gates (7950/8000,
   19985/20000) are proxies for "the wiring call exists inside record_result" and are
   now shaping code placement (15-50 chars slack). WHEN THE BUDGET RUNS OUT: an edit
   inside record_result forces refactor-or-test-amendment. FIX: replace char windows
   with AST-based wiring assertions (same intent, no character economy). Queued.
A4-3 EP ORDINAL: confirmed content-free (instance-local counter; no game/session
   identifiers in logic; OOD lint enforces).

## AMENDMENT 5 (2026-08-14, Isaiah): DEFERRED LIST CLEARED
STRUCK: mutmut nightly, pyright ratchet, cloud heartbeat, alpha/EWMA precision upgrade.
alpha/EWMA RE-ENTRY CONDITION (the only way back): family-selection churn in the books —
the same bank family oscillating TRANSFERRED/BROKEN across episodes on stable mechanics
(the stale-averaging signature). Absent that, it stays struck.

## AMENDMENT 6 (2026-08-14, four flags)
A6-1 alpha/EWMA RE-ENTRY CORRECTED: not churn (that is averaging-too-fast — EWMA fixes
   the OPPOSITE). Trigger: a family whose STANDING STAYS HIGH while its recent-window
   settlement rate DIVERGES from lifetime rate — stuck-trusted, recent BROKENs, no
   oscillation.
A6-2 R_T READABILITY PRE-REGISTERED: R_T is citable only at >= 100 stamped verdicts
   spanning >= 5 games; below that the number is reported as ACCRUING, never as the
   answer. (5 stamped verdicts is not a measurement.)
A6-3 The Register L sweep is run TO LOOK, not to confirm: every board-scale/level-
   structure/action-cost constant gets checked against the RECORD (the ls20 treatment),
   expected-answer-one notwithstanding.
A6-4 PRE-STAGED READ: if cn04 adoption has not occurred by its verdict deadline, the
   immediate next read is the REJECT/NOT-FOUND REASONS on the 66 — does the wheel
   refuse for a readable reason, or does the offer never arrive (consumer never
   matched vs matched-but-unverified vs seeded-but-never-planned).

## AMENDMENT 7 (2026-08-15): FIGURE 2 REV — constitutive anchors vs instruments
"An anchor is legitimate when the question is CONSTITUTIVELY about it. Where it
estimates a fact outside itself it is an INSTRUMENT, and instruments can be wrong on
axes they do not measure."
REGISTER F SPLITS ACCORDINGLY: CONSTITUTIVE (the question is the anchor — level wins,
win_detected semantics, the gate suite for gate-passing, git history for what-landed):
infallible BY DEFINITION, need no violation detector, must never update. FROZEN
INSTRUMENTS (estimate something outside themselves — F11 sig_class estimates sameness;
the MDL inequality estimates worth; the dead-cell rule estimates deadness): frozen for
stability, NOT infallible — each OWES a violation detector (the metamer read is
sig_class's), and each CAN be wrong on unmeasured axes. THE WEEK'S ERROR CLASS NAMED:
every guaranteed-number failure (rho=0, R_T=0, rss=0) was an instrument read as a
constitutive anchor. The ladder's trap-check ("could this number have been anything
else?") is exactly the instrument test — constitutive reads are exempt from it,
instrument reads never are.

## AMENDMENT 8 (2026-08-15): corrections to Amendment 7 (the split stands; two conflations fixed)
A8-1 TWO TRAPS, TWO CHECKS — kept SEPARATE in the ladder:
   GUARANTEED-BY-CONSTRUCTION: "could this number have been anything else?" — fails
   BEFORE the instrument measures (rho=0 at a collision-forbidding grain; a key compared
   to itself). Arithmetic wearing a result's clothes.
   INSTRUMENT ERROR: "what axis does this NOT measure?" — the number is real and
   incomplete (the metamer class). Collapsing these loses the first, which is the one
   that has cost incidents.
A8-2 THE ANCHOR IS CONSTITUTIVE; THE READING OF IT IS AN INSTRUMENT and inherits every
   instrument failure mode (Fig 10 panel 2: the ground does not decay, the channel
   does — the mid-animation percept is the proof). "Constitutive all the way down" is
   STRUCK: it is precisely the belief that lets a broken reading pass unexamined.
A8-3 THE CONSTITUTIVE ANCHORS, EXPLICITLY (short by law — >4 items means something was
   promoted that should not have been):
   1. WIN/LEVEL SEMANTICS (the mission currency: rung 0's question IS this anchor)
   2. GATE-PASSING (a build passes iff the suite passes; the question is the suite)
   3. ISAIAH'S RULINGS ON DESIGN LAW (what the law is, is constitutively his word)
   Git history is a RECORD, not an anchor — nothing is graded by it. Everything else
   in the system is an instrument or a frozen instrument.

## AMENDMENT 9 (2026-08-16): movement-stack first activation (Register G rows)
A9-1 NAV_BIAS_P = 0.5 (cognitive_loop.py) — cap on the [NAV] GridNav steer's share of
   the blind movement draw (actions 1-4). Provenance: GUESSED. Register G,
   arm-testable. NOTE: the future arm must distinguish testing the CAP from testing
   the CAPABILITY.
A9-2 RESET_MIN_RUN = 3 (cognitive_loop.py) — frame-changing steps that make a run
   "solid" before an anchor-revert counts as a [RESET]. Provenance: GUESSED. The
   counter it feeds is INSTRUMENTATION ONLY (scope ruling 2026-08-16): it reports;
   a selection guard may enter SINGLY, later, judged against the counter's books.
A9-3 THE MOVEMENT STACK'S REGISTERED VERDICT IS A COMPARISON against the incumbent,
   not proof-of-firing — bias-not-veto can degrade silently, so the read must be
   able to say WORSE, not just ALIVE. Books-read: (1) collective "frontier_harvest"
   kind="move" records (per-episode, per-action 1-5 changed/unchanged counts,
   banked by the player at episode end) -> per-game+level move effectiveness;
   (2) personal "starvation" settle records (level + budget_spent per episode) ->
   level progress per budget on the mover games; (3) the "[NAV] episode steers=N"
   end_game settle line marks the arm: steers>0 (nav-biased) vs steers=0
   (blind-explore incumbent) episodes of the SAME game+level. WORSE on (1) or (2)
   for steers>0 episodes is a real verdict the wheel must hear.

## AMENDMENT 10 (2026-08-17): THE RANKED DRAIN (G21) — one knob row, two GUESSES
A10-1 DRAIN_WINDOW = 512 (consumer.py). The number of PENDING records — taken from the
   NEWEST end — that the drain ranks per pass. Provenance: GUESSED, Register G,
   arm-testable. IT IS A BOUND, NOT A PREFERENCE: the point is that the ~370k
   pre-characterization backlog is never sorted, so a characterized record OLDER than
   the window is deliberately NOT promoted (gated by test_ranked_drain.py's bound
   falsifier). The window is anchored at the NEWEST end because that is where the
   82,301 complete sigmas live; a front-anchored window would rank the backlog against
   itself forever and change nothing.
A10-2 THE KEY ORDER is itself GUESSED, and it is the more dangerous half — it decides
   WHICH EVIDENCE EXISTS, so a future arm must test the ORDER (characterized-first vs
   largest-residual-first), not only the window SIZE. Same distinction as A9-1's
   cap-vs-capability note.
A10-3 THE OFF-ARM IS THE RECEIPT (CLAIM.md's ablation constraint): DRAIN_RANKED — the
   environment variable outranks the module flag consumer.DRAIN_RANKED — set to
   0/false/no/off returns pending() VERBATIM, oldest-first, producing BYTE-IDENTICAL
   streams on disk. Shipped as a PASSING test at ship time, not a future intention.
A10-4 REGISTERED VERDICT (THE_LADDER, wave 1, 2 beats post-deploy): the decline rate
   falls and candidates>0 appear. LOSING CONDITION, stated: if declines stay at ~100%
   WITH characterized records reaching the guard, the queue-order diagnosis was wrong
   and the ordering was not the blocker — revert (one call site), do not re-tune the
   window. NOT-MEASURED CONDITION: a beat below rung-0b's MIN_EXPOSURE floor reads
   UNMEASURED, never "no effect".
A10-5 NOT A KNOB (recorded so it is not mistaken for one): the ORIGIN MARKER shipped in
   the same wave writes origin/mint_seq/source_game at mint and seed time. It has no
   tunable value and no arm — it is instrumentation, and its absence-reads-UNKNOWN law
   is a Register F-adjacent semantic (a default that says "local" would be the defect).

## AMENDMENT 11 (2026-08-17): THE CORPSE GUARD (G22) — one toggle, no numeric dial
A11-1 CORPSE_GUARD = True (cognitive_game_player.py). Provenance: GUESSED, Register G,
   arm-testable. IT IS A TOGGLE, NOT A VALUE: the build deliberately introduces NO
   numeric knob — no candidate-scan bound (the alternatives per game+level are single
   digits; a bound would silently make older prefixes unreachable, the DRAIN_WINDOW
   failure mode one organ over), no decay, no death-count threshold. ONE recorded death
   refuses; the value that could have been tuned (how many deaths before refusal) is
   fixed at 1 BY THE PREREG, and moving it would be a new arm, not a tuning.
A11-2 THE OFF-ARM IS THE RECEIPT (CLAIM.md's ablation constraint): the environment
   variable CORPSE_GUARD outranks the class flag; 0/false/no/off/empty reproduces
   PRE-GUARD behaviour byte-identically on BOTH sides — banking (the death step banks;
   prefix_json bytes unchanged, because the `terminal` marker is stripped before
   serialization in BOTH arms) and selection (the original ORDER BY uses DESC,
   created_at ASC LIMIT 1 runs verbatim under the off branch). Shipped as PASSING tests
   (tests/gate/test_corpse_guard.py::TestTheOffArm), not a future intention.
A11-3 REGISTERED VERDICT (PREREG_CORPSE_GUARD, 2 beats): [SALIENT] replays stop
   terminating in GAME_OVER on the first cognitive action; cognitive actions available
   at the frontier rise above 1. LOSING CONDITION, stated: if replays still end in death
   with the guard ON, the death is not coming from the banked prefix — the diagnosis was
   wrong; REVERT, do not extend the guard. NOT-MEASURED CONDITION: a beat below rung-0b's
   MIN_EXPOSURE floor reads UNMEASURED, never "no effect".
A11-4 NOT A KNOB, recorded so it is not mistaken for one: the OUTCOME VOCABULARY
   (reached_level / died / aborted) is a SEMANTIC, and `aborted` is a UNION (divergence,
   API break, and a clean run that neither died nor levelled) — an instance of the
   INEXPRESSIBLE-STATE GENUS, logged rather than hidden. Only `died` is load-bearing
   today (it is the only value that refuses selection), so the conflation costs nothing
   until someone asks how often replays merely fizzle; splitting it needs its own prereg.

## AMENDMENT 12 (2026-08-17): THE DEAD DEDUP (G23) — a UNIT correction, not a threshold
A12-1 DEAD_DEDUP = True (engines/egocentric/frontier.py). Provenance: GUESSED, Register
   G, arm-testable. WHAT IT IS NOT: it does not touch F8. F8 freezes the RULE (">= 2
   independent reports"); this fixes the UNIT that rule was being applied to — the code
   counted LIST ENTRIES and the caller banked the per-episode dead list verbatim, so
   one episode clicking a cell twice satisfied "two independent reports". The threshold
   stays 2; what changed is what counts as ONE. Registering the distinction here because
   an F-row and a G-row over the same sentence is exactly how a frozen rule gets tuned
   by accident.
A12-2 THE MEASURED HARM (audit F-3, PREREG_DEAD_DEDUP.md): live ar25 level 2 —
   dead(as coded)=163 vs dead(as documented)=41. 122 cells (75% of the blacklist) were
   eliminated by WITHIN-EPISODE repeats, and nothing decays it (no recency term, the
   janitor has never run), so the elimination was MONOTONE across every future episode
   and every recycle.
A12-3 BOTH ENDS, BY THE ARCHIVE LAW: the WRITE fix alone would only correct FUTURE
   records, leaving the ~370k already banked inflated forever; a rewrite of those
   records would violate the evidence-only-added law. So the READ side counts distinct
   records — the correction is applied at load time and NOTHING on disk is deleted or
   rewritten. Consequence to state plainly: the two ends must be toggled TOGETHER (one
   flag, both sites), or a mixed arm would measure neither counting rule.
A12-4 THE OFF-ARM IS THE RECEIPT (CLAIM.md's ablation constraint): env DEAD_DEDUP
   outranks the module flag; 0/false/no/off/empty reproduces per-entry counting
   BYTE-IDENTICALLY at BOTH ends — the banked record bytes equal a literal pre-fix
   append, and the returned dead set equals the literal pre-fix computation. Shipped as
   PASSING tests (tests/gate/test_dead_dedup.py::TestTheOffArm), not an intention.
A12-5 REGISTERED VERDICT (PREREG_DEAD_DEDUP.md): ar25 L2 dead falls from 163 toward the
   documented 41 (READ-ONLY RECOMPUTE ON THE LIVE BOOKS AT SHIP: 163 -> 41 exactly, on
   the 32 L2 records in .runs/swarm/ar25/ego_fabric; L1 13 -> 12, L0 40 -> 35). READ
   WITH ITS LIMIT, so the welcome number gets the same check as an unwelcome one: hitting
   41 says the COUNT has no residual, NOT that F-5 level-mixing is absent — a cell
   clicked during the L0 phase of one episode and the L1 phase of another is still banked
   into two distinct L2 records and is still dead under the corrected rule. F-5 is
   untouched and remains the next single. LOSING CONDITION, stated: if the live
   dead count does not move at all, the counting was not the inflation source — REVERT,
   do not re-tune. NOT-MEASURED CONDITION: a beat below rung-0b's MIN_EXPOSURE floor
   reads UNMEASURED, never "no effect".
A12-6 NOT A KNOB, recorded so it is not mistaken for one: DEDUP IS NOT DECAY. A cell
   dead in two genuinely different episodes is still dead FOREVER — F-4 (a cell inert in
   board config A and load-bearing in config B) and F-5 (per-episode lists never reset on
   level change) are untouched by this build and remain open.

### A12-7 (Seat 2, independent verification of G23, 2026-08-17)
The builder reported ar25 only. A Seat-2 census over ALL 27 (box, game, level) harvest
partitions — own reader, frontier.py never imported — REPRODUCES ar25 EXACTLY
(L2 163->41, L1 13->12, L0 40->35) and gives the swarm-wide figure the build did not:
  DEAD CELLS, PER-ENTRY -> PER-RECORD, ALL BOXES: 743 -> 454 (-289, -38.9%)
  worst inflators: ar25 L2 163->41 (4.0x) | lp85 L1 158->92 | sb26 L0 107->48 |
                   sk48 L0 78->62 | ft09 L0 88->76
  ELEVEN partitions are unaffected because they bank ZERO dead cells despite large
  record counts (bp35 460 recs, s5i5 248, vc33 248, sc25 238, lf52 221, tn36 179,
  r11l 161+21, sp80 106+35, dc22 90, ka59 134). r11l L1 alone: 1669 effects, 0 dead.
=> THE INFLATION IS NOT UNIFORM AND NEITHER IS THE REGIME. Half the swarm never
blacklists a cell at all; the fix only bites where clicking is mostly futile. Any claim
that G23 "helps the swarm" must name the partition — 289 cells is a swarm total, not a
per-game effect, and 0 of it lands on the eleven zero-dead partitions.

### A13 — THE BUDGET REGIME IS ASSUMED, NOT MODELLED (2026-08-18, Seat 2 sweep)

VERIFICATION FIRST: `SessionMemory`, `action_limit`, and the "100k floor" DO NOT EXIST in
this repository (grep, whole tree). Fifth cross-thread set. THE DIAGNOSIS IS CORRECT AND
LANDS ON A DIFFERENT CONSTANT.

**G24 MAX_ACTIONS = 500 [GUESSED, UNREGISTERED UNTIL NOW, Register G]**
  Sites: cognitive_loop.py:415 (`self._max_actions: int = 500`), :475 (ctor default),
         :294 (`s.get("max_actions", 500)`).
  CONSUMED AS FEASIBILITY: cognitive_loop.py:1168-1169 and :1250-1251 —
         `budget=float(max(0, self._max_actions - self._actions_taken))`
  IDENTICAL FOR ALL 25 GAMES. Never measured against any game. No per-game value, no
  per-level value, no estimator, no None-branch, no "unknown" state.

**Q1 — DOES ANYTHING MODEL A BUDGET REGIME? NO.** Not a bad estimator: NO ESTIMATOR.
The quantity feasibility divides by is a literal.

**Q2 — IS THE REGIME OBSERVABLE FROM FRAME DATA? YES, AND IT IS MEASURED, AND NOTHING
READS IT.** BOARD_AUDIT.md section 2: ar25 publishes a 64-CELL MONOTONE CLOCK IN COLUMN
63 — refills at level-up, spends on effectful actions, terminal when full. Winning levels
ended with 16 and 18 spare; the fatal prefix spent 64, ran a second 64, and died
completing it, VISIBLE WITH AN EXACT COUNTDOWN FOR 97 STEPS.
  **THE OBSERVABLE REGIME HAS PERIOD 64. THE ASSUMED CONSTANT IS 500. NOT THE SAME ORDER
  OF MAGNITUDE — the loop's model of "how much can I do" is ~8x wrong on the one game
  where we have measured the truth.**
  And goal_abduction.py already defines colour_count_zero(colour) — which can express the
  clock's exhaustion exactly — and never evaluates it.

**Q3 — WHAT DOES THE PLANNER DO WHEN THE REGIME IS UNKNOWN?** NONE OF THE THREE. It never
asks. There is no unknown branch because there is no regime variable. This is a FOURTH
option and it is worse than fail-closed, assume-unbounded, or assume-last-seen:
**ASSUME A NUMBER WITH NO PROVENANCE.** 500 fails silently in both directions — it
over-plans on a 64-tick game and under-plans on an unbounded one, and cannot report
either, because nothing compares it to anything.

## THE REGISTER L SWEEP — WHERE ELSE THE LOOP ASSUMES A CONSTANT THE WORLD VARIES
Bound applied (per the reviewer's scoping clause): ONLY properties A DECISION DEPENDS ON.
Observable-but-unread is a deletion candidate, not an estimator candidate.

  ENVIRONMENT PROPERTIES ASSUMED CONSTANT (candidates for Register L, ranked):
    L-1  max_actions = 500        cognitive_loop.py:415,475,294   FEASIBILITY. Board says 64.
    L-2  max_condition_cells = 4  effects.py:676   CAPS PRECONDITION WIDTH — and the board
                                  audit's finding is that ACTION6 is gated by a
                                  precondition the model has no slot for. A 4-cell cap is
                                  a prior on how complex a gate may be.
    L-3  max_shift = 12           agency.py:39     HOW FAR A MOVE CARRIES. Per-game fact.
    L-4  stall_steps = 50         goal.py:30       WHEN A GOAL IS STALLED = game tempo.
    L-5  max_size = 30            goal.py:131      LARGEST TARGETABLE OBJECT. Per-game fact.
    L-6  birth_min_overlap = 0.30 / death_occupancy = 0.50   perception.py:170
                                  OBJECT IDENTITY ACROSS FRAMES = how fast things move.
    L-7  ttl = 80                 navigation.py:33  PATH LIFETIME.

  NOT Register L (epistemic thresholds, correctly global — the wheel rule):
    min_evidence = 3 (bank.py:50, binder.py:66, spine.py:30), min_obs/purity
    (bank.py:295), eps (router.py:36). These are about HOW MUCH EVIDENCE CONVINCES US,
    not about what the world is. They stay F/G.

## THE ORDERING CONSTRAINT (adopted from the reviewer, and it is binding)
An estimator whose output nothing consumes IS the produced-recorded-and-unread genus.
Building one for L-1 before the planner reads a regime variable would be committing the
genus KNOWINGLY. Therefore: **CONSUMER FIRST.** The feasibility site
(cognitive_loop.py:1168/1250) must read a regime VALUE from a source that can be wrong
and can be corrected; only then does an estimator fill it. Wire, then measure.

## THE GENERAL LAW (stated once, with the scoping clause that makes it terminate)
ANY ENVIRONMENT PROPERTY THE AGENT CANNOT SEE MUST BE DERIVED, AND ANY PROPERTY IT
DERIVES MUST BE RE-DERIVED PER REGIME — BOUNDED TO PROPERTIES SOME DECISION DEPENDS ON.
Register L discipline: THE ESTIMATOR IS A SOCKET (global, F/G, one for all games); THE
ESTIMATE IS PER-GAME PER-LEVEL LEARNED STATE (data, not a knob). This does not violate
the anti-overfit law because no game-specific VALUE is ever shipped — only the capacity
to measure one.

### A14 — G23 PARTIALLY WRONG: THE REPEATS WERE DATA, AND THE SHIPPED FIX DELETES THEM
(2026-08-18, Seat 2, on Seat 4's challenge. This corrects shipped work.)

**THE CHECK SEAT 4 DEMANDED, RUN.** Do repeated dead-cell entries carry distinct stamps?
STRUCTURALLY THEY CANNOT. A dead entry is a BARE [x,y]. The whole record is
{dead, deltas, effects, fatal, game, level, seq} — THE ONLY STAMP IS THE RECORD'S OWN seq.
So "distinct seq per probe" was never available to check.

**BUT THE COUNTS ANSWER IT ANYWAY, AND THEY ANSWER SEAT 4'S WAY:**
  ar25 L2, 32 records:
    WITHIN-RECORD duplicate entries:                    2,061
    MAX REPEATS OF ONE CELL INSIDE ONE RECORD:            290
    max DISTINCT RECORDS naming one cell:                   8
    max TOTAL entries for one cell — (36,36):             299
**290 REPEATS INSIDE A SINGLE EPISODE IS NOT ONE PROBE RE-APPENDED.** Against
G24 MAX_ACTIONS=500, that is ~58% OF AN ENTIRE EPISODE'S ACTION BUDGET SPENT RE-PROBING
ONE CELL THAT RETURNED NOTHING EVERY TIME. Seat 4's alternative reading is the correct
one, and it is the more serious one: **A BEHAVIOUR DEFECT, NOT A CENSUS ARTIFACT.**

**WHAT THIS COSTS THE FIX I SHIPPED.** G23 dedups at BOTH ends; at WRITE it keeps the
first occurrence and DISCARDS THE REST. **SO THE SHIPPED FIX DESTROYS THE RE-PROBE COUNT
AT THE SOURCE — the single most damning behavioural signal in these books. I FIXED THE
CENSUS AND DELETED THE EVIDENCE.** The census numbers still stand AS CENSUS NUMBERS
(553 distinct cells, 41 dead per-record at ar25 L2, 743->454 swarm-wide). What was wrong
was the FRAMING: I called the repeats "pure inflation". They are inflation OF THE CENSUS
and SIGNAL ABOUT BEHAVIOUR at the same time — two questions sharing one ledger.

**REQUIRED REVISION (queued, not built): BANK THE COUNT, DO NOT DISCARD IT.**
  {"cell": [x,y], "probes": n}  — preserves BOTH readings from one record.
  Until then G23 is CORRECT-BUT-LOSSY and must be cited that way.

### A14b — THE AS-OF IS UNANSWERABLE, AND THAT IS THE FINDING
Seat 4: "no as-of on the 45%". Correct, and it cannot be supplied.
**THE HARVEST RECORD CARRIES NO TIME FIELD AT ALL** — verified: keys are exactly
{dead, deltas, effects, fatal, game, level, seq}. NO READING EVER TAKEN OFF THIS STREAM
CAN CARRY AN AS-OF. The only bounds are the file mtime (2026-08-17 17:06) and the
level-convention pinning (9e05be3 / e6a533a, 2026-08-14). Records span seq 1..81 with no
way to date any of them, so **THE POPULATION MAY STRADDLE THE 08-14 SEMANTICS CHANGE AND
I CANNOT RULE IT OUT.** This is a DEFECT IN THE RECORD, not an oversight in the report —
and it is the third number to arrive without an as-of, which is the pattern rather than
the instance. FIX (queued): a timestamp on the harvest record. One field.

### A14c — A NUMBER IN THE RELAY THAT IS NOT MINE
"87 dead cells in a 32-cell L2 grid is arithmetically impossible." THE 32 IS THE RECORD
COUNT, NOT A GRID SIZE. The grid is 64x64 and ar25 L2 holds 553 DISTINCT tried cells. No
"87" appears in any figure I reported (mine were 163 -> 41). The arithmetic-impossibility
argument does not apply to these numbers. **F-5 LEVEL-MIXING REMAINS SEPARATELY OPEN AND
UNADDRESSED** — the prereg named it as the fallback explanation and the count did not
show it, which is not the same as its absence.

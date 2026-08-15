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

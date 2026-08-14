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

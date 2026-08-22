# PLAN — RETIRE THE SUPERVISED FLEET, ADOPT THE ARC SWARM SHAPE (2026-08-22)

Status: PLAN ONLY, as ruled. No build. Fleet stopped, HOLD up.

## 1 · WHAT THE ARC SWARM ACTUALLY IS (read from the docs, not inferred)
From `docs.arcprize.org/swarms.md`, verbatim: *"Swarms are used to orchestrate your agent
across multiple games simultaneously."* It **"creates one agent instance per game"**, **"runs
all agents concurrently using threads"**, manages scorecard open/close, and cleans up when
all agents complete. Invoked as `uv run main.py --agent <name> [--game <filter>]`.

THE AGENT CONTRACT IS TWO METHODS (`docs.arcprize.org/create-agent.md`):
```python
class MyAgent(Agent):
    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool: ...
    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction: ...
```
Registered by adding it to `agents/__init__.py`.

TWO FACTS THAT MATTER MORE THAN THE INTERFACE:
- **The swarm lives in the ARC-AGI-3-Agents repo, not in the `arc_agi` toolkit we have
  installed.** Our `arc_agi` package ships `Arcade.make()` (one environment), the wrappers,
  scorecards, and `listen_and_serve` — and NO swarm runner. Adopting the swarm means
  adopting that harness, not calling a function we already have.
- **Local play is ~2,000 FPS, no API key, "run as many instances as you want"**
  (`local-vs-online.md`). No rate limit offline; the 600 req/min cap is the hosted API only.

## 2 · THE FINDING THAT DECIDES THE DESIGN — THREADS vs THE GIL
The swarm runs its agents **as threads in one process**. That model assumes the agent is
**I/O-bound**: it blocks on an HTTP call to the hosted API, releases the GIL, and another
agent's thread runs. For the reference agents that is exactly right.

**OUR AGENT IS CPU-BOUND AND OFFLINE.** Measured tonight: 3.7–46 seconds *per action*, spent
inside our own numpy/Python cognition — the planner, the composer, `apply_effect`, the mint.
The environment itself is 0.15s for a whole episode and does 2,000 FPS.

So 25 of our agents as 25 threads would **serialise on one GIL** — one core's worth of
cognition for the whole fleet, against the ~3.4 of 4 cores that 25 processes currently use.
That is not a speed-up; on this box it is roughly a **3–4× slow-down** of aggregate
throughput.

**THIS IS THE THING TO DECIDE BEFORE ANYTHING IS BUILT.** The swarm's concurrency is the
right shape for a thin agent and the wrong shape for a heavy one, and ours is heavy for
reasons that are the project's actual subject.

Three honest options:
- **(a) Swarm shape, threads, accept the GIL.** Simplest, matches the docs, and caps the
  fleet at one core of cognition. Rational IF the intent is to make the agent much cheaper
  per action (which the 0.15s-vs-389s gap says is where the real problem is anyway).
- **(b) Swarm interface, process-per-game underneath.** Write the `Agent` subclass so the
  cognition is harness-shaped, but run N of them as processes (multiprocessing, or the
  harness once per game). Keeps 4 cores, drops the supervisor, drops the population, keeps
  one clean entry point. **This is what I would recommend**, and it is a smaller change than
  it sounds because the supervisor's only irreplaceable job is restarting a dead process.
- **(c) Hybrid: threads for the environment, a process pool for cognition.** Most work,
  least certain payoff. Not recommended without a profile that says cognition parallelises.

## 3 · WHAT ACTUALLY BREAKS (investigated, with sites)

### LOAD-BEARING — these fail immediately in a one-process, many-game shape
1. **The fabric root is CWD-RELATIVE.** `cognitive_loop.py:133`, `:262`, `:1940`, `:2064`
   construct `KnowledgeFabric("ego_fabric", ...)` — a *relative* path. Today each worker's
   cwd IS its box, so this resolves per game by accident. **25 games in one process share
   one cwd, so all 25 would read and write ONE fabric.** Every atom, every narration record,
   every settlement would merge across games. This is the single largest breakage and it is
   silent — nothing errors, the data just fuses.
2. **The database anchor is cwd-derived.** `resolve_db_path()` (`database_interface.py:1991`)
   resolves an unspecified default against `Path.cwd()`. Same failure, same silence: one
   database for 25 games. (I built this anchor tonight; it is correct for the current shape
   and wrong for the proposed one.)
3. **Process-level caches are keyed by path but sized for one game**: `fabric._SEQ_TAIL`,
   `_READ_CACHE` (32 MiB cap, ~132 MB of parsed dicts). Shared across 25 games in one
   process, the cache thrashes or must be resized — a knob, not a redesign, but it must be
   re-derived rather than inherited.
4. **Scorecards.** The swarm "automatically manages scorecard opening and closing". Our
   `cognitive_game_player` opens its own (`Created new scorecard` per session). Two owners
   of one lifecycle; ours must yield.

### GOES, AND SHOULD — no loss
5. **The supervisor.** Its only irreplaceable job is restarting a dead process; everything
   else it does (mem-kill, 120-min recycle, deploy-on-change) is judgement it should never
   have had, per the GM's own rule. Under (b) a process pool restarts a dead worker; under
   (a) nothing needs restarting.
6. **The population, the lottery, prestige, operating modes.** Measured: 28,886 agents with
   ONE genome, `discovery_prestige` 0 for every one of them and written by nothing in
   production, 2 of 4 modes ever used, `best_single_game_score` 0 fleet-wide. The selection
   machinery selects uniformly at random from identical agents. **Nothing measurable is lost
   by deleting it**, and the swarm's "one agent instance per game" replaces it exactly.
7. **`evolution_runner`'s generation loop.** Its 50-generation cap, its every-50 lifecycle
   cleanup, its `--population/--agents-per-gen` arguments — all population machinery.

### KEPT, AND UNAFFECTED BY THE SHAPE
8. The whole cognitive stack: `cognitive_loop`, the library/Γ, the mint, the composer, the
   narration spine, the reasoning gate, the frontier book, standing, retention, persistence.
   None of it knows what launched it. It becomes the body of `choose_action`.
9. The fabric streams and the DB — **but see (1) and (2): they must be given explicit
   per-game roots rather than inheriting a cwd.**

## 4 · WHAT WE GENUINELY LOSE, NAMED
- **Replay and mastery-lite as currently wired.** `cognitive_game_player` owns the banked-
  prefix replay, the salient path, the corpse guard and the mastery gate. The swarm's agent
  contract has no session-start hook — `choose_action` is called per frame. Replay must be
  re-expressed as "the first N calls to `choose_action` return banked actions", which is a
  real port, not a move. **This is the one place I would expect the work to exceed the
  estimate.**
- **Cross-game seeding.** `OURO_FABRIC_SEEDS` mounts every other box's fabric read-only, so
  a game can import atoms discovered elsewhere. In one process with one cwd this either
  becomes trivial (all games already share) or must be rebuilt deliberately — and "trivial
  because everything fused" is the failure mode in (1), not a feature.
- **The per-box 284-table database.** Under a shared-process shape this becomes one database
  with a game column, or 25 explicit paths. Either is fine; neither is free.
- **Nothing else.** No capability the agent has depends on being supervised.

## 5 · THE SEQUENCE I PROPOSE (no step starts before the prior one reads green)
1. **Decide (a)/(b)/(c) above.** Everything downstream depends on it. My recommendation: (b).
2. **De-cwd the agent.** Give `KnowledgeFabric` and `resolve_db_path` an explicit per-game
   root threaded from the entry point. Falsifier: two games in ONE process write two
   disjoint fabrics and two disjoint databases, asserted by reading both back. This step is
   worth doing **regardless of the shape decision** — the current code is correct only by
   the accident of one process per box.
3. **Write the `Agent` subclass.** `is_done`/`choose_action` over the existing loop, with the
   replay port stated as its own falsifier (a banked prefix still replays; the corpse guard
   still refuses a dead one).
4. **Verify the plumbing, as a check and not a controller** (the GM's words): reasoning logs
   written, action traces landing, fabric streams appended, per game, under the new shape.
5. **Delete the population machinery and the supervisor** — last, once nothing calls them.

## 6 · WHAT I AM NOT CLAIMING
That this makes the agent fast. The 0.15s-episode against 389s-to-first-cycle gap is
**inside our cognition**, and 375 of those 389 seconds are still unattributed — the stack
sampler filtered out its own answer and the corrected run has not been made. Changing the
harness removes process overhead and the supervisor; it does not touch the per-action cost,
and under (a) it would make aggregate throughput worse. The speed problem and the shape
problem are separate, and only the shape problem is what this plan solves.

---

# ADDENDUM — THE KAGGLE CONSTRAINT (2026-08-22), AND WHAT IT REVEALS

## 7 · WHAT THE COMPETITION ACTUALLY IS (docs.arcprize.org/arc-prize-2026.md, fetched today)
- **"You submit a notebook, Kaggle runs it twice."** Phase A validation, then **Phase B
  HIDDEN GAME EVALUATION**.
- **"All accelerated Kaggle sessions have internet disabled."** Fully offline, self-contained.
- The starter kit's ONLY editable file is `agent/my_agent.py`, implementing exactly the two
  methods the swarm calls: `is_done(frames, latest_frame)` and
  `choose_action(frames, latest_frame)`. `make play-local` runs every game locally;
  `make submit` builds the notebook and pushes it. Output is `submission.parquet`.
- Accelerators offered: CPU-only, T4 x2 (default), P100, RTX 6000.

## 8 · THE FINDING THIS FORCES, AND IT IS NOT ABOUT STORAGE
**PHASE B IS HIDDEN GAMES. A HIDDEN GAME HAS NO BANKED PREFIX. SO REPLAY CONTRIBUTES
EXACTLY NOTHING AT SUBMISSION.**
Tonight's measurement, restated against that fact: 1,496 level completions across 3,474
sessions, and **not one session in 1,542 ever exceeded its box's ceiling**; the two boxes
with the MOST completions (g50t 298, sk48 273) **have never minted a single atom**. The
fleet's entire demonstrated capability is playback of prefixes banked on games it has
already seen.
On a hidden game the agent arrives with an empty bank, and the only thing left is the
cognition that has never, in 3,474 sessions, produced a crossing beyond playback.
**THE SUBMISSION SCORE IS THEREFORE PREDICTED BY THE ONE NUMBER WE HAVE NEVER MOVED, NOT BY
THE ONE THAT LOOKS HEALTHY.** That reorders everything: the replay port (section 4) is work
for local iteration only, and the salient path — a coin flip with 13/13 measured deaths —
should be questioned rather than ported, exactly as Seat 4 said.

## 9 · STORAGE, MEASURED — AND THE REAL CONSTRAINT IS THE OPPOSITE OF THE ONE ASKED ABOUT
Our footprint today, measured: **`.runs/swarm` is 12 GB for 25 boxes** — median box 493 MB,
largest 1,209 MB (g50t: a 976 MB database and a 205 MB fabric). That is MONTHS OF
ACCUMULATION on games we have played repeatedly.
KAGGLE'S `/kaggle/working` QUOTA: **I could not obtain a current figure.** kaggle.com/docs
and the competition page are JavaScript-rendered and returned only titles to a fetch; the
ARC starter-kit page does not state disk, RAM or runtime limits and says so. **I am not
quoting a number I could not verify** — the last figure I hold is ~20 GB, undated and
unconfirmed, and this is precisely the "bound derived against a machine that is not the
target" defect, so I will not repeat it as fact. **It needs one look at the competition's
own Rules/Environment tab by a human session, and the date recorded.**
BUT THE BINDING CONSTRAINT IS NOT THE CEILING, IT IS THE FLOOR: **the notebook starts with
NOTHING.** No `.runs`, no databases, no fabric, no banked prefixes — unless we ship them as
a Kaggle Dataset input. And atoms are keyed by game, so shipping our 12 GB would contribute
nothing to a HIDDEN game anyway. The submission writes only what it produces during one run:
25 games × one session ≈ tens of MB, not gigabytes. **We are nowhere near any plausible
quota, and that is not good news — it is the same finding as section 8 from the storage
side. Nothing we have accumulated transfers.**

## 10 · HOW THE ROOT IS DETERMINED (the GM's constraint, answered)
One resolver, one rule, no cwd anywhere:
```
OURO_DATA_ROOT   env var, explicit               -- wins if set
else /kaggle/working/ouro   if os.path.isdir("/kaggle/working")   -- the Kaggle branch
else <repo>/.runs           if the repo marker is present         -- the local branch
else RAISE
```
- The per-game root is then `root / "games" / game_id`, **passed explicitly** into
  `KnowledgeFabric` and `resolve_db_path`. No component reads `os.getcwd()` or `Path.cwd()`.
- **NO CWD FALLBACK, EVER.** If none of the three branches resolves, it raises naming all
  three and what it looked for. Falling back to cwd is the defect being removed; a fallback
  would reintroduce it wearing a nicer name (Figure 10 — install what can be violated).
- Kaggle detection is by DIRECTORY EXISTENCE, not by an env var Kaggle might rename.
- FALSIFIERS: two games in one process write two disjoint fabrics and two disjoint databases,
  read back and compared; an unset/unresolvable root RAISES rather than defaulting; the
  Kaggle branch is selected on a constructed `/kaggle/working` and the local branch on a
  constructed repo, with the same code and no cwd change between them; and an AST test that
  no module under the production globs calls `getcwd`/`Path.cwd()` for a data path.

## 11 · WHAT CHANGES IN THE PLAN
- Section 2's option (b) still stands for LOCAL iteration (four cores, process-per-game).
- **But the submission shape is fixed by the competition: ONE notebook, the framework's own
  swarm, `my_agent.py`.** There is no supervisor and no population to argue about — the
  competition already deleted them. Our local shape should match the submission shape as
  closely as possible, which is a second, independent argument for retiring the fleet.
- The de-cwd work (section 5, step 2) becomes the FIRST and most urgent item: it is
  required by Kaggle, required by any one-process shape, and correct on its own merits.

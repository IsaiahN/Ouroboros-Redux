# OFFLINE MODE — measured. One environment variable, never set.
2026-08-18. MODE: **GROUNDED**. TAG: **APPARATUS** (it changes what readings are possible —
offline has no scorecards). Seat 3 has already ruled the policy; this is the measurement.

## THE NUMBER
```
    200 OFFLINE steps in 0.16s =  1,243 steps/sec  (0.805 ms/step)
  2,000 OFFLINE steps in 0.17s = 11,782 steps/sec  (0.085 ms/step)

  ONLINE cap, per ARC's own docs: 600 requests/minute = 10 actions/sec
```
**124x to 1,178x.** ARC's docs claim ~2,000 FPS offline; we measure 1,243 cold and 11,782
warm on this box. *Could it have been otherwise:* yes — offline could have been unavailable,
unsupported by our stack, or slower in practice than advertised. It is none of those.

**AND OFFLINE NEEDS NO API KEY.** Probe ran with `ARC_API_KEY` deleted from the environment.
`Arcade(OFFLINE)` constructed in **0.01 s**; it located and loaded the game **from local
disk** — `environment_files\ls20\9607627b\ls20.py` — and `reset()` returned in **9 ms**.

## THE CAUSE — ONE LINE, AND IT IS A DEFAULT NOBODY SET
`arc_api_adapter.py:68`
```python
    return os.getenv('OPERATION_MODE', 'NORMAL').upper()
```
**`OPERATION_MODE` IS NOT SET ANYWHERE.** `.env` carries exactly one key, `ARC_KEY`. So
every run this project has ever made defaulted to **NORMAL** ("local + API"), and the logs
show it reaching the API: scorecards created, metadata fetched, `/cmd/ACTION1` endpoints.

**THE MACHINERY WAS ALREADY BUILT AND FULLY PARAMETERISED.** `arc_api_adapter.py:409`
accepts `operation_mode`, `:434-441` resolves it, `:444` constructs `Arcade` with it, `:464`
exposes an `is_offline` property, and `game_player.py:144-152` already tags scorecards by
mode. **NOTHING NEEDED BUILDING. THE SWITCH EXISTED AND WAS NEVER THROWN.**

## WHAT IT COSTS IN THE UNITS THAT MATTER
An ar25 episode is up to ~1,788 actions.
```
  OFFLINE:                       1788 / 11782      =  0.15 SECONDS
  ONLINE, 25 workers sharing
  600 req/min (24/worker/min):   1788 / 24         =  74.5 MINUTES
```
**~30,000x on a single episode.** And Isaiah's original premise was not optimistic, it was
conservative: **25 games x 1788 actions = 44,700 actions = 3.8 SECONDS offline**, against
"less than 3 minutes".

**THIS RE-EXPLAINS EVERY TIMING NUMBER IN THE RECORD.** The 15h22m r11l arm, the workers
emitting once per 10-15 minutes, the 16-hour arm blocking the whole board — I attributed
those to CPU contention and to the egocentric stack. **Both attributions were wrong in the
same direction.** The dominant term was a 600 req/min API cap divided 25 ways. Seat 4's
rule applies exactly: *a measurement taken under uncontrolled conditions is a measurement
of the conditions* — and I had never applied the population/as-of discipline to timing.

## WHAT I GOT WRONG ON THE WAY HERE, RECORDED
I was one command from publishing **"our code never imports the SDK"** — it does, at
`arc_api_adapter.py:41`, `evolution_runner.py:43`, `game_player.py:144`. Caught by checking
before asserting. The true finding is narrower and worse: the SDK is imported, the mode is
plumbed end to end, and **the default was never changed.**

## AND A NAMING CORRECTION OWED TO A PUBLIC DOCUMENT
**ARC defines a swarm as: one agent instance per game, run concurrently, ONCE**, with
scorecards opened and closed automatically. **WHAT THIS PROJECT CALLS "SWARM MODE" — 25
pinned workers replaying one game each for hundreds of episodes — IS A DIFFERENT THING
WEARING THE SAME NAME.** ar25's worker log alone carries 256 episode boundaries. The docs
are public; ours must either be renamed or explicitly described as an extension.

## STATUS
Online swarm **STOPPED** (0 processes) pending the switch. Every wall-clock and throughput
figure taken to date is **a measurement of the online path under contention** and is
labelled as such rather than deleted — including the arm's, whose CAPABILITY result is
unaffected because contention changes wall-clock and not what an agent achieves per episode.

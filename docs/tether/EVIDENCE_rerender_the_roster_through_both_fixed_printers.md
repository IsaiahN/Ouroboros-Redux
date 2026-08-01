# EVIDENCE — arm T: the roster re-rendered through both fixed printers

Prereg: `PREREG_rerender_the_roster_through_both_fixed_printers.md`, written before launch.
Run: 2026-08-01 10:36–10:45 UTC · 25 games · `max_actions=120 wall_cap_s=200` · no `only` filter.
Scorecard: **https://arcprize.org/scorecards/6b4470b1-5349-4fa1-8251-4c6db9a1ccd0**
Capture: `/tmp/armT.txt` · **result sidecar `/tmp/armT_res.json` (264,933 bytes)**
Bank at launch: **WARM** — 15 files, 744K, fingerprint `bd0744f64dbceae55996ed297d88b371`, not byte-identical
to `/tmp/bank_snapshot`. Every firing count below is a warm-bank count.

## The prediction ledger

| # | prediction | result |
|---|---|---|
| T-1 | `>=75%` zero on every game | **CONFIRMED** — 0/25 |
| T-2 | `>=50%` nonzero on EXACTLY `m0r0` and `tn36` | **CONFIRMED** — exactly those two, 1 step each |
| T-3 | `>=25%` nonzero on EXACTLY those two plus `lp85` | **CONFIRMED** — exactly three |
| T-4 | `live_max_frac` within ±2 pp of the forced column | **CONFIRMED, AND STRONGER** — see below |
| T-5 | roster `redraw` under 2% of `live` | **CONFIRMED** — 2 of 1265 = 0.16% |
| T-6 | `local + redraw + unsized == live`, `unsized == 0` | **CONFIRMED** — residue 0 on all 25 |
| T-7 | 6–10 games WIDENED, 14–19 crossing >1 exit | **CONFIRMED** — 9 widened, 19 crossing |
| T-8 | regrouping residue 0 | **CONFIRMED** — 2822 = 2822, residue 0 |
| T-9 | sidecar reloads byte-identical | **CONFIRMED** |

Nine of nine. No prediction was adjusted after launch and none is being reinterpreted here.

## CLASSIFIER 20 — the largest change a board makes is a property of the BOARD, not of the run

T-4 was written as a tolerance and came back as an identity. The forced column was computed from
`armO_floor.txt`'s `live(mean/max)` statistic — a DIFFERENT run, eight hours and a different trajectory earlier —
as `max / 4096`. On **all 24 games that had a prior maximum, arm T's `maxfrac` matched to the printed decimal.**
Not one game moved by so much as 0.1 pp. (`sc25` had no row in that capture and so had no prediction; it
rendered 1.3%.)

That is not what a trajectory-dependent statistic does. The *counts* moved everywhere — `cd82`'s live went 12→14,
`lf52`'s band 57→87, `s5i5`'s sub_floor 54→20 — while every *maximum* held exactly. So `live_max_frac` is
measuring the board's largest available response, and the agent reaches it on essentially every run without
trying to. **A derived point prediction from a published instrument is therefore cheap and sound for this
statistic specifically**, which is what made this whole arm predictable in advance at zero API cost.

*How to overturn it:* run the roster again at a much lower `max_actions` (say 30). If the maxima still hold, the
board's biggest response is reachable in the first thirty steps and the claim strengthens; if they collapse, the
statistic is trajectory-length-dependent after all and every derived prediction above needs re-pricing.

## CLASSIFIER 19 on the full roster — `live` is a floor-edge population and almost nothing else

    TOTAL   live 1265   local 1263   redraw 2   unsized 0   resid 0   |   >=25%: 3   >=50%: 2   >=75%: 0

Two steps in the entire roster replaced half the screen: one on `m0r0-492f87ba` (66.1%) and one on
`tn36-ef4dde99` (61.5%). The arm-S reading on the cheap pair — one redraw in thirty-six — was not a small-sample
artefact; it was the roster's shape. Twenty of twenty-five games never exceed 6.8% of the board, and eleven never
exceed 2%.

`lp85-305b61c3` behaves exactly as the head item said it would: 34.4%, `local` at the shipped 50% edge, `redraw`
at a 30% one, and the only game in the roster whose verdict the edge choice actually decides. It is the single
row that makes the `@25/@50/@75` columns worth printing.

## CLASSIFIER 18 on the full roster — and CLASSIFIER 21, what is left when the printer is fixed

Giving arm O's broken per-exit rendering its best row per game, 24 games resolved to:
**13 MUTE, 5 ACTION-CONDITIONAL, 5 UNIFORM-and-HIGH, 1 UNIFORM-not-high.** Fifty-seven of its seventy rows
refused to answer.

Arm T's by-game block, same control, question's own denominator, 25 games:
**7 MUTE, 11 ACTION-CONDITIONAL, 4 UNIFORM-and-HIGH, 3 UNIFORM-not-high.**

Nine games were WIDENED — their actions never met inside a single exit, so every per-exit verdict on them was a
subset — and **seven of those nine now read ACTION-CONDITIONAL**: `bp35` (92.0 pts), `cd82` (29.4), `cn04` (44.9),
`ka59` (100.0), `sb26` (83.3), `sc25` (19.4), `sp80` (100.0). Those are seven verdicts the old printer could not
structurally produce. Six games that were MUTE-in-every-row under arm O now carry a verdict.

**CLASSIFIER 21: the control's remaining blindness is the AGENT'S ACTION MONOTONY, not the printer.** The seven
games still MUTE are `ft09`, `lp85`, `r11l`, `s5i5`, `tn36`, `vc33` — one action label each, all A6 — plus
`tr87`, which spent 115 of 119 priced steps on A3. No regrouping can rescue these: a split cannot vary when
there is nothing to split. To get a verdict on them the agent must emit a second action label on them, which is
a statement about the drive layer and not about any instrument.

*How to overturn it:* if a future sweep resolves one of those seven WITHOUT the agent's action distribution
changing on that game, the attribution to monotony is wrong.

## What did not move, and is not claimed

- `cleared = 0`. Break events 48, residual computed 43, non-empty 24, minted 21, promoted into Γ 5, offered 22,
  **FIRED 9, CLEARED 0** — on a WARM bank. The chain still does not complete, the detector taxonomy stays frozen,
  and nothing in this arm was an agent change.
- `indicts=mixed (source=reuse_funnel, scope=MINTED_UNUSED, attempts=9)` against
  `indicts_worst_stage=drive (USED_NOCLEAR)`. The two readings still disagree; the branch reading is the
  attribution.
- Budget identity closes: steps 2962 = decide 2942 + retries 20, residue 0.
- Γ→action pre-registered prediction of 0 directed steps: PASS.

## The sidecar — the debt class is retired

`tools/sweep_chain.py` now writes its result dict beside the capture and can re-render a banked sweep with
`--render <file>`, needing no API key. The write is not trusted: the capture is rendered twice, once from the
measured dict and once from the reloaded file, and compared. Arm T's verdict line reads **byte-identical**.

From here a printer fix costs a re-render, not a sweep. Arm T is the last sweep that will ever have to be spent
on one. `tests/test_sweep_dump.py` pins the round trip, pins the reloaded numbers by name, pins that the
re-render path opens no session — and, in its third test, pins that the comparison CAN fail, because an equality
assertion between two renders is worth nothing if the renders could not differ.

## One instrument defect found on the way, banked and NOT fixed this beat

Running `pytest` while a live sweep is writing `recordings/` turns ten normally-skipped replay tests into three
failures, including `test_ls20_only_ever_mints_colour_agnostic_intended_free` asserting *"no ls20 recording
produced an affordance mint"* when the real situation is that no ls20 recording was present at all. These tests
read whatever recordings happen to be lying in the working directory and assert on their contents, so a PARTIAL
recording set makes them fail with a message that sounds like a finding about the agent. After
`rm -rf recordings environment_files` the suite is clean. Recorded here so the next beat that sees those three
failures does not spend itself diagnosing the agent.

## Gates at the commit

`pytest tests -q` **777 passed, 12 skipped** · `-m newhorse.audit` **VERDICT: clean (1 warn)**
(`novelty_claims: ['ft09_win=match_active_panel_to_reference']`) · `-m newhorse.redux_arch.answer_lint`
**clean**. `docs/AUDIT_BASELINE.json` ratcheted 784 → 789 (the five new sidecar tests).

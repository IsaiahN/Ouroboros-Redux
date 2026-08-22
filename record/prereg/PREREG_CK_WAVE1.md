# PREREG: CORE-KNOWLEDGE WAVE 1 — typed transforms + affordance un-gating

DATE: 2026-08-13. STATUS: registered before build. AUTHORITY: Isaiah's directive ("we need
to wire this into the closure") + CK_LEDGER.md. Measured grounds: [PLAN-GATE] lp85
episode A = g1..g6=194, g7=0 (atoms present + slots bound + EMPTY PLAN every cycle);
harvest=0 across all 18 level-0 games.

## CK-1a: TYPED PARAMETERIZED TRANSFORMS (attacks g7=0; Marcus variable binding + geometry priors)
Build in engines/egocentric/effects.py:
- classify_transform(before, after) -> one of {TRANSLATE(dx,dy), ROTATE(k), REFLECT(axis),
  SCALE(fx,fy), COLOUR_PERM(mapping), NONE} computed on the changed bbox. Pure function.
- learn_effect stores, when classification succeeds, atom.ttype + atom.params alongside the
  existing raw before/after (raw stays as fallback — nothing removed).
- apply_effect: for typed atoms, apply the PARAMETERIZED op to the matched region — the atom
  now fires in contexts it has never literally seen (the open variable bound to a role).
- The planner and bank consume typed atoms through the existing interfaces (no signature
  change); composability comes from apply_effect generalizing.
Legitimacy: rotation/translation/reflection/scaling/colour-mapping are Part-A2(d)/Part-F
core geometry — four-year-old test passes.
FALSIFIER (shown failing first): tests/gate/test_typed_transforms.py — (1) classify a pure
translation/rotation/reflection/scale/colour-perm patch correctly; (2) a typed atom applies
to a NOVEL context (different absolute position) where the raw-patch fallback cannot;
(3) NONE for an unstructured diff; (4) existing effects tests stay green (raw path intact).
VERDICT RULE: next beats, [PLAN-GATE] g7 must move off zero in games where g6>0; a nonzero
shadow count is the success signal (DRIVE stays gated on 2x TRANSFERRED — the wheel rule
unchanged).
UNDO: git revert of the commit; raw path is unchanged so revert is clean.

## CK-1b: AFFORDANCE HARVEST UN-GATING (Gibson; fixes level-0 blind re-exploration)
Current: frontier harvest banks only on level/death events -> the 18 level-0 games have
banked NOTHING across 48-112 episodes each.
Build: bank the episode's experience (effect cells: cell -> action -> changed?, dead cells)
at EPISODE END regardless of level/death, same record shape, same conservative >=2-report
dead rule, same veto/remap consumers. No new consumer behaviour — only the accrual gate.
Legitimacy: "this object permits this action, which changes that state" is affordance
perception — core (Gibson; Adolph). Mechanics only; no answer content.
FALSIFIER (shown failing first): tests/gate/test_affordance_harvest.py — an episode with
zero level-ups and zero deaths still writes harvest records; the >=2-report dead rule and
remap behaviour unchanged (existing frontier tests green).
VERDICT RULE: harvest counts move off zero for level-0 games within one beat; untried-cell
remap starts consuming them (log lines exist already).
UNDO: git revert; the gate is one condition.

## CONTAINMENT (both)
Gate suite 167+ green. CK-1a changes what atoms EXPRESS (knowledge), not what actions are
chosen absent a plan; CK-1b changes what is BANKED. Both alter long-run behaviour BY DESIGN
(that is their point) — the wheel rule stays: blind explore incumbent, DRIVE still requires
2x TRANSFERRED verification. The letters-wall watchdog and the four-year-old test bound the
vocabulary. One wave, two builds, separately revertible.

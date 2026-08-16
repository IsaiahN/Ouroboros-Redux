# PIPELINE AUDIT (2026-08-16, read-only trace, receipts in task record)
CAUSAL STORY (found, not assumed): goals are rarely POSED (upstream break) AND the
selector's exploit branches predate the goal object (correct 2026-02-13/14, condition
died 2026-02-15, ran 6 months) — the two compose. Exploit-waste is downstream symptom.
FINDINGS: 1a no goal lifecycle (rebuilt from pixels each frame; no create/retire).
1b has_goal=True on panel detection alone -> goal:0/0 phantom (conflates "display
exists" with "goal known"; perceiver.py:260-262). 1c 0/0 BLOCKS its own recovery
(Gap-1 gated on `not has_goal`, loop:3092) — live in the log, dead in the decision.
1d goal:n/n is EXPLORATION COVERAGE mislabeled as goal (workspace delta written into
goal fields, loop:3099-3107; docstring admits it). 1e completion FORCES exploit
(cells_remaining<=3 includes 0; loop:3270-3276); no retirement anywhere. 1f exploit
branches goal-blind: `_prior_loaded + map>0.1 or cert>0.2 -> exploit` (loop:3292-3297).
1g dated: convention outlived condition 2026-02-15. 1h INSTRUMENT DEFECT: P: summary
frozen pre-enrichment (loop:3078 vs 3092) — no-goal counts inflated. 2a T:exploit vs
experiment downstream-indistinguishable (same decide(), strategy not in context).
2b goal-less exploit rung FABRICATES a majority-colour objective (exploitation.py:
3319-3331) — the literal mechanism of exploiting nothing. 4a budget strategy-blind.
4b THREE dead throttles: exploitation budget modifier (0 call sites), imagination rung
gated on nonexistent method, frustration escape reads never-written table.
ROLE COLLAPSE (separate trace): incidental w_A/w_B writer/reader inversion noted
(agent_factory writes w_B; operating_mode_system reads it as wA).
FIX PROGRAM NAMED (F1-F8): F1 exploit requires live non-vacuous non-completed goal;
F2 split has_goal (panel-detected vs goal-known; 0/0 never live, never blocks Gap-1);
F3 coverage never written into goal fields; F4 n/n retires -> explore; F5 no fabricated
objectives (no goal_state -> no constraint-solve; fall through); F6 fix P: timing;
F7 dead throttles removed or wired (decide per soundness); F8 w_A/w_B (awaits role
trace). Behavior changes -> prereg + falsifiers + control-arm verdicts per framework.

## WAVE GOVERNANCE (reviewer, 2026-08-16 — binding):
(1) VALUE-VS-EFFECT SWEEP runs BEFORE the wave: for every gate test, does it assert a
VALUE or an EFFECT? The role test asserted a table while the organ was orphaned —
same genus as R_T=0.000 (checks the record, passes either way). Sweep dispatched.
(2) CONFOUND AS-OF: every measurement since f673b9a (2026-08-13) was on a swarm with
zero optimizers/exploiters and NO live budget differentiation — LP arms, rho readings,
rung-4 traffic (86->123) all carry this date as a standing caveat.
(3) ORDERING LAW: F6 FIRST (the instrument timing defect — everything is measured
through it); then the pure inconsistency repairs, no arms needed (F7-single-target-
table, F3 wire-or-delete, F5 orphan, RF6 knowledge/telemetry split) — those remove
things that lie; THEN behavioral changes SINGLY, one change then re-run. Fifteen in a
wave is fifteen confounded arms.
(4) THE CAUSAL STORY IS A HYPOTHESIS WITH A FALSIFIER, registered now: fixing the goal
lifecycle predicts budget goes somewhere useful and levels move. If levels do NOT move
after F1-F8, that is INFORMATIVE, not disappointing: the wasted budget was not the
binding constraint and TARGET-SELECTION is. Named before the wave so the outcome is
readable either way.

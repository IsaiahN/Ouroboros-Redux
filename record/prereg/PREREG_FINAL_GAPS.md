# PREREG: THE FINAL GAPS — rho, R_T bracket, goal abduction, LP drive

DATE: 2026-08-14. AUTHORITY: Isaiah ("resolve the gaps first... get the system fully
built"). Order: G-A rho + G-B bracket (parallel, measurement), G-C goal abduction
(mechanism), G-D LP drive (last; must beat random). Hardened process: tests-first,
ruff/OOD/ship-clean gates, disjoint ownership, separate commits.

## G-A: THE RHO ESTIMATOR (closes the anchor figure's metric)
engines/egocentric/rho.py: rho(fabric_a_atoms, fabric_b_atoms) -> [0,1] = weighted
Jaccard over atom signatures (sigma + ttype/params class), plus n_eff(k, rho_bar) =
k/(1+(k-1)*rho_bar). Consumers (same build, one-currency law): (1) the triangulation
consumer ranks candidate sources by LOW rho (independence is the gate — Fig 8's debit);
(2) a COLLAPSE-4 GUARD: rho ~ 1 between two fabrics -> their agreement counts once
(n_eff), logged [RHO] per consume pass. Pure functions; no behavior change outside
consumer ranking.
FALSIFIER: identical fabrics -> rho ~ 1, n_eff -> 1; disjoint synthetic fabrics ->
rho ~ 0, n_eff ~ k; consumer prefers the low-rho source when two sources match.

## G-B: THE R_T BRACKET RESIDUAL (closes Fig D)
tools/bracket_rt.py: measures |T_A . T_E(x) - x| — the promote->seed->re-derive round
trip: (1) pick a promoted generator (a collective atom with provenance); (2) in a FRESH
box seeded ONLY with priors (never the atom itself — the membrane law), count episodes/
evidence until an equivalent atom (sigma-match) is re-derived; (3) R_T = divergence
(sigma distance + cost delta). Synthetic mode for the gate test (two in-process fabrics);
live mode reads real boxes read-only. Reported per game, [BRACKET] lines.
FALSIFIER: a synthetic generator seeded as a prior is re-derived cheaper than cold
(the prior lowered the kernel — Fig D's caption measured); a playback sequence NEVER
crosses (asserts membrane).

## G-C: GOAL ABDUCTION (the thin link — tier-2 objectives beyond d->0-to-reference)
engines/egocentric/goal_abduction.py + wiring: bank the LEVEL-UP FRAME DELTA (what
changed at the moment of level-up, banked per game+level across episodes — mechanics,
not answers: the PREDICATE shape, e.g. "region X uniform", "count(colour c)==0",
"pattern A matches B") as GOAL HYPOTHESES in the fabric (collective, level-scoped,
credibility-ranked like priors). The planner gains a second target mode: plan toward
the top abduced goal predicate when no reference snapshot exists (the g4=0 episodes!)
— same verification gates, DRIVE still needs 2x TRANSFERRED atoms. abduced=[] dies.
FALSIFIER: synthetic episodes where level-up always co-occurs with a predicate ->
the hypothesis is banked with rising credibility; a fresh episode with no reference
snapshot produces a [PLAN] shadow toward the abduced goal; no level-up evidence ->
no hypotheses (never invented).

## G-D: LP DRIVE (LAST, flagged, three-arm — C33's control finally run)
engines/egocentric/lp_drive.py behind LP_DRIVE_ARM env flag with THREE ARMS: fixed /
random / lp (learning-progress: aim exploration at the NOVEL bin's most compressible
residuals — the mint's own MDL scores as the compressibility signal, its output never
a metric). Arm assignment per worker via env; the control-arm driver compares arms.
ACCEPTANCE: lp must beat random on evidence-per-budget across arms or it does not
merge into default-on. Build the machinery + arms now; the arm experiment runs live.
FALSIFIER: with LP arm on, exploration provably reweights toward high-|R|-compressible
sites in a synthetic drive; fixed/random arms byte-identical to current behavior.

## CONTAINMENT (all): suite 500+ green, failing-first, ruff/OOD/ship-clean, wheel rule
untouched (LP steers exploration ONLY — never prices, never bypasses verification).

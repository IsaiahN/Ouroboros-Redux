# PRE-REGISTRATION — the budget restoration (Isaiah's directive)

**Written 2026-08-12. Two findings drove this: (1) post-handoff episodes stand at level 2 with
only the replay REMAINDER (our 3c conservatism) — measured deaths at 15-60 post-handoff actions;
Isaiah's diagnosis: "no wonder — it runs out of room"; (2) the role-based budget economy
(`adaptive_action_limits.ROLE_BASE_ATP`) exists in full and is wired to NOTHING — every agent
in every run got a flat 400. Another stranded organ, restored by owner directive.**

## THE CHANGE THAT IS AUTHORISED
> (a) **Dynamic level allowance at handoff**: a replayed level is a completed level for funding —
> handoff budget = allowance × (1 + levels_replayed) − replay_cost, mirroring the live level-up
> grant (player line ~555) exactly. (b) **Role-scaled allowance** (v1, static component): the
> episode's actions_per_level = max_actions × ROLE_BASE_ATP[role] using Isaiah's committed
> table (pioneer 1.5 / generalist 1.2 / optimizer 1.0 / exploiter 0.8); unknown role → 1.0.
> The full salary system (network-need adjustment, low-start boost) is a later prereg.

## THE GATE
1. TESTS FIRST: handoff funding arithmetic; role multiplier application incl. unknown-role
   fallback; source scans.
2. ⚠ CONTAINMENT BREAK IS EXPECTED AND DOCUMENTED: budgets change globally by design. New
   control shas stored post-land (the crash-fix precedent). 
3. **SCOREBOARD LINE:** any L2 from here on is reported on the BUDGET-RESTORED line, never
   conflated with the sealed baselines (which were budget-starved at the frontier by (1)).
4. ⭐ FALSIFIER (capability): in the next compounding run, post-handoff episodes show budgets
   > replay remainder in the handoff lines, and pioneer/exploiter episode budgets differ by
   their multipliers (re-derived from logs).

## THE UNDO
`git revert`.

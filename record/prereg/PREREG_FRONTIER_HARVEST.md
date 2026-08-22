# PRE-REGISTRATION — 3d-ii: the frontier exploration harvest (Isaiah's correction)

**Written 2026-08-11, at `a3ddfa0`+log. Isaiah: "where the agent died isn't as important as what
it learned about what it explored." The fatal-opening ban (3d-i) keeps ONE bit per frontier
episode; the other ~150 actions of experience evaporate. This banks the experience.**

## THE CHANGE THAT IS AUTHORISED

> Every frontier episode (reached level >= 1), on ANY end (death or budget), banks a HARVEST
> record to the collective fabric (topic "frontier_harvest", per game+level): the cells clicked
> with NO effect (dead), the cells whose click CHANGED the frame (effects), the fatal cell if
> the episode died (subsumes 3d-i's data), and the established action->delta map. Observations,
> never signal — nothing here opens the wheel.
>
> Consumers, at the frontier (game+level scoped, all exploration ORDERING):
>   * dead cells (CONSERVATIVE: reported dead in >=2 independent records AND never in any
>     effects list — one episode's dead click may be state-dependent) are remapped away from,
>     to the NEAREST UNTRIED cell (untried = not in the union of all tried cells) — coverage
>     becomes cumulative: N episodes stop being N independent blind draws and become one
>     population-wide sweep of the frontier board;
>   * fatal cells keep 3d-i's veto;
>   * harvested deltas pre-establish the spine's move-map (means, not signal — drive still
>     requires a confirmed goal; this only removes the re-learning tax the replay feed pays).

## THE GATE — binding
1. TESTS FIRST, SHOWN TO FAIL: harvest round-trip + merge rules (the >=2-and-never-effect dead
   rule pinned; effects always win over dead reports); `remap_to_untried` (prefer untried over
   merely non-avoided; fallback chain; determinism); delta pre-establishment; wiring scans
   (harvest written on BOTH death and budget ends; consumers in the pre-empt block only).
2. ⭐ FALSIFIER (containment): all six control shas byte-identical (empty fabric = all no-ops).
3. ⭐ FALSIFIER (capability, population run): harvest records with non-empty dead/effects
   appear; later frontier episodes show untried-remaps; and the per-(game,level) TRIED union
   grows monotonically across records (re-derived from the fabric by the proctor). Coverage
   that does not grow means the sweep is not cumulative -> fix or revert.

## THE UNDO
`git revert` of the 3d-ii commit(s).

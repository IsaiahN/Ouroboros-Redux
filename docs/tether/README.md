# The Tether — canonical spec + figures (persisted for the build loop)

The authoritative architecture, committed here so every reclone (and thus every compacted beat) has it.
Read alongside the project docs claude/DESIGN_tether_architecture_groundtruth.md and claude/DESIGN_collaboration_as_tether.md.

- THE_TETHER_spec.pdf — the full 40-page spec (§0 thesis .. §9 caveats + references).
- THE_TETHER_Figure1_the_agent.png — Fig 1: how structure grows (kernel K=(Γ,M), per-step POMDP loop, boundary diff, one mint operator on 3 residual streams: Lane A transition→affordance, B reward→goal, C frame-transform→bracket).
- THE_TETHER_Figure2_ground_and_frames.png — Fig 2: what makes growth CORRECTIVE not merely coherent (ground + liveness, alignment=triangulation, anchor condition, non-identity, ground-maintainer, four ground-failure modes).

Neither figure is self-sufficient. Ground-verified closure vs the LIVE environment is the sole metric.

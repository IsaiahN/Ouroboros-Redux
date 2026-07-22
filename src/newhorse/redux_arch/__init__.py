"""
redux_arch -- the Ouroboros-Redux architecture (branch `redux-arch`), assembled to the chart.

This package expresses the working `new-horse` loop as the chart's NAMED, CITATION-MATCHED blocks, and makes
the one novel block -- residual-driven predicate minting (Region III) -- an explicit seam to be filled. It does
NOT reimplement the proven internals; it COMPOSES them (AgentLoop is held, its parts exposed as named blocks),
so `AgentLoop` and its live wins (tu93) stay untouched while the architecture's structure becomes explicit.

Charter: `claude/DESIGN_redux_arch_charter.md`. Spec: `OUROBOROS_REDUX_architecture_spec.md`.
"""
from .loop import ArchLoop, CHART_BLOCKS

__all__ = ["ArchLoop", "CHART_BLOCKS"]

"""engines.egocentric -- Phase 1 verbatim ports of the new horse's belief-state bricks.

Modules (ported byte-identical from Nexus:src/newhorse/, logic untouched):
  * perception  -- segment / Object / ObjectTracker (object permanence by overlap)
  * self_locus  -- SelfLocus (contingency, not correlation: the Goodhart guard)
  * agency      -- CursorAgency (per-action displacement map, background-separated)
  * observer    -- EgoObserver wrapper (read-only sensing for the cognitive loop)
"""
from engines.egocentric import agency, perception, self_locus  # noqa: F401
from engines.egocentric.observer import EgoObserver  # noqa: F401

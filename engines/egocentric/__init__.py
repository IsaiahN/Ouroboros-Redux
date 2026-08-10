"""engines.egocentric -- Phase 1 verbatim ports of the new horse's belief-state bricks.

Modules (ported byte-identical from Nexus:src/newhorse/, logic untouched):
  * perception  -- segment / Object / ObjectTracker (object permanence by overlap)
  * self_locus  -- SelfLocus (contingency, not correlation: the Goodhart guard)
  * agency      -- CursorAgency (per-action displacement map, background-separated)
  * observer    -- EgoObserver wrapper (read-only sensing for the cognitive loop)
  * goal        -- GoalManager (a market of candidate goals priced by reward)  [Phase 2]
  * relations   -- relation hypotheses over objects                            [Phase 2]
  * navigation  -- GridNav (walls are Phase 2b; present, not yet consumed)     [Phase 2]
  * spine       -- GoalSpine wrapper (confirmed reward earns the wheel)        [Phase 2]
  * fabric      -- KnowledgeFabric (scoped JSONL + the idea economy)           [Phase 3a]
  * falsified_ledger -- FalsifiedLedger (weighted, defeasible reject-memory)   [Phase 3a]
"""
from engines.egocentric import agency, falsified_ledger, goal, navigation, perception, relations, self_locus  # noqa: F401
from engines.egocentric.fabric import KnowledgeFabric  # noqa: F401
from engines.egocentric.observer import EgoObserver  # noqa: F401
from engines.egocentric.spine import GoalSpine  # noqa: F401

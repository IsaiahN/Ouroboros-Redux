"""observer.py -- Phase 1's read-only wrapper around the egocentric substrate.

`EgoObserver` holds the previous frame's objects internally so the cognitive loop can feed it
one (post_frame, action) pair per step and get back a small dict of beliefs:

  * `colour`  -- the controllable colour named by `SelfLocus` (contingency, not correlation:
                 the Goodhart guard), or None while cold;
  * `objects` -- how many objects the tracker currently carries in view;
  * `centroid`-- the picked controllable object's centroid, or None.

Discipline (PREREG_PHASE1.md): deterministic (no RNG, no I/O), and EVERY exception is
swallowed to the `errors` counter -- sensing must never crash the loop it feeds.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from engines.egocentric.perception import Object, ObjectTracker, segment
from engines.egocentric.self_locus import SelfLocus


class EgoObserver:
    """Read-only egocentric sensing: segment -> track -> accrue action-contingency evidence."""

    def __init__(self, background: int = 0):
        self.background = int(background)
        self.tracker = ObjectTracker()
        self.locus = SelfLocus()
        self._prev_objs: Optional[List[Object]] = None
        self.errors: int = 0          # exceptions land here, never in the caller's lap
        self.calls: int = 0           # total observe() calls (the loop logs every 10th)

    def observe(self, frame: Any, action: Any) -> Dict[str, Any]:
        """Digest one post-action frame. First call stores state and names nobody (colour=None)."""
        self.calls += 1
        try:
            g = np.asarray(frame)
            objs = segment(g, background=self.background)
            current = self.tracker.update(objs)
            if self._prev_objs is not None:
                self.locus.observe(str(action), self._prev_objs, current)
            self._prev_objs = current
            picked = self.locus.pick(current)
            return {
                "colour": self.locus.controllable_colour(),
                "objects": len(current),
                "centroid": picked.centroid if picked is not None else None,
            }
        except Exception:
            self.errors += 1
            return {"colour": None, "objects": 0, "error": True}

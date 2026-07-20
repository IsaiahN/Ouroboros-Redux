"""
primitive_ledger.py  --  refactor infrastructure for the composition system: regression suite + interfaces + version
control, at the primitive level. One object, three views. Reuses the existing substrate (prediction_error_bus verdicts,
the registry) rather than duplicating it.

DISCIPLINE (baked in): defaults to OBSERVE-ONLY. It records verified predictions and LOGS what a gated restructure would
do, but changes NO decisions unless OURO_REFACTOR_LEDGER=active. So it cannot break the working agent, and the A/B
(naive demotion vs ledger-gated demotion vs uncontaminated baseline) is a runtime flag, not a code change.

Thread-local: the Kaggle framework runs one agent per game in its own thread, so every game gets an isolated ledger --
no cross-game races.

Modes (env OURO_REFACTOR_LEDGER):
  off      -- inert (no recording, no logging)
  observe  -- record verified predictions + log would-revert decisions; change nothing   [DEFAULT]
  active   -- additionally GATE restructures: revert any that would orphan a verified prediction
"""
from __future__ import annotations
import os, threading, copy, json

MODE = os.environ.get("OURO_REFACTOR_LEDGER", "observe").strip().lower()
VERIFY_EPS = float(os.environ.get("OURO_LEDGER_EPS", "0.05"))   # residual <= EPS on a REAL frame => verified
SNAP_CAP   = int(os.environ.get("OURO_LEDGER_SNAPS", "16"))     # bounded snapshot stack (no unbounded growth)
LOG_CAP    = int(os.environ.get("OURO_LEDGER_LOG", "400"))


def _norm(x):
    """Stable, hashable signature of a predicted/observed value."""
    try:
        return json.dumps(x, sort_keys=True, default=str)[:200]
    except Exception:
        return str(x)[:200]


class PrimitiveLedger:
    def __init__(self):
        self._local = threading.local()

    def _st(self):
        s = getattr(self._local, "st", None)
        if s is None:
            s = {"verified": {}, "contract": {}, "snapshots": [], "log": [], "stats": {"commit": 0, "revert": 0, "would_revert": 0}}
            self._local.st = s
        return s

    # ---------------------------------------------------------------- View 1: REGRESSION SUITE (verified predictions)
    def record(self, prim, frame_sig, predicted, observed=None, residual=None):
        """A prediction checked against a REAL frame. residual<=EPS (or an explicit confirmed verdict) => it becomes a
        behavioral invariant this episode. Called observe-side from the prediction-error path; never changes decisions."""
        if MODE == "off":
            return
        ok = (residual is not None and residual <= VERIFY_EPS)
        if residual is None and observed is not None:   # no residual given: exact-match fallback
            ok = (_norm(predicted) == _norm(observed))
        if ok:
            self._st()["verified"].setdefault(str(prim), set()).add((str(frame_sig), _norm(predicted)))

    def verified_set(self, prim):
        return self._st()["verified"].get(str(prim), set())

    def record_verdict(self, prim, frame_sig, predicted, verdict):
        """Bridge for the existing bus verdict vocabulary ('confirmed'/'provisional'/'falsified')."""
        if MODE == "off":
            return
        if str(verdict).lower() == "confirmed":
            self.record(prim, frame_sig, predicted, residual=0.0)

    # -------------------------------------------------------------------------- View 2: INTERFACES (contracts)
    def declare(self, prim, consumes=(), produces=(), prediction_shape=None):
        if MODE == "off":
            return
        self._st()["contract"][str(prim)] = (tuple(consumes), tuple(produces), prediction_shape)

    def dependents(self, prim):
        """Primitives whose contract CONSUMES something this primitive PRODUCES -- the only ones a restructure of `prim`
        can break. Keeps regression re-check scoped, not global."""
        c = self._st()["contract"].get(str(prim))
        if not c:
            return []
        produced = set(c[1])
        return [p for p, (cons, prod, ps) in self._st()["contract"].items()
                if p != str(prim) and produced & set(cons)]

    # ------------------------------------------------------------------- View 3: VERSION CONTROL (checkpoint/revert)
    def checkpoint(self, registry):
        snaps = self._st()["snapshots"]
        snaps.append(copy.deepcopy(registry))
        if len(snaps) > SNAP_CAP:
            del snaps[:-SNAP_CAP]

    def commit(self):
        snaps = self._st()["snapshots"]
        if snaps:
            snaps.pop()

    def revert(self, registry):
        snaps = self._st()["snapshots"]
        if snaps and isinstance(registry, dict):
            registry.clear()
            registry.update(snaps.pop())
            return True
        return False

    # ------------------------------------------------------------- the engineering-complete refactor operator
    def safe_refactor(self, prim, registry, apply_fn, reverify_fn):
        """Behavior-preserving restructure, gated by the regression suite.
        apply_fn(registry)                 -- mutates the registry (demote / re-rank / recompose)
        reverify_fn(p, frame_sig, pred)    -- bool: does this VERIFIED prediction still hold after the restructure?
        Returns dict(committed, orphaned, note). OBSERVE logs but keeps the restructure; ACTIVE reverts if unsafe."""
        if MODE == "off":
            apply_fn(registry)
            return {"committed": True, "orphaned": 0, "note": "off"}
        affected = [str(prim)] + self.dependents(prim)
        self.checkpoint(registry)
        apply_fn(registry)
        orphaned = 0
        for p in affected:
            for (fsig, pred) in list(self.verified_set(p)):
                try:
                    if not reverify_fn(p, fsig, pred):
                        orphaned += 1
                except Exception:
                    pass
        if orphaned > 0:
            if MODE == "active":
                self.revert(registry)
                self._st()["stats"]["revert"] += 1
                self._log("REVERT %s: would orphan %d verified predictions" % (prim, orphaned))
                return {"committed": False, "orphaned": orphaned, "note": "reverted (active)"}
            # observe: keep the restructure (existing behavior) but record that it was unsafe
            self.commit()
            self._st()["stats"]["would_revert"] += 1
            self._log("WOULD-REVERT %s: %d verified predictions at risk (observe-only)" % (prim, orphaned))
            return {"committed": True, "orphaned": orphaned, "note": "observe: not reverted"}
        self.commit()
        self._st()["stats"]["commit"] += 1
        self._log("COMMIT %s: 0 orphaned" % prim)
        return {"committed": True, "orphaned": 0, "note": "committed"}

    def gate_prunes(self, candidates, verified_names, reverify_fn=None):
        """Convenience for the win-condition PRUNE site: given predicate names slated for demotion, return the SUBSET to
        actually prune. ACTIVE keeps any that are verified invariants (won't orphan); OBSERVE returns all but logs."""
        if MODE == "off":
            return list(candidates)
        unsafe = [c for c in candidates if str(c) in verified_names]
        if MODE == "active" and unsafe:
            self._st()["stats"]["revert"] += len(unsafe)
            self._log("PRUNE-GATE kept %d verified predicate(s): %s" % (len(unsafe), unsafe))
            return [c for c in candidates if c not in unsafe]
        if unsafe:
            self._st()["stats"]["would_revert"] += len(unsafe)
            self._log("PRUNE-GATE would keep %d verified predicate(s) (observe): %s" % (len(unsafe), unsafe))
        return list(candidates)

    # ------------------------------------------------------------------------------------ diagnostics
    def _log(self, msg):
        lg = self._st()["log"]
        lg.append(msg)
        if len(lg) > LOG_CAP:
            del lg[:-LOG_CAP]

    def narrate(self):
        st = self._st()
        v = sum(len(s) for s in st["verified"].values())
        return ("refactor-ledger[%s]: %d verified predictions across %d primitives | %d contracts | "
                "commits=%d reverts=%d would-revert=%d"
                % (MODE, v, len(st["verified"]), len(st["contract"]),
                   st["stats"]["commit"], st["stats"]["revert"], st["stats"]["would_revert"]))

    def stats(self):
        return dict(self._st()["stats"])

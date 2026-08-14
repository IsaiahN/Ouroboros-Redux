"""W2a: the predictor bank -- one predictor per bound slot; every capable slot bets every action.

The board was one slot; now BODY, WORKSPACE, REFERENCE and RESOURCE each carry their own
predictor and their own residual. A slot that can't bet doesn't get read (bet=False).

  * BODY      -- per-action exact (dr, dc) delta evidence, established at >= min_evidence
                 consistent observations (the goal spine's note_move discipline).
  * WORKSPACE -- bets only through Gamma's stored EFFECT atoms for (game, level); a matching
                 atom's apply_effect IS the prediction (from_known_atom=True, and the
                 settlement names WHICH atom bet via "atom_key" -- the n=1 metric's linkage).
  * REFERENCE -- always bets "unchanged"; a mutated reference is a loud residual.
  * RESOURCE  -- per-action exact scalar delta evidence, same discipline as BODY.

B9: workspace settlements carry their frames ("committed", "observed") and "action" so the
router can feed a ConditionalMiner -- divergence is mined where it is seen.

B10: ClassFissionSocket -- per-object-class settlement outcomes tracked per INSTANCE; a
consistent verify/fail split (hidden types; essentialism, Xu-Carey) fissions the class into
class__a / class__b, the event exposed as a readable record for probes.

B11 (flag AGENT_MOTION_ENABLED): the AGENT_MOTION predictor family -- constructed only for
classes showing SELF-PROPELLED motion (moves with no acting click adjacent); bets next-step
constant-velocity AND pursuit-toward-target; settles like every other predictor.

Discipline: deterministic (no RNG, no wall-clock), every exception is swallowed to the
`errors` counter -- the bank must never crash the loop it advises. Works with gamma=None
(effects is imported lazily inside the workspace path only).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

__all__ = ["PredictorBank", "ClassFissionSocket", "AGENT_MOTION_ENABLED"]

AGENT_MOTION_ENABLED = True    # B11 module flag: the whole family off in one place

_MOTION_HISTORY = 16           # B11: positions kept per class (bounded)


def _no_bet(observed: Any) -> Dict[str, Any]:
    return {"bet": False, "predicted": None, "observed": observed,
            "residual": 0.0, "from_known_atom": False}


class PredictorBank:
    """commit(slot_states, action) then settle(observed_states) -> per-slot verdicts."""

    def __init__(self, gamma=None, game=None, level=None, min_evidence: int = 3):
        self.gamma = gamma
        self.game = game
        self.level = level
        self.min_evidence = int(min_evidence)
        # action -> {exact (dr, dc) delta -> count}
        self._body_evidence: Dict[int, Dict[Tuple[int, int], int]] = {}
        # action -> {exact float delta -> count}
        self._resource_evidence: Dict[int, Dict[float, int]] = {}
        self._pending: Optional[Dict[str, Any]] = None
        self._pending_action: Optional[int] = None
        # B11: per-class motion history and the constructed AGENT_MOTION families
        self._motion: Dict[Any, List[Tuple[int, int]]] = {}
        self._self_propelled: Dict[Any, int] = {}
        self._agent_families: set = set()
        self._agent_pending: Dict[Any, Tuple[Any, Any, Any]] = {}
        self.errors: int = 0

    # ── commit ────────────────────────────────────────────────────────────────

    def commit(self, slot_states: Dict[str, Any], action: int) -> None:
        try:
            self._pending = dict(slot_states)
            self._pending_action = int(action)
        except Exception:
            self.errors += 1
            self._pending = None
            self._pending_action = None

    # ── settle ────────────────────────────────────────────────────────────────

    def settle(self, observed_states: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        pending, action = self._pending, self._pending_action
        self._pending, self._pending_action = None, None
        if pending is None or action is None:
            return out
        for slot in pending:
            if slot not in observed_states:
                continue
            committed = pending[slot]
            observed = observed_states[slot]
            try:
                if slot == "BODY":
                    out[slot] = self._settle_body(committed, observed, action)
                elif slot == "WORKSPACE":
                    out[slot] = self._settle_workspace(committed, observed, action)
                elif slot == "REFERENCE":
                    out[slot] = self._settle_reference(committed, observed)
                elif slot == "RESOURCE":
                    out[slot] = self._settle_resource(committed, observed, action)
                else:
                    out[slot] = _no_bet(observed)
            except Exception:
                self.errors += 1
                out[slot] = _no_bet(observed)
        return out

    # ── BODY: per-action vector delta evidence ────────────────────────────────

    def _established(self, evidence: Dict[Any, int]) -> Optional[Any]:
        """Dominant exact delta seen >= min_evidence times (ties: smallest delta)."""
        if not evidence:
            return None
        best = min(sorted(evidence.items()), key=lambda kv: -kv[1])
        if best[1] >= self.min_evidence:
            return best[0]
        return None

    def _settle_body(self, committed: Tuple[int, int], observed: Tuple[int, int],
                     action: int) -> Dict[str, Any]:
        counts = self._body_evidence.setdefault(int(action), {})
        delta = self._established(counts)
        if delta is None:
            result = _no_bet(observed)
        else:
            predicted = (int(committed[0]) + delta[0], int(committed[1]) + delta[1])
            residual = float(abs(predicted[0] - int(observed[0])) +
                             abs(predicted[1] - int(observed[1])))
            result = {"bet": True, "predicted": predicted, "observed": observed,
                      "residual": residual, "from_known_atom": False}
        # ALWAYS learn from the observed transition, after settling.
        seen = (int(observed[0]) - int(committed[0]), int(observed[1]) - int(committed[1]))
        counts[seen] = counts.get(seen, 0) + 1
        return result

    # ── WORKSPACE: bets only through known EFFECT atoms ───────────────────────

    def _settle_workspace(self, committed: np.ndarray, observed: np.ndarray,
                          action: int) -> Dict[str, Any]:
        if self.gamma is None:
            return _no_bet(observed)
        from engines.egocentric.effects import Gamma, apply_effect  # lazy: gamma=None never pays
        records = self.gamma.fabric.query("collective", Gamma.TOPIC)
        for rec in records:
            if str(rec.get("game")) != str(self.game):
                continue
            if int(rec.get("level", -1)) != int(self.level):
                continue
            atom = rec.get("atom") or {}
            if atom.get("kind") != "EFFECT":
                continue
            if int(atom.get("action", -1)) != int(action):
                continue
            predicted = apply_effect(atom, np.asarray(committed))
            if predicted is None:
                continue                                    # context does not match here
            residual = self._grid_residual(predicted, observed)
            return {"bet": True, "predicted": predicted, "observed": observed,
                    "residual": residual, "from_known_atom": True,
                    "atom_key": rec.get("id"),              # WHICH atom bet (n=1 linkage)
                    "committed": committed, "action": int(action)}   # B9: divergence food
        return _no_bet(observed)

    # ── REFERENCE: always bets "unchanged" ────────────────────────────────────

    def _settle_reference(self, committed: np.ndarray, observed: np.ndarray) -> Dict[str, Any]:
        predicted = np.asarray(committed)
        residual = self._grid_residual(predicted, observed)
        return {"bet": True, "predicted": predicted, "observed": observed,
                "residual": residual, "from_known_atom": False}

    # ── RESOURCE: per-action scalar delta evidence ────────────────────────────

    def _settle_resource(self, committed: float, observed: float,
                         action: int) -> Dict[str, Any]:
        counts = self._resource_evidence.setdefault(int(action), {})
        delta = self._established(counts)
        if delta is None:
            result = _no_bet(observed)
        else:
            predicted = float(committed) + float(delta)
            result = {"bet": True, "predicted": predicted, "observed": observed,
                      "residual": abs(predicted - float(observed)),
                      "from_known_atom": False}
        seen = float(observed) - float(committed)
        counts[seen] = counts.get(seen, 0) + 1
        return result

    # ── B11: the AGENT_MOTION predictor family (flag AGENT_MOTION_ENABLED) ────

    def note_motion(self, object_class, position, click_cell=None) -> None:
        """One observed position for a class, via the ordinary observe path. A move with
        no acting click adjacent to where the object WAS is self-propelled (animacy);
        min_evidence such moves construct the family. Bounded history; never raises."""
        try:
            pos = (int(position[0]), int(position[1]))
            hist = self._motion.setdefault(object_class, [])
            if hist:
                prev = hist[-1]
                moved = pos != prev
                unaided = (click_cell is None
                           or max(abs(int(click_cell[0]) - prev[0]),
                                  abs(int(click_cell[1]) - prev[1])) > 1)
                if moved and unaided:
                    self._self_propelled[object_class] = (
                        self._self_propelled.get(object_class, 0) + 1)
            hist.append(pos)
            del hist[:-_MOTION_HISTORY]
            if (AGENT_MOTION_ENABLED
                    and self._self_propelled.get(object_class, 0) >= self.min_evidence):
                self._agent_families.add(object_class)
        except Exception:
            self.errors += 1

    def agent_family(self, object_class) -> bool:
        """True once the class has EARNED the AGENT_MOTION family."""
        return object_class in self._agent_families

    def commit_agent(self, object_class, position, target=None) -> bool:
        """Stake the family's next-step bets: constant-velocity (from the motion history)
        and pursuit (one step toward ``target``, when one is supplied)."""
        try:
            if object_class not in self._agent_families:
                self._agent_pending.pop(object_class, None)
                return False
            pos = (int(position[0]), int(position[1]))
            hist = self._motion.get(object_class) or []
            vel = None
            if len(hist) >= 2:
                vel = (hist[-1][0] - hist[-2][0], hist[-1][1] - hist[-2][1])
            tgt = None if target is None else (int(target[0]), int(target[1]))
            self._agent_pending[object_class] = (pos, vel, tgt)
            return True
        except Exception:
            self.errors += 1
            return False

    def settle_agent(self, object_class, observed_position) -> Dict[str, Any]:
        """Settle the staked bets against where the object actually went. The winning
        (lowest-residual, deterministic tie order) bet is the settlement the router
        reads; every bet's own residual stays visible in ``bets``."""
        try:
            obs = (int(observed_position[0]), int(observed_position[1]))
            pending = self._agent_pending.pop(object_class, None)
            if pending is None:
                return _no_bet(obs)
            pos, vel, tgt = pending
            bets: Dict[str, Dict[str, Any]] = {}
            if vel is not None:
                p = (pos[0] + vel[0], pos[1] + vel[1])
                bets["constant_velocity"] = {
                    "predicted": p,
                    "residual": float(abs(p[0] - obs[0]) + abs(p[1] - obs[1]))}
            if tgt is not None:
                step_r = (tgt[0] > pos[0]) - (tgt[0] < pos[0])
                step_c = (tgt[1] > pos[1]) - (tgt[1] < pos[1])
                p = (pos[0] + step_r, pos[1] + step_c)
                bets["pursuit"] = {
                    "predicted": p,
                    "residual": float(abs(p[0] - obs[0]) + abs(p[1] - obs[1]))}
            if not bets:
                return _no_bet(obs)
            winner = min(sorted(bets.items()), key=lambda kv: kv[1]["residual"])
            return {"bet": True, "family": "AGENT_MOTION", "bets": bets,
                    "winner": winner[0], "predicted": winner[1]["predicted"],
                    "observed": obs, "residual": winner[1]["residual"],
                    "from_known_atom": False}
        except Exception:
            self.errors += 1
            return _no_bet(observed_position)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _grid_residual(predicted: np.ndarray, observed: np.ndarray) -> float:
        p = np.asarray(predicted)
        o = np.asarray(observed)
        if p.shape != o.shape:
            return float(max(p.size, o.size))               # a reshape is maximally loud
        return float((p != o).sum())


# ── B10: the class-fission socket -- hidden types split a bimodal class ───────

class ClassFissionSocket:
    """Per-object-class settlement outcomes tracked per INSTANCE. When the same predicted
    transform verifies on some instances and fails on others -- each side consistent
    beyond (min_obs, purity) -- the class hides two types: FISSION it into class__a
    (the verifying mode) and class__b (the failing mode), distinguished by a
    discriminating feature when one value cleanly separates the sides, else by instance
    bucket. The event is a readable record in ``fission_events`` (the probe target);
    ``resolve()`` keys predictions on the subclass so they track separately. A class
    fissions at most once. Deterministic; never raises past the ``errors`` counter."""

    def __init__(self, min_obs: int = 3, purity: float = 0.75):
        self.min_obs = max(1, int(min_obs))
        self.purity = float(purity)
        self._outcomes: Dict[Any, Dict[Any, List[int]]] = {}   # class -> inst -> [ok, fail]
        self._features: Dict[Any, Dict[Any, Dict[str, Any]]] = {}
        self._fissioned: Dict[Any, Dict[str, Any]] = {}
        self.fission_events: List[Dict[str, Any]] = []
        self.errors: int = 0

    def note_outcome(self, object_class, instance, verified, features=None) -> None:
        """One settled prediction for one instance of the class: verified or failed."""
        try:
            counts = self._outcomes.setdefault(object_class, {}).setdefault(instance, [0, 0])
            counts[0 if verified else 1] += 1
            if features:
                self._features.setdefault(object_class, {})[instance] = dict(features)
            self._check(object_class)
        except Exception:
            self.errors += 1

    def resolve(self, object_class, instance, features=None):
        """The identity predictions should key on: the subclass after fission (by known
        instance, else by the discriminating feature), the class itself before."""
        try:
            fis = self._fissioned.get(object_class)
            if not fis:
                return object_class
            sub = fis["assignment"].get(instance)
            if sub is not None:
                return sub
            feat = fis["feature"]
            if feat and features is not None:
                if features.get(feat["name"]) == feat["a"]:
                    return "%s__a" % object_class
                if features.get(feat["name"]) == feat["b"]:
                    return "%s__b" % object_class
            return object_class                       # unknown instance, no feature: parent
        except Exception:
            self.errors += 1
            return object_class

    # -- internals ---------------------------------------------------------------

    def _mode(self, counts: List[int]) -> Optional[str]:
        ok, fail = counts
        total = ok + fail
        if total < self.min_obs or max(ok, fail) / float(total) < self.purity:
            return None                               # short or noisy: no mode yet
        return "verify" if ok > fail else "fail"

    def _check(self, object_class) -> None:
        if object_class in self._fissioned:
            return                                    # a class fissions at most once
        modes = {inst: self._mode(c) for inst, c in self._outcomes[object_class].items()}
        verifying = sorted(i for i, m in modes.items() if m == "verify")
        failing = sorted(i for i, m in modes.items() if m == "fail")
        if not verifying or not failing:
            return                                    # unimodal: no hidden type
        feature = self._discriminator(object_class, verifying, failing)
        assignment = {}
        for inst in verifying:
            assignment[inst] = "%s__a" % object_class
        for inst in failing:
            assignment[inst] = "%s__b" % object_class
        self._fissioned[object_class] = {"assignment": assignment, "feature": feature}
        self.fission_events.append({
            "class": object_class,
            "subclasses": ["%s__a" % object_class, "%s__b" % object_class],
            "assignment": dict(assignment),
            "feature": feature,
            "verifying": verifying,
            "failing": failing,
        })

    def _discriminator(self, object_class, verifying, failing) -> Optional[Dict[str, Any]]:
        """A feature whose value is uniform inside each side and different across them."""
        feats = self._features.get(object_class, {})
        names: set = set()
        for inst in list(verifying) + list(failing):
            names.update((feats.get(inst) or {}).keys())
        for name in sorted(names):
            va = {(feats.get(inst) or {}).get(name) for inst in verifying}
            vb = {(feats.get(inst) or {}).get(name) for inst in failing}
            if len(va) == 1 and len(vb) == 1 and va != vb:
                return {"name": name, "a": va.pop(), "b": vb.pop()}
        return None

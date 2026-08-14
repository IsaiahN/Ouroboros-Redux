"""W1b: RoleBinder -- one invariance classifier, four verdicts. Self-locus generalised.

Roles by INVARIANCE, never appearance:
  * BODY      -- moves contingently on my action (and NEVER changes without me:
                 any autonomous change disqualifies BODY -- the Goodhart guard,
                 inherited from the self-locus).
  * WORKSPACE -- mutates under my contact.
  * RESOURCE  -- a scalar drifts monotone under my actions.
  * REFERENCE -- invariant under ME (no action-contingent movement, no contact
                 mutation, no scalar drift). CK-2a: world-caused (exafferent)
                 change does not disqualify the world frame -- only MY
                 influence does.

Precedence when several could match: WORKSPACE > BODY > RESOURCE > REFERENCE
(mutation is the strongest evidence; reference only when nothing else fits).

CK-2a (von Holst; Wolpert) -- efference-copy subtraction: ``observe_attributed``
takes the cells an object actually changed plus the cells MY action was
predicted to change (``predicted_change_mask``); the intersection is
reafference (contact mutation), the remainder exafference (changed without
agent). The old radius-1 click-proximity heuristic misfiled both ways (g4=0).

Bindings are published per object class as {"slot": ..., "confidence": ...} with
confidence in (0, 1], or None while evidence is short of ``min_evidence``.
``on_level_change()`` clears everything: the maze redraws; bindings re-earn.

Stdlib only (numpy/effects load lazily inside ``predicted_change_mask`` and
only when a gamma is supplied). Deterministic -- no RNG anywhere. Defensive
try/except around the public surface with an ``errors`` counter so a malformed
observation can never take the loop down.
"""
from __future__ import annotations


class _ClassEvidence:
    """Per-object-class evidence counters. Pure bookkeeping, no verdicts."""

    __slots__ = (
        "observations",
        "moves_by_action",   # action id -> [moved_count, total_count]
        "move_count",
        "mutation_count",
        "autonomous_count",
        "delta_pos",
        "delta_neg",
    )

    def __init__(self):
        self.observations = 0
        self.moves_by_action = {}
        self.move_count = 0
        self.mutation_count = 0
        self.autonomous_count = 0
        self.delta_pos = 0
        self.delta_neg = 0


class RoleBinder:
    """Bind object classes to functional slots by accrued invariance evidence."""

    SLOT_BODY = "BODY"
    SLOT_WORKSPACE = "WORKSPACE"
    SLOT_REFERENCE = "REFERENCE"
    SLOT_RESOURCE = "RESOURCE"

    def __init__(self, min_evidence=3):
        self.min_evidence = max(1, int(min_evidence))
        self._evidence = {}   # object_class -> _ClassEvidence
        self.errors = 0

    # ------------------------------------------------------------------ #
    # evidence accrual
    # ------------------------------------------------------------------ #
    def observe(self, object_class, action, moved_with_action,
                mutated_on_contact, changed_without_agent, scalar_delta):
        """Accrue one observation of ``object_class`` under ``action``."""
        try:
            ev = self._evidence.get(object_class)
            if ev is None:
                ev = _ClassEvidence()
                self._evidence[object_class] = ev
            ev.observations += 1

            moved = bool(moved_with_action)
            slot = ev.moves_by_action.get(action)
            if slot is None:
                slot = [0, 0]
                ev.moves_by_action[action] = slot
            slot[1] += 1
            if moved:
                slot[0] += 1
                ev.move_count += 1

            if bool(mutated_on_contact):
                ev.mutation_count += 1
            if bool(changed_without_agent):
                ev.autonomous_count += 1

            delta = float(scalar_delta) if scalar_delta is not None else 0.0
            if delta > 0.0:
                ev.delta_pos += 1
            elif delta < 0.0:
                ev.delta_neg += 1
        except Exception:
            self.errors += 1

    def observe_attributed(self, object_class, action, moved_with_action,
                           mutated, changed_cells, predicted_mask,
                           scalar_delta=0):
        """CK-2a: efference-copy subtraction (von Holst; Wolpert).

        ``changed_cells`` are the (row, col) cells this object actually changed;
        ``predicted_mask`` the cells MY action was predicted to change (see
        ``predicted_change_mask``). A mutation intersecting the mask is
        reafference -- my own contact echoing back -- and accrues
        mutated_on_contact; a mutation entirely outside it is exafference --
        the world moving on its own -- and accrues changed_without_agent.
        Delegates to ``observe``: one evidence store, sharper flags.
        """
        try:
            mut = bool(mutated)
            hit = False
            if mut:
                cells = {tuple(c) for c in (changed_cells or ())}
                mask = {tuple(c) for c in (predicted_mask or ())}
                hit = bool(cells & mask)
            self.observe(object_class, action, moved_with_action,
                         mutated_on_contact=(mut and hit),
                         changed_without_agent=(mut and not hit),
                         scalar_delta=scalar_delta)
        except Exception:
            self.errors += 1

    @staticmethod
    def predicted_change_mask(pre_frame, action, click_cell,
                              gamma=None, game=None, level=None, bank=None):
        """The efference copy: (row, col) cells MY action is predicted to change.

        Best source first: the committed prediction -- the FIRST stored EFFECT
        atom for this (game, level, action) whose context matches ``pre_frame``
        (the bank's own workspace discipline), its diff being the mask. Floor:
        the clicked cell and its radius-1 neighbourhood (the old heuristic).
        ``bank`` supplies gamma/game/level when not given. Never raises.
        """
        mask = set()
        try:
            if bank is not None:
                if gamma is None:
                    gamma = getattr(bank, "gamma", None)
                if game is None:
                    game = getattr(bank, "game", None)
                if level is None:
                    level = getattr(bank, "level", None)
            if gamma is not None and pre_frame is not None:
                import numpy as _np  # lazy: the floor never pays

                from engines.egocentric.effects import Gamma as _G
                from engines.egocentric.effects import apply_effect as _ap
                _pre = _np.asarray(pre_frame)
                for _rec in gamma.fabric.query("collective", _G.TOPIC):
                    _atom = _rec.get("atom") or {}
                    if (_atom.get("kind") != "EFFECT"
                            or str(_rec.get("game")) != str(game)
                            or int(_rec.get("level", -1)) != int(level)
                            or int(_atom.get("action", -1)) != int(action)):
                        continue
                    _prd = _ap(_atom, _pre)
                    if _prd is None or _prd.shape != _pre.shape:
                        continue                   # context does not match here
                    mask.update((int(r), int(c))
                                for r, c in _np.argwhere(_prd != _pre))
                    break                          # the committed prediction
        except Exception:
            mask = set()
        try:
            if not mask and click_cell is not None:
                _r0, _c0 = int(click_cell[0]), int(click_cell[1])
                mask = {(_r0 + dr, _c0 + dc)
                        for dr in (-1, 0, 1) for dc in (-1, 0, 1)}
        except Exception:
            pass
        return mask

    # ------------------------------------------------------------------ #
    # verdicts
    # ------------------------------------------------------------------ #
    def binding(self, object_class):
        """Return {"slot": ..., "confidence": ...} or None if unbound."""
        try:
            ev = self._evidence.get(object_class)
            if ev is None or ev.observations < self.min_evidence:
                return None
            total = ev.observations

            # WORKSPACE: contact mutation is the strongest evidence.
            if ev.mutation_count >= self.min_evidence:
                return self._publish(self.SLOT_WORKSPACE, ev.mutation_count, total)

            # BODY: movement contingent on my action, and NEVER autonomous.
            if ev.autonomous_count == 0 and self._moves_contingently(ev):
                return self._publish(self.SLOT_BODY, ev.move_count, total)

            # RESOURCE: all observed nonzero deltas share one sign.
            nonzero = ev.delta_pos + ev.delta_neg
            if nonzero >= self.min_evidence and (ev.delta_pos == 0 or ev.delta_neg == 0):
                return self._publish(self.SLOT_RESOURCE, nonzero, total)

            # REFERENCE: invariant under the AGENT -- nothing else fits.
            # CK-2a: exafference tolerated -- the world changing on its own
            # does not disqualify the world frame; only MY influence does.
            if ev.move_count == 0 and ev.mutation_count == 0 and nonzero == 0:
                return self._publish(self.SLOT_REFERENCE, total, total)

            return None
        except Exception:
            self.errors += 1
            return None

    @staticmethod
    def _moves_contingently(ev):
        """Contingency, not correlation: movement must depend on what I do.

        With several actions observed, the per-action move rate must differ
        (moves under some actions and not others, or at different rates).
        With a single action observed, any movement is contingent against the
        implicit no-action baseline -- provided autonomy is zero, which the
        caller has already checked.
        """
        if ev.move_count == 0:
            return False
        rates = [moved / float(seen) for moved, seen in ev.moves_by_action.values() if seen > 0]
        if not rates:
            return False
        if len(rates) == 1:
            return rates[0] > 0.0
        return max(rates) > min(rates)

    @staticmethod
    def _publish(slot, supporting, total):
        conf = supporting / float(total) if total > 0 else 0.0
        conf = min(1.0, max(conf, 1.0 / float(total) if total > 0 else 0.0))
        return {"slot": slot, "confidence": conf}

    # ------------------------------------------------------------------ #
    # level lifecycle
    # ------------------------------------------------------------------ #
    def on_level_change(self):
        """The maze redraws; all evidence and bindings must re-earn themselves."""
        try:
            self._evidence = {}
        except Exception:
            self.errors += 1

    def on_fission(self, object_class):
        """B10: the class fissioned (bank.ClassFissionSocket) -- the parent identity's
        evidence conflated two hidden types and is stale. Drop it; the subclass
        identities (class__a / class__b) re-earn their own bindings from scratch."""
        try:
            self._evidence.pop(object_class, None)
        except Exception:
            self.errors += 1

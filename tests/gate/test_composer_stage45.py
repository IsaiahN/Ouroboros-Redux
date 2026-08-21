"""COMPOSER STAGE 4.5 -- THE SEAM REPAIRS (record/findings/COMPOSER_SEAM_READ.md).

Stages 1-4 each passed their own falsifiers; their COMBINATION had four
silent successes. The build under test (engines/egocentric/composer.py,
consumer.extent_bargain, applicability._derive_composite, observer's exact
cell, the cognitive_loop seams _w3c_compose / _w3d_site / _w3d_drive /
_w3d_continue) makes each fail LOUDLY (a fixed reason token on the PLAN
record or the attempt's result) or cannot occur.

The falsifiers, as gated here -- each reproduced on the OLD behaviour's
shape and asserted both directions:
  S1  predicate mode already satisfied: the WANT is checked against frame0
      FIRST (want-already-satisfied, no candidates read); _advances requires
      a FLIP (baseline compared); the drive record carries the predicate and
      the live settle re-verifies the flip (predicate-unmet) -- a genuine
      flip still composes, drives and settles.
  S2  csig-less composites: no derived signature -> REFUSED
      (csig-underivable), never inf-ranked; every LOCAL mint pays the import
      door's inequality (consumer.extent_bargain, ONE statement) before
      compose() -- a dear chain is price-refused with the price stated, the
      cheap sibling admits; admission_price and the local mint quote the
      same cost/bar.
  S3  act_offset None: an offset-less atom composes as a no-movement chain
      ONLY (compose-only, no-act-offset on the PLAN record, shadowed, never
      driven); _w3d_site never synthesises a site from the patch centre; the
      reach's anchor, the simulation's stamp and the drive's click site are
      ONE cell carried on the chain (a world where anchors[0] is the WRONG
      anchor composes and drives at the right one).
  S4  the avatar-independent final seam: after a BODY prefix the avatar's
      colour must occupy the act cell (the check fails on a wrong colour);
      a prefix that contributes nothing (frame0 already wears the avatar
      colour at the act cell) is dropped -- the shorter chain mints with
      prefix-unnecessary; a necessary prefix is kept (prefix-required) and
      its avatar-at-act-cell check passes.
  H   handoffs: is_citable / citation_allowed read the STREAM RECORD via
      gamma (an id + gamma works; gamma.get's atom is refused loudly);
      reach["verified"] is READ (True -> reach-contract-breach); the loop
      states the avatar source (self-cell exact / centroid-rounded fallback).
  R4  exact drive->settle sequences through the real seams on the
      reconciled-anchor world and on a predicate-mode chain.
  KNOWN-NEGATIVES: malformed drive records, stale anchors, idless reads.
  STRUCTURAL: one inequality (extent_bargain) for door and local mint; no
      patch-centre synthesis in _w3d_site; no inf sentinel in _attempt.

Seeded with a FIXED CONSTANT (the build date), never a clock.
"""
from __future__ import annotations

import ast
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import cognitive_loop as cl  # noqa: E402
from engines.egocentric import applicability as A  # noqa: E402
from engines.egocentric import composer as C  # noqa: E402
from engines.egocentric import consumer as CO  # noqa: E402
from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric import enables as EN  # noqa: E402
from engines.egocentric import narration as na  # noqa: E402
from engines.egocentric import scheduler as sch  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.goal_abduction import satisfies  # noqa: E402
from engines.egocentric.mint import MDLMint  # noqa: E402

SEED = 20260821  # fixed constant (the build date) -- deterministic forever

DELTAS4 = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


# ── constructions (stage 4's world, plus the seam-read's counter-worlds) ──────

def _gamma(tmp_path, name):
    return E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a",
                                   kin_key="v4"))


def _atom(ctx, out, key, action=6, ttype=None, params=None):
    ctx_l = [[int(v) for v in row] for row in ctx]
    out_l = [[int(v) for v in row] for row in out]
    a = {"kind": "EFFECT", "arity": 2, "key": key, "action": action,
         "context": ctx_l,
         "transform": {"before": ctx_l, "after": out_l},
         "changed": int((np.asarray(ctx) != np.asarray(out)).sum())}
    if ttype:
        a["ttype"] = ttype
        a["params"] = dict(params or {})
    return a


def _click_atom(ctx, out, key, dr, dc):
    a = _atom(ctx, out, key)
    a[EN.ACT_OFFSET_FIELD] = {"v": EN.ACT_OFFSET_VERSION,
                              "dr": int(dr), "dc": int(dc)}
    return a


def _mv_right(key="mv-right"):
    return _atom([[7, 0]], [[0, 7]], key, action=4, ttype="TRANSLATE",
                 params={"dx": 0, "dy": 1, "fill": 0})


def _world(tmp_path, name):
    """Stage 4's world: avatar 7 at (0,0); button 3 at (2,4); B (writes 9)
    anchored on the button, act cell (0,4). WANT = 9 at (2,4)."""
    f = np.zeros((3, 6), dtype=int)
    f[0, 0] = 7
    f[2, 4] = 3
    g = _gamma(tmp_path, name)
    ids = {"mv": g.add(_mv_right(), "g1", 1),
           "B": g.add(_click_atom([[3]], [[9]], "click-b", -2, 0), "g1", 1)}
    return f, g, ids, [(2, 4, 9)]


def _two_anchor_world(tmp_path, name, avatar_col=3):
    """THE RECONCILED-ANCHOR WORLD: two buttons (3) at (2,1) and (2,4); B
    matches BOTH (anchors[0] = (2,1)); the WANT is 9 at (2,4) ONLY. The
    avatar 7 at (0, avatar_col) is nearer (0,4) = the act cell of anchor
    (2,4) -- the reach picks the SECOND anchor. Before stage 4.5 the final
    seam applied at apply_effect's FIRST anchor (2,1), advanced nothing at
    (2,4), and the chain died unverified."""
    f = np.zeros((3, 6), dtype=int)
    f[0, avatar_col] = 7
    f[2, 1] = 3
    f[2, 4] = 3
    g = _gamma(tmp_path, name)
    ids = {"mv": g.add(_mv_right(), "g1", 1),
           "B": g.add(_click_atom([[3]], [[9]], "click-b", -2, 0), "g1", 1)}
    return f, g, ids, [(2, 4, 9)]


def _records(g, aid):
    return [r for r in g.fabric.query("collective", g.TOPIC)
            if r.get("id") == aid]


def _composites(g):
    return [r for r in g.fabric.query("collective", g.TOPIC)
            if (r.get("atom") or {}).get("kind") == "COMPOSITE"]


def _ns(tmp_path, name, g, verified=None, self_cell=None):
    """The loop namespace at the stage-4 seams (stage 4's construction) --
    plus the optional self-locus EXACT cell (stage 4.5)."""
    ns = SimpleNamespace(
        _ego_fabric=KnowledgeFabric(str(tmp_path / name), agent_id="a",
                                    kin_key="v4"),
        _game_id="g1", _actions_taken=0, _ego_agent_id="a", _ego_level=0,
        _w2b_sched=sch.PlannerScheduler(), _w2b_narr=None, _w2b_driven=None,
        _w2b_key=None, _w3d_chain=None,
        _w4c_counters={"mint_passed": 0}, _narr_import_n=0,
        _narration=None, _narr_slots=None,
        _atom_verified=dict(verified or {}),
        _residual_router=None,
        _plan_gate={"g1": 0, "g2": 0, "g3": 0, "g4": 0, "g5": 0, "g6": 0,
                    "g7": 0, "shadow": 0, "drive": 0, "cycles": 1},
        _narr_settle=None, _narr_mint=None, _prev_frame=None,
        _ego_seeded={}, _ego_seeded_clicks={}, _gamma=g, _mdl_mint=MDLMint(g),
        _ego_prev_centroid=(0, 0), _ego_frontier_book=None,
        _ego_harvest_cache=None,
        _perceiver=SimpleNamespace(_to_numpy=np.asarray))
    if self_cell is not None:
        ns._ego_self_cell = tuple(self_cell)
        ns._ego_prev_centroid = (float(self_cell[0]) + 0.4,
                                 float(self_cell[1]) - 0.4)
    return ns


def _cf(conf=0.0, speed="explore"):
    return SimpleNamespace(action_confidence=float(conf), rung_name="",
                           action_speed=str(speed))


def _plan_records(ns):
    return [r for r in ns._ego_fabric.query("personal", na.TOPIC)
            if r["point"] == na.PLAN]


def _compose(ns, f, want, avatar=(0, 0)):
    """Engage the gate, compose with the CONSTRUCTED deltas (the loop seam
    reads the action book, which a constructed game lacks), stage the
    narration _w3c_compose would."""
    assert cl._w2b_engage(ns, f, _cf(0.0)) is True, "construction: gate opens"
    res = C.compose_attempt(want, f, ns._gamma, avatar, DELTAS4, set(), "g1", 1)
    assert res["reason"] == C.COMPOSED, (
        "construction: the world must compose; got %r" % (res,))
    res["avatar"] = C.AVATAR_CENTROID
    ns._w2b_narr = ("composed", res["composite"],
                    {"settled": False, "driven": False,
                     "avatar": C.AVATAR_CENTROID, "prefix": res.get("prefix")})
    return res


def _drive(ns, f, res):
    step = cl._w3d_drive(ns, f, res)
    cl._narr_bet(ns, step[0] if step else 6, _cf(0.0), {})
    return step


def _land(ns, pre, post, level_changed=False):
    ns._prev_frame = np.asarray(pre)
    cl._w3d_settle(ns, np.asarray(post), level_changed)
    cl._w2b_abort(ns, bool((np.asarray(pre) != np.asarray(post)).any()),
                  level_changed)


def _cont(ns, frame):
    ns._actions_taken += 1
    step = cl._w3d_continue(ns, frame)
    if step is not None:
        cl._narr_bet(ns, step[0], _cf(0.0), {})
    return step


def _pool(g):
    order, atoms = [], {}
    for rec in g.fabric.query("collective", g.TOPIC):
        aid = str(rec.get("id"))
        if aid not in atoms:
            order.append(aid)
        atoms[aid] = rec.get("atom")
    return order, atoms


# ── S1 · predicate mode already satisfied ─────────────────────────────────────

class TestS1WantAlreadySatisfied:

    def test_a_satisfied_predicate_want_refuses_before_any_candidate(
            self, tmp_path):
        """THE OLD SHAPE: 9 is already present; B (writes 9) applies; the
        baseline-free test satisfies(pred, result) said 'advanced' and the
        cheapest chain minted. NOW: want-already-satisfied, nothing read."""
        g = _gamma(tmp_path, "s1a")
        g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)
        f = np.array([[3, 9]], dtype=int)
        pred = {"kind": "colour_present", "colour": 9}
        assert satisfies(pred, f), "construction: the WANT already holds"
        # the old decider's shape: the predicate holds on the applied frame
        applied = E.apply_effect(g.get(g.fabric.query("collective", g.TOPIC)[0]["id"]), f)
        assert applied is not None and satisfies(pred, applied)
        assert C._advances(f, applied, None, pred) is False, (
            "S1 FALSIFIED: holding already counted as advancing (no baseline)")
        res = C.compose_attempt(pred, f, g, None, {}, set(), "g1", 1)
        assert res["composite"] is None and res["reason"] == C.R_WANT_SATISFIED, (
            "S1 FALSIFIED: a satisfied WANT composed -- %r" % (res,))
        assert res["candidates"] == 0, "refused BEFORE the pool is read"
        assert _composites(g) == []

    def test_a_satisfied_cells_want_refuses(self, tmp_path):
        g = _gamma(tmp_path, "s1b")
        g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)
        res = C.compose_attempt([(0, 0, 9)], np.array([[9]], dtype=int), g,
                                None, {}, set(), "g1", 1)
        assert res["reason"] == C.R_WANT_SATISFIED and res["composite"] is None
        # a partly-satisfied cells WANT still composes toward the rest
        res = C.compose_attempt([(0, 0, 9), (0, 1, 9)],
                                np.array([[9, 3]], dtype=int), g, None, {},
                                set(), "g1", 1)
        assert res["reason"] == C.COMPOSED

    def test_a_genuine_flip_composes_drives_and_settles_live(self, tmp_path):
        """Both directions: 9 absent -> the flip composes; the drive record
        carries the predicate; the live settle verifies the flip on the
        LIVE frame and states it in the settle facts."""
        g = _gamma(tmp_path, "s1c")
        bid = g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)
        f = np.array([[3, 0]], dtype=int)
        pred = {"kind": "colour_present", "colour": 9}
        res = C.compose_attempt(pred, f, g, None, {}, set(), "g1", 1)
        assert res["reason"] == C.COMPOSED and res["chain"] == [bid]
        assert res["want_cells"] is None and res["pred"] == pred
        drive = C.drive_record(res)
        assert drive is not None and drive["pred"] == pred, (
            "S1 FALSIFIED: the drive record does not carry the predicate")
        out = C.live_settle(g, drive, np.array([[9, 0]], dtype=int))
        assert out["settled"] is True and out["reason"] == C.S_SETTLED
        rec = _records(g, res["composite"])[-1]
        assert rec["settle"] == {"steps": 1, "cells": 1, "want": 0,
                                 "predicate": True}

    def test_the_live_settle_verifies_the_flip_not_just_the_cells(
            self, tmp_path):
        """want_cells=None NEVER means 'no check': a drive whose predicate
        already held at drive start (the forged baseline) cannot settle
        even when every predicted cell matches live -- predicate-unmet."""
        g = _gamma(tmp_path, "s1d")
        g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)
        f = np.array([[3, 0]], dtype=int)
        pred = {"kind": "colour_present", "colour": 9}
        res = C.compose_attempt(pred, f, g, None, {}, set(), "g1", 1)
        drive = C.drive_record(res)
        forged = dict(drive)
        forged["frame0"] = np.array([[9, 0]], dtype=int)   # already held
        forged["frames"] = [np.array([[9, 0]], dtype=int)]
        v = C.settle_verdict(forged, np.array([[9, 0]], dtype=int))
        assert v["diverged"] == [] and v["predicate"] is False
        assert v["settled"] is False, (
            "S1 FALSIFIED: a cell match settled a predicate that never flipped")
        out = C.live_settle(g, forged, np.array([[9, 0]], dtype=int))
        assert out["settled"] is False and out["reason"] == C.S_PRED_UNMET
        assert out["written"] is False
        assert len(_records(g, res["composite"])) == 1
        # and drive_record itself refuses a result whose predicate holds on
        # frame0, or that carries neither cells nor a predicate
        bad = dict(res)
        bad["frame0"] = np.array([[9, 0]], dtype=int)
        assert C.drive_record(bad) is None
        bad2 = dict(res)
        bad2["pred"] = None
        assert C.drive_record(bad2) is None, (
            "S1 FALSIFIED: want_cells=None with no predicate drove")


# ── S2 · csig-less composites and the priced local mint ───────────────────────

class TestS2PricedLocalMint:

    def test_a_csig_less_chain_is_refused_not_inf_ranked(self, tmp_path,
                                                           monkeypatch):
        """THE OLD SHAPE: composite_signature None -> price inf -> still
        ranked, still minted, index-invisible. NOW: csig-underivable, no
        mint, the verified count still states the chain simulated."""
        g = _gamma(tmp_path, "s2a")
        g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)
        f = np.array([[3, 0]], dtype=int)
        monkeypatch.setattr(C._app, "composite_signature",
                            lambda parts, resolver: None)
        res = C.compose_attempt([(0, 0, 9)], f, g, None, {}, set(), "g1", 1)
        assert res["composite"] is None, (
            "S2 FALSIFIED: a csig-less chain minted -- %r" % (res,))
        assert res["reason"] == C.R_CSIG_UNDERIVABLE and res["verified"] == 1
        assert res["refused"] == [{"reason": C.R_CSIG_UNDERIVABLE, "price": None}]
        assert _composites(g) == []

    def test_a_dear_chain_is_price_refused_the_cheap_sibling_admits(
            self, tmp_path):
        """A 4x4 context retaining 15 cells around one changed cell: derived
        price 16 -> cost 2.8 vs bar 2.7 at the mint's constants -> REFUSED,
        the price stated. The 1x1 sibling (price 1) admits and mints."""
        g = _gamma(tmp_path, "s2b")
        ctx = [[3, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]]
        out = [[9, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]]
        dear = g.add(_atom(ctx, out, "eff-dear"), "g1", 1)
        f = np.asarray(ctx, dtype=int)
        res = C.compose_attempt([(0, 0, 9)], f, g, None, {}, set(), "g1", 1)
        assert res["composite"] is None and res["reason"] == C.R_PRICE_REFUSED, (
            "S2 FALSIFIED: the dear chain minted unpriced -- %r" % (res,))
        assert res["verified"] == 1 and res["price"] == 16
        ref = res["refused"][0]
        assert ref["reason"] == C.R_PRICE_REFUSED and ref["price"] == 16
        assert ref["cost"] > ref["bar"], "refused by the bar, stated"
        assert _composites(g) == []
        # ONE STATEMENT: the import door quotes the identical verdict for a
        # composite carrying the same derived signature
        csig = A.composite_signature([dear], g.get)
        assert csig["price"] == 16 and csig["changed"] == 1
        door = CO.admission_price({"kind": "COMPOSITE", "csig": csig})
        assert door["admit"] is False
        assert door["cost"] == ref["cost"] and door["bar"] == ref["bar"]
        assert CO.extent_bargain(1, 16.0)["cost"] == ref["cost"]
        # the cheap sibling admits: both directions
        cheap = g.add(_atom([[3]], [[9]], "eff-cheap"), "g1", 1)
        res = C.compose_attempt([(0, 0, 9)], f, g, None, {}, set(), "g1", 1)
        assert res["reason"] == C.COMPOSED and res["chain"] == [cheap]
        assert res["price"] == 1 and res["verified"] == 2
        assert res["refused"][0]["reason"] == C.R_PRICE_REFUSED
        assert CO.extent_bargain(1, 1.0)["admit"] is True

    def test_the_door_and_the_local_mint_share_one_inequality(self):
        """Structural: admission_price holds no inequality of its own --
        both branches call extent_bargain; composer._attempt calls it before
        compose(); MDL_MARGIN is consulted in exactly one function."""
        csrc = open(os.path.join(REPO, "engines", "egocentric", "consumer.py"),
                    encoding="utf-8").read()
        ctree = ast.parse(csrc)
        ap = _fn(ctree, "admission_price")
        assert len(_calls(ap, "extent_bargain")) == 2, (
            "S2 FALSIFIED: the door does not delegate both branches")
        assert "MDL_MARGIN" not in _body_source(csrc, ap), (
            "S2 FALSIFIED: the door still states the inequality itself "
            "(its docstring may document it; its code may not hold it)")
        eb = _fn(ctree, "extent_bargain")
        assert "MDL_MARGIN" in _body_source(csrc, eb)
        msrc = open(os.path.join(REPO, "engines", "egocentric", "composer.py"),
                    encoding="utf-8").read()
        mtree = ast.parse(msrc)
        at = _fn(mtree, "_attempt")
        assert len(_calls(at, "extent_bargain")) == 1
        assert "MDL_MARGIN" not in msrc
        infs = [n for n in _calls(at, "float")
                if n.args and isinstance(n.args[0], ast.Constant)
                and n.args[0].value == "inf"]
        assert infs == [], (
            "S2 FALSIFIED: the inf sentinel survives in _attempt")
        seg = _body_source(msrc, at)
        assert seg.index("extent_bargain") < seg.index("gamma.compose("), (
            "the bargain must be paid BEFORE the mint")


# ── S3 · act_offset None and the reconciled anchor ────────────────────────────

class TestS3OffsetAndAnchor:

    def test_an_offset_less_atom_composes_only_and_is_never_driven(
            self, tmp_path):
        """THE OLD SHAPE: _w3d_site synthesised (patch centre) for an atom
        with no act_offset and the composite drove. NOW: the attempt notes
        no-act-offset, the drive shadows with the token, g7 untouched."""
        f = np.array([[3, 0], [0, 1]], dtype=int)
        g = _gamma(tmp_path, "s3a")
        bid = g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)
        atom = g.get(bid)
        assert cl._w3d_site(f, atom, (0, 0)) is None, (
            "S3 FALSIFIED: a site was synthesised for an offset-less atom")
        ns = _ns(tmp_path, "s3a_n", g, verified={bid: 2})
        assert cl._w2b_engage(ns, f, _cf(0.0)) is True
        res = cl._w3c_compose(ns, f, [(0, 0, 9)])
        assert res is not None and res["reason"] == C.COMPOSED
        assert res["notes"] == {C.NO_ACT_OFFSET: 1} and res["actions"] == []
        assert res["anchor"] == (0, 0), "the simulation's anchor is recorded"
        assert _drive(ns, f, res) is None, "S3 FALSIFIED: it drove"
        assert ns._plan_gate["g7"] == 0 and ns._plan_gate["shadow"] == 1
        assert ns._w3d_chain is None and ns._w2b_driven is None
        plan = _plan_records(ns)[-1]
        assert plan["mode"] == "composed" and plan["driven"] is False
        assert plan["reason"] == C.NO_ACT_OFFSET and plan["parts"] == [bid]
        assert plan["avatar"] == C.AVATAR_CENTROID

    def test_the_reach_anchor_the_stamp_and_the_click_are_one_cell(
            self, tmp_path):
        """THE OLD SHAPE: anchors[0] = (2,1) everywhere -- the final seam
        applied there, advanced nothing at (2,4), the chain died unverified
        (and had it lived, the drive would have clicked (0,1)). NOW: the
        reach's anchor (2,4) is the stamp and the site."""
        f, g, ids, want = _two_anchor_world(tmp_path, "s3b")
        anch = C._anchors(f, g.get(ids["B"]))
        assert anch == [(2, 1), (2, 4)], "construction: two anchors, (2,1) first"
        old = E.apply_effect(g.get(ids["B"]), f)
        assert int(old[2, 1]) == 9 and int(old[2, 4]) == 3, (
            "construction: apply_effect's first anchor is the WRONG one")
        res = C.compose_attempt(want, f, g, (0, 3), DELTAS4, set(), "g1", 1)
        assert res["reason"] == C.COMPOSED, (
            "S3 FALSIFIED: the second-anchor chain did not compose -- %r" % (res,))
        assert res["chain"] == [ids["mv"], ids["B"]] and res["actions"] == [4]
        assert res["anchor"] == (2, 4) and res["act"] == (0, 4)
        assert res["anchors"] == [None, (2, 4)]
        assert int(res["frames"][-1][2, 4]) == 9 and int(res["frames"][-1][2, 1]) == 3
        assert res["prefix"] == C.PREFIX_REQUIRED
        ns = _ns(tmp_path, "s3b_n", g, verified={ids["mv"]: 2, ids["B"]: 2})
        res = _compose(ns, f, want, avatar=(0, 3))
        assert _drive(ns, f, res) == (4, None)
        drive = ns._w3d_chain["drive"]
        _land(ns, f, drive["frames"][0])
        step = _cont(ns, drive["frames"][0])
        assert step == (6, {'x': 4, 'y': 0}), (
            "S3 FALSIFIED: the drive clicked elsewhere than the reconciled "
            "anchor's act cell; got %r" % (step,))

    def test_the_no_movement_path_drops_the_anchors0_assumption(self, tmp_path):
        """Avatar ALREADY at the act cell of the SECOND anchor: the chain is
        [B] alone, stamped and driven at (2,4), not anchors[0]."""
        f, g, ids, want = _two_anchor_world(tmp_path, "s3c", avatar_col=4)
        res = C.compose_attempt(want, f, g, (0, 4), DELTAS4, set(), "g1", 1)
        assert res["reason"] == C.COMPOSED and res["chain"] == [ids["B"]]
        assert res["anchor"] == (2, 4) and res["actions"] == []
        assert int(res["frames"][-1][2, 4]) == 9
        ns = _ns(tmp_path, "s3c_n", g, verified={ids["B"]: 2})
        res = _compose(ns, f, want, avatar=(0, 4))
        assert _drive(ns, f, res) == (6, {'x': 4, 'y': 0})


# ── S4 · the avatar-dependent final seam ──────────────────────────────────────

class TestS4PrefixNecessity:

    def test_a_prefix_that_contributes_nothing_is_dropped(self, tmp_path):
        """THE OLD SHAPE: self-locus says (0,0) but the act cell (0,4)
        already wears the avatar's colour; the reach proposed 4 moves and
        the 5-part chain minted, billing and driving a prefix the click
        never needed. NOW: the shorter chain mints, prefix-unnecessary."""
        f = np.zeros((3, 6), dtype=int)
        f[0, 0] = 7                              # the self-locus cell
        f[0, 4] = 7                              # the act cell already worn
        f[2, 4] = 3
        g = _gamma(tmp_path, "s4a")
        mv = g.add(_mv_right(), "g1", 1)
        bid = g.add(_click_atom([[3]], [[9]], "click-b", -2, 0), "g1", 1)
        reach = EN.cross_shelf_reach(g.get(bid), [(2, 4)], (0, 0), DELTAS4,
                                     (3, 6))
        assert reach is not None and reach["chain"] == [4, 4, 4, 4], (
            "construction: the algebra still proposes the 4-step prefix")
        res = C.compose_attempt([(2, 4, 9)], f, g, (0, 0), DELTAS4, set(),
                                "g1", 1)
        assert res["reason"] == C.COMPOSED
        assert res["chain"] == [bid] and res["actions"] == [], (
            "S4 FALSIFIED: a prefix that contributed nothing was minted -- "
            "%r" % (res["chain"],))
        assert res["prefix"] == C.PREFIX_UNNECESSARY and res["price"] == 1
        assert res["anchor"] == (2, 4) and res["act"] == (0, 4)
        assert res["proposed"] == 2, "both variants proposed; the short wins"
        assert mv not in res["chain"]
        ns = _ns(tmp_path, "s4a_n", g, verified={mv: 2, bid: 2})
        assert cl._w2b_engage(ns, f, _cf(0.0)) is True
        res2 = C.compose_attempt([(2, 4, 9)], f, g, (0, 0), DELTAS4, set(),
                                 "g1", 1)
        res2["avatar"] = C.AVATAR_CENTROID
        assert cl._w3d_drive(ns, f, res2) == (6, {'x': 4, 'y': 0})
        cl._narr_bet(ns, 6, _cf(0.0), {})
        plan = _plan_records(ns)[-1]
        assert plan["prefix"] == C.PREFIX_UNNECESSARY and plan["driven"] is True

    def test_a_necessary_prefix_is_kept_and_the_avatar_check_passes(
            self, tmp_path):
        f, g, ids, want = _world(tmp_path, "s4b")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        assert res["reason"] == C.COMPOSED
        assert res["chain"] == [ids["mv"]] * 4 + [ids["B"]]
        assert res["prefix"] == C.PREFIX_REQUIRED and res["proposed"] == 1, (
            "S4 FALSIFIED: a necessary prefix was dropped -- %r" % (res,))
        assert int(res["frames"][3][0, 4]) == 7, (
            "the avatar occupies the act cell before the click seam")
        assert res["anchors"] == [None] * 4 + [(2, 4)]
        # the check itself, both ways, on the simulation seam
        order, atoms = _pool(g)
        body = [ids["mv"]] * 4
        trace = [(0, c) for c in range(5)]
        cells = [(2, 4, 9)]
        ok = C._simulate(f, atoms, body, trace, [ids["B"]], cells, None,
                         anchor=(2, 4), act=(0, 4), avatar_colour=7)
        assert ok is not None and ok[1][-1] == (2, 4)
        bad = C._simulate(f, atoms, body, trace, [ids["B"]], cells, None,
                          anchor=(2, 4), act=(0, 4), avatar_colour=5)
        assert bad is None, (
            "S4 FALSIFIED: the click seam verified with the wrong patch at "
            "the act cell")
        none = C._simulate(f, atoms, body, trace, [ids["B"]], cells, None,
                           anchor=(2, 4), act=(0, 4), avatar_colour=None)
        assert none is None, "an unknown avatar colour never passes the check"

    def test_the_final_seam_stamps_at_the_named_anchor_only(self, tmp_path):
        """_apply_at refuses a cell the matcher does not confirm; at a
        confirmed cell it writes exactly apply_effect's masked stamp."""
        g = _gamma(tmp_path, "s4c")
        bid = g.add(_atom([[3, E.DONT_CARE]], [[9, E.DONT_CARE]], "b"), "g1", 1)
        f = np.array([[3, 5, 3, 6]], dtype=int)
        atom = g.get(bid)
        assert C._anchors(f, atom) == [(0, 0), (0, 2)]
        second = C._apply_at(atom, f, (0, 2))
        assert second.tolist() == [[3, 5, 9, 6]], "stamped at (0,2); (0,3) kept"
        first = C._apply_at(atom, f, (0, 0))
        assert first.tolist() == E.apply_effect(atom, f).tolist()
        assert C._apply_at(atom, f, (0, 1)) is None, "not a match: refused"
        assert C._apply_at(atom, f, (0, 3)) is None


# ── H · handoffs ──────────────────────────────────────────────────────────────

class TestHandoffs:

    def test_is_citable_reads_the_stream_record_through_gamma(self, tmp_path):
        """THE OLD SHAPE: production holds gamma + id; gamma.get returns the
        ATOM, which cannot carry settled -> is_citable read False forever,
        silently. NOW: (id, gamma) reads the record; the atom is refused."""
        f, g, ids, want = _world(tmp_path, "h1")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        cid = res["composite"]
        assert C.is_citable(cid, gamma=g) is False
        assert C.citation_state(g, cid) == {"citable": False, "reason": "candidate"}
        assert C.citation_allowed(cid, C.ROLE_BET, gamma=g) is True
        assert C.citation_allowed(cid, C.ROLE_GROUND, gamma=g) is False
        live = np.zeros((3, 6), dtype=int)
        live[0, 4] = 7
        live[2, 4] = 9
        assert C.live_settle(g, C.drive_record(res), live)["settled"]
        assert C.is_citable(cid, gamma=g) is True, (
            "H FALSIFIED: a settled composite is not readable by id")
        assert C.citation_state(g, cid) == {"citable": True, "reason": C.S_SETTLED}
        assert C.citation_allowed(cid, C.ROLE_GROUND, gamma=g) is True
        assert C.is_citable(C.composite_record(g, cid)) is True
        atom = g.get(cid)
        assert atom["kind"] == "COMPOSITE" and "atom" not in atom
        with pytest.raises(TypeError, match=C.NOT_A_RECORD):
            C.is_citable(atom)                   # the misread, refused loudly
        with pytest.raises(TypeError, match=C.NOT_A_RECORD):
            C.citation_allowed(atom, C.ROLE_GROUND)
        assert C.citation_state(g, "cmp-ghost:99") == {
            "citable": False, "reason": C.S_NO_RECORD}
        with pytest.raises(TypeError, match=C.NOT_A_RECORD):
            C.is_citable(cid)                    # an id needs gamma

    def test_a_reach_claiming_verified_is_a_contract_breach(self, tmp_path,
                                                            monkeypatch):
        f, g, ids, want = _world(tmp_path, "h2")
        real = EN.cross_shelf_reach

        def _liar(*a, **k):
            r = real(*a, **k)
            if r is not None:
                r = dict(r)
                r["verified"] = True
            return r
        monkeypatch.setattr(C._enables, "cross_shelf_reach", _liar)
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        assert res["composite"] is None and res["reason"] == C.R_REACH_BREACH, (
            "H FALSIFIED: a reach claiming verified=True was consumed -- %r"
            % (res,))
        assert _composites(g) == []
        monkeypatch.setattr(C._enables, "cross_shelf_reach", real)
        assert C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1",
                                 1)["reason"] == C.COMPOSED

    def test_the_loop_states_the_avatar_source(self, tmp_path):
        f = np.array([[7, 3]], dtype=int)
        g = _gamma(tmp_path, "h3")
        bid = g.add(_click_atom([[3]], [[9]], "click-b", 0, -1), "g1", 1)
        exact = _ns(tmp_path, "h3_e", g, self_cell=(0, 0))
        assert cl._w2b_engage(exact, f, _cf(0.0)) is True
        res = cl._w3c_compose(exact, f, [(0, 1, 9)])
        assert res["reason"] == C.COMPOSED and res["chain"] == [bid]
        assert res["avatar"] == C.AVATAR_EXACT
        assert exact._w2b_narr[2]["avatar"] == C.AVATAR_EXACT
        fallback = _ns(tmp_path, "h3_c", g)       # centroid only
        assert cl._w2b_engage(fallback, f, _cf(0.0)) is True
        res = cl._w3c_compose(fallback, f, [(0, 1, 9)])
        assert res["avatar"] == C.AVATAR_CENTROID, (
            "H FALSIFIED: the centroid fallback is not stated")
        cl._narr_bet(fallback, 6, _cf(0.0), {})
        assert _plan_records(fallback)[-1]["avatar"] == C.AVATAR_CENTROID
        blind = _ns(tmp_path, "h3_n", g)
        blind._ego_prev_centroid = None
        assert cl._w2b_engage(blind, f, _cf(0.0)) is True
        assert cl._w3c_compose(blind, f, [(0, 1, 9)]) is None
        assert blind._w2b_narr == ("compose-none", C.R_UNREACHABLE)

    def test_the_observer_exposes_the_exact_cell_only_for_a_single_cell(self):
        from engines.egocentric.observer import EgoObserver
        from engines.egocentric.perception import Object
        obs = EgoObserver()
        one = Object(cells=frozenset({(2, 3)}), colours=frozenset({7}))
        two = Object(cells=frozenset({(2, 3), (2, 4)}), colours=frozenset({7}))
        obs.locus.pick = lambda objs: one
        obs._prev_objs = []
        info = obs.observe(np.zeros((4, 5), dtype=int), "4")
        assert info["cell"] == (2, 3) and info["centroid"] == (2.0, 3.0)
        obs.locus.pick = lambda objs: two
        info = obs.observe(np.zeros((4, 5), dtype=int), "4")
        assert info["cell"] is None and info["centroid"] == (2.0, 3.5), (
            "a multi-cell body has no one exact cell: None, stated")


# ── R4 · exact sequences through the real seams ───────────────────────────────

class TestR4ExactSequences:

    def test_reconciled_anchor_drive_then_settle(self, tmp_path):
        f, g, ids, want = _two_anchor_world(tmp_path, "r4a")
        ns = _ns(tmp_path, "r4a_n", g, verified={ids["mv"]: 2, ids["B"]: 2})
        res = _compose(ns, f, want, avatar=(0, 3))
        assert _drive(ns, f, res) == (4, None)
        drive = ns._w3d_chain["drive"]
        _land(ns, f, drive["frames"][0])
        assert _cont(ns, drive["frames"][0]) == (6, {'x': 4, 'y': 0})
        live = drive["frames"][0].copy()
        live[2, 4] = 9
        _land(ns, drive["frames"][0], live)
        cid = res["composite"]
        modes = [(r["mode"], r["gate"]) for r in _plan_records(ns)]
        assert modes == [("composed", cid), ("composite-drive", cid),
                         ("settled", cid)], "R4 FALSIFIED: %r" % (modes,)
        plans = _plan_records(ns)
        assert plans[0]["prefix"] == C.PREFIX_REQUIRED
        assert plans[0]["avatar"] == C.AVATAR_CENTROID
        recs = _records(g, cid)
        assert len(recs) == 2 and recs[-1][C.SETTLED_FIELD] is True
        assert recs[-1]["settle"] == {"steps": 2, "cells": 3, "want": 1}
        assert C.is_citable(cid, gamma=g)
        assert ns._plan_gate["g7"] == 1 and ns._w2b_sched.plan_wrong == {}
        assert int(recs[-1]["atom"]["parts"].index(ids["B"])) == 1

    def test_predicate_mode_drive_then_settle_through_the_loop_seam(
            self, tmp_path):
        f = np.array([[7, 3]], dtype=int)
        g = _gamma(tmp_path, "r4b")
        bid = g.add(_click_atom([[3]], [[9]], "click-b", 0, -1), "g1", 1)
        ns = _ns(tmp_path, "r4b_n", g, verified={bid: 2}, self_cell=(0, 0))
        assert cl._w2b_engage(ns, f, _cf(0.0)) is True
        pred = {"kind": "colour_present", "colour": 9}
        res = cl._w3c_compose(ns, f, pred)
        assert res is not None and res["chain"] == [bid] and res["pred"] == pred
        assert _drive(ns, f, res) == (6, {'x': 0, 'y': 0})
        _land(ns, f, np.array([[7, 9]], dtype=int))
        cid = res["composite"]
        modes = [(r["mode"], r["gate"]) for r in _plan_records(ns)]
        assert modes == [("composed", cid), ("settled", cid)], modes
        assert _plan_records(ns)[0]["avatar"] == C.AVATAR_EXACT
        rec = _records(g, cid)[-1]
        assert rec[C.SETTLED_FIELD] is True
        assert rec["settle"] == {"steps": 1, "cells": 1, "want": 0,
                                 "predicate": True}
        assert ns._w3d_chain is None and ns._w2b_driven is None

    def test_predicate_mode_drive_then_fail_routes_plan_wrong(self, tmp_path):
        f = np.array([[7, 3]], dtype=int)
        g = _gamma(tmp_path, "r4c")
        bid = g.add(_click_atom([[3]], [[9]], "click-b", 0, -1), "g1", 1)
        ns = _ns(tmp_path, "r4c_n", g, verified={bid: 2})
        assert cl._w2b_engage(ns, f, _cf(0.0)) is True
        res = cl._w3c_compose(ns, f, {"kind": "colour_present", "colour": 9})
        assert _drive(ns, f, res) == (6, {'x': 0, 'y': 0})
        _land(ns, f, f)                          # the click did nothing
        last = _plan_records(ns)[-1]
        assert last["mode"] == "abort" and last["gate"] == sch.ABORT_PLAN_WRONG
        assert last["component"] == bid and last["settled"] is False
        assert len(_records(g, res["composite"])) == 1
        assert not C.is_citable(res["composite"], gamma=g)

    def test_a_satisfied_predicate_at_the_loop_seam_is_narrated(self, tmp_path):
        f = np.array([[7, 9]], dtype=int)
        g = _gamma(tmp_path, "r4d")
        g.add(_click_atom([[3]], [[9]], "click-b", 0, -1), "g1", 1)
        ns = _ns(tmp_path, "r4d_n", g)
        assert cl._w2b_engage(ns, f, _cf(0.0)) is True
        assert cl._w3c_compose(ns, f, {"kind": "colour_present", "colour": 9}) is None
        assert ns._w2b_narr == ("compose-none", C.R_WANT_SATISFIED)
        cl._narr_bet(ns, 6, _cf(0.0), {})
        plan = _plan_records(ns)[-1]
        assert plan["mode"] == "compose-none" and plan["gate"] == C.R_WANT_SATISFIED
        assert ns._plan_gate["g7"] == 0 and _composites(g) == []


# ── known-negatives ───────────────────────────────────────────────────────────

class TestKnownNegatives:

    def test_a_stale_anchor_yields_no_site_and_the_chain_drops_loudly(
            self, tmp_path):
        f, g, ids, want = _world(tmp_path, "kn0")
        atom = g.get(ids["B"])
        assert cl._w3d_site(f, atom, (2, 4)) == (4, 0)
        assert cl._w3d_site(f, atom, (2, 3)) is None, "no match there: no site"
        assert cl._w3d_site(f, atom, None) is None, "no reconciled anchor: no site"
        ns = _ns(tmp_path, "kn0_n", g, verified={ids["mv"]: 2, ids["B"]: 2})
        res = _compose(ns, f, want)
        assert _drive(ns, f, res) == (4, None)
        drive = ns._w3d_chain["drive"]
        pre = f
        for i in range(4):
            _land(ns, pre, drive["frames"][i])
            pre = drive["frames"][i]
            if i < 3:
                assert _cont(ns, pre) is not None
        drive["anchors"][-1] = (2, 3)            # the anchor went stale
        assert _cont(ns, pre) is None
        assert ns._w3d_chain is None
        last = _plan_records(ns)[-1]
        assert last["mode"] == "abort" and last["gate"] == "could-not-issue"
        assert last["reason"] == "could-not-issue" and last["part"] == 4
        assert len(_records(g, res["composite"])) == 1

    def test_malformed_drive_records_never_drive(self, tmp_path):
        f, g, ids, want = _world(tmp_path, "kn1")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        assert C.drive_record(res) is not None
        no_anchors = dict(res)
        no_anchors["anchors"] = [None]
        assert C.drive_record(no_anchors) is None, "one anchor slot per part"
        no_want = dict(res)
        no_want["want_cells"] = None
        assert C.drive_record(no_want) is None
        ns = _ns(tmp_path, "kn1_n", g, verified={ids["mv"]: 2, ids["B"]: 2})
        assert cl._w2b_engage(ns, f, _cf(0.0)) is True
        assert cl._w3d_drive(ns, f, no_want) is None
        assert ns._plan_gate["shadow"] == 1 and ns._plan_gate["g7"] == 0
        assert ns._w2b_narr[2]["reason"] == "drive-record-malformed"

    def test_an_avatar_off_frame_is_stated_not_guessed(self, tmp_path):
        f, g, ids, want = _world(tmp_path, "kn2")
        res = C.compose_attempt(want, f, g, (9, 9), DELTAS4, set(), "g1", 1)
        assert res["composite"] is None and res["reason"] == C.R_UNREACHABLE
        assert res["notes"] == {C.R_NO_AVATAR: 1}
        res = C.compose_attempt(want, f, g, None, DELTAS4, set(), "g1", 1)
        assert res["reason"] == C.R_UNREACHABLE and res["notes"] == {C.R_NO_AVATAR: 1}

    def test_single_prior_palette_credit_matches_the_cell_count(self, tmp_path):
        """Repair 6: the palette credits the ONE establishing prior only --
        where no prior establishes a later step's cells, its residue colours
        are demanded of the frame even if some prior could write them."""
        g = _gamma(tmp_path, "kn3")
        a = g.add(_atom([[3]], [[4]], "a34"), "g1", 1)           # writes 4
        b = g.add(_atom([[4, 4]], [[5, 5]], "b45"), "g1", 1)     # needs 2x 4
        csig = A.composite_signature([a, b], g.get)
        assert csig["residue"] == 2, "a 1x1 after-patch contains no 1x2 context"
        assert csig["pre"]["pal"] == [3, 4], (
            "repair 6 FALSIFIED: the palette credited a prior that established "
            "no cell (union credit) -- %r" % (csig["pre"]["pal"],))
        c = g.add(_atom([[4]], [[5]], "c45"), "g1", 1)
        csig = A.composite_signature([a, c], g.get)
        assert csig["residue"] == 0 and csig["pre"]["pal"] == [3], (
            "the establishing prior IS credited (stage-1 F2 unchanged)")


# ── structural ────────────────────────────────────────────────────────────────

def _fn(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError("%s not found" % name)


def _calls(node, name):
    return [n for n in ast.walk(node)
            if isinstance(n, ast.Call) and (
                (isinstance(n.func, ast.Name) and n.func.id == name)
                or (isinstance(n.func, ast.Attribute) and n.func.attr == name))]


def _body_source(src, fn):
    """The function's CODE (every statement after the docstring)."""
    stmts = fn.body[1:] if ast.get_docstring(fn) is not None else fn.body
    return "\n".join(ast.get_source_segment(src, s) or "" for s in stmts)


class TestStructural:

    def test_no_patch_centre_synthesis_and_no_anchors0_at_the_drive(self):
        src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                   errors="replace").read()
        tree = ast.parse(src)
        site = ast.get_source_segment(src, _fn(tree, "_w3d_site")) or ""
        assert "// 2" not in site and "anch[0]" not in site, (
            "STRUCTURAL FALSIFIED: _w3d_site still synthesises a site")
        for name in ("_w3d_drive", "_w3d_continue", "_w3d_step"):
            seg = ast.get_source_segment(src, _fn(tree, name)) or ""
            assert "anch[0]" not in seg and "anchors[0]" not in seg
        drive = ast.get_source_segment(src, _fn(tree, "_w3d_drive")) or ""
        assert "NO_ACT_OFFSET" in drive and "_w3d_offsetless" in drive
        for name in ("_w3d_drive", "_w3d_continue", "_w3d_settle", "_w3d_abort"):
            assert not _calls(_fn(tree, name), "append"), (
                "%s appends -- stage 4's one-writer discipline" % name)

    def test_the_attempt_checks_the_want_first_and_reads_the_contract(self):
        src = open(os.path.join(REPO, "engines", "egocentric", "composer.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        seg = ast.get_source_segment(src, _fn(tree, "_attempt")) or ""
        assert seg.index("_satisfied(") < seg.index("gamma.fabric.query"), (
            "the WANT must be checked BEFORE the pool is read")
        assert 'reach.get("verified") is not False' in seg
        assert "R_REACH_BREACH" in seg
        adv = ast.get_source_segment(src, _fn(tree, "_advances")) or ""
        assert "not bool(satisfies(pred, frame))" in adv, (
            "predicate advance must compare the baseline")
        sim = ast.get_source_segment(src, _fn(tree, "_simulate")) or ""
        assert "_apply_at(" in sim and "apply_effect(atoms.get(aid)" not in sim, (
            "the final seam must stamp at the named anchor")
        assert _calls(_fn(tree, "settle_verdict"), "satisfies"), (
            "the live settle must re-verify the predicate")
        assert _calls(_fn(tree, "is_citable"), "_as_record")
        assert _calls(_fn(tree, "citation_allowed"), "_as_record")

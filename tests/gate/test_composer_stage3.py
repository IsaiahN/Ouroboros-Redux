"""COMPOSER STAGE 3 -- THE COMPOSE LOOP (PROPOSAL_COMPOSER_DESIGN.md par.3/6.3).

The build under test (engines/egocentric/composer.py + the cognitive_loop
seam _w3c_compose/_w3c_want_cells):
  compose_attempt = the design's loop, run EXACTLY where the planner already
  engages: WANT -> Gamma candidates by psig-written intersecting the WANT's
  target colours (stored signatures) -> matching anchors via the existing
  vectorised matcher -> BODY prefix via enables.cross_shelf_reach where the
  atom's act cell is not the avatar -> enabler prefix via
  enables.enables_edges where the candidate has no anchor -> chains
  simulated seam by seam (apply_effect, with the per-step ENDPOINT CHECK on
  movement) -> verified chains ranked by the DERIVED price
  (applicability.composite_signature) -> cheapest -> Gamma.compose() ->
  COMPOSITE minted as CANDIDATE (stage 4 owns citability). The two stage-2
  instruments flip SEVERED -> LIVE with this consumer.

The falsifiers, as gated here:
  F1  end-to-end two-shelf: WANT satisfied by atom B whose act cell is away
      from the avatar; the BODY chain is found, simulated, and the composite
      mints with the parts in exact chain order ([body..., B]).
  F2  scheduler-gated: structurally, every compose call in cycle() is
      nested under the W2b engage gate (AST containment -- closed gates
      cannot reach it); behaviorally, a closed gate narrates the skip and
      leaves no composite in the stream.
  F3  fallback ordering: every compose call sits under a `_plan is None` /
      `_ap is None` guard (a found plan means NO compose attempt); invoked,
      the seam narrates mode "composed" with the composite id at the PLAN
      point, or "compose-none" with the fixed reason.
  F4  simulation honesty (the stated scope's boundary is GATED): a movement
      chain whose BODY action has no minted TRANSLATE atom is
      proposed-unverified and NEVER minted; a chain the world blocks (a wall
      the mask does not know) fails the seam/endpoint check and is NEVER
      minted. Nothing unverifiable reaches Gamma.compose.
  F5  price-ranked: two viable chains -> the CHEAPER mints (insertion order
      cannot save the dear one).
  R4  exact outcomes on constructed worlds: avatar-already-at-act-cell
      composes [B] alone; a no-anchor candidate composes [enabler, B]
      through the within-Gamma edge, exact parts both times.
  KNOWN-NEGATIVES: empty WANT -> "empty-want"; a WANT nobody writes ->
      "no-candidates"; unreachable (fatal-masked) anchors -> "unreachable";
      a colour-less predicate -> "want-underivable". None ever mint.

Seeded with a FIXED CONSTANT (the build date), never a clock.
"""
from __future__ import annotations

import ast
import os
import sys
from types import SimpleNamespace

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import cognitive_loop as cl  # noqa: E402
from engines.egocentric import composer as C  # noqa: E402
from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric import enables as EN  # noqa: E402
from engines.egocentric import narration as na  # noqa: E402
from engines.egocentric import scheduler as sch  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402

SEED = 20260821  # fixed constant (the build date) -- deterministic forever

# constructed deltas, (dr, dc): 1 up, 2 down, 3 left, 4 right
DELTAS4 = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


# ── constructions ─────────────────────────────────────────────────────────────

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
    """An EFFECT atom carrying a stored act_offset (the mint's stamp)."""
    a = _atom(ctx, out, key)
    a[EN.ACT_OFFSET_FIELD] = {"v": EN.ACT_OFFSET_VERSION,
                              "dr": int(dr), "dc": int(dc)}
    return a


def _mv_right(key="mv-right"):
    """A minted BODY-shelf TRANSLATE atom: action 4 moves the 7-avatar one
    column right ((dx, dy) = (0, 1) verbatim per effects' TRANSLATE)."""
    return _atom([[7, 0]], [[0, 7]], key, action=4, ttype="TRANSLATE",
                 params={"dx": 0, "dy": 1, "fill": 0})


def _two_shelf_world(tmp_path, name, with_body=True, obstacle=None):
    """Avatar 7 at (0,0); button 3 at (2,4); atom B (writes 9) anchored on
    the button with act cell (0,4) = anchor + (-2, 0). WANT = 9 at (2,4)."""
    f = np.zeros((3, 6), dtype=int)
    f[0, 0] = 7
    f[2, 4] = 3
    if obstacle is not None:
        f[obstacle] = 5
    g = _gamma(tmp_path, name)
    ids = {}
    if with_body:
        ids["mv"] = g.add(_mv_right(), "g1", 1)
    ids["B"] = g.add(_click_atom([[3]], [[9]], "click-b", -2, 0), "g1", 1)
    return f, g, ids, [(2, 4, 9)]


def _composites(g):
    return [r for r in g.fabric.query("collective", g.TOPIC)
            if (r.get("atom") or {}).get("kind") == "COMPOSITE"]


# ── F1 · the two-shelf case composes end-to-end ───────────────────────────────

class TestF1TwoShelfEndToEnd:

    def test_body_chain_found_and_composite_minted_in_order(self, tmp_path):
        f, g, ids, want = _two_shelf_world(tmp_path, "f1")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        assert res["reason"] == C.COMPOSED, (
            "F1 FALSIFIED: the constructed two-shelf case did not compose -- "
            "%r" % (res,))
        assert res["composite"], "the composite id must be returned"
        assert res["chain"] == [ids["mv"]] * 4 + [ids["B"]], (
            "F1 FALSIFIED: parts must be the BODY prefix THEN the Gamma atom, "
            "in execution order; got %r" % (res["chain"],))
        assert res["actions"] == [4, 4, 4, 4], (
            "the BODY prefix is the reach's chain (4 right-steps)")
        assert res["price"] is not None and res["verified"] >= 1
        comps = _composites(g)
        assert len(comps) == 1 and comps[-1]["id"] == res["composite"]
        assert comps[-1]["atom"]["parts"] == res["chain"], (
            "the stored composite must carry the same parts order")

    def test_the_composite_is_a_candidate_nothing_marks_it_citable(
            self, tmp_path):
        """Stage 4 owns citability: the minted record carries NO settlement
        or citability marking of any kind -- proposable-not-standable by
        construction (design par.1.4 / par.5 no-self-settlement)."""
        f, g, ids, want = _two_shelf_world(tmp_path, "f1c")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        assert res["reason"] == C.COMPOSED, "construction: must compose"
        rec = _composites(g)[-1]
        for field in ("settled", "citable", "verified"):
            assert field not in rec and field not in rec["atom"], (
                "F1 FALSIFIED: the composite carries %r -- simulation must "
                "never count as the settle" % field)


# ── F2 · scheduler-gated: closed gates cannot reach the compose ───────────────

def _cycle_ast():
    src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
               errors="replace").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "CognitiveLoop":
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name == "cycle":
                    return sub
    raise AssertionError("CognitiveLoop.cycle not found")


def _parents(root):
    par = {}
    for node in ast.walk(root):
        for child in ast.iter_child_nodes(node):
            par[child] = node
    return par


def _compose_calls(fn):
    return [n for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "_w3c_compose"]


def _ancestor_ifs(node, par):
    out = []
    while node in par:
        node = par[node]
        if isinstance(node, ast.If):
            out.append(node)
    return out


def _test_calls(node, name):
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
               and n.func.id == name for n in ast.walk(node.test))


def _is_none_guard(node, names):
    t = node.test
    return (isinstance(t, ast.Compare) and isinstance(t.left, ast.Name)
            and t.left.id in names and len(t.ops) == 1
            and isinstance(t.ops[0], ast.Is)
            and isinstance(t.comparators[0], ast.Constant)
            and t.comparators[0].value is None)


def _loop_ns(tmp_path, name="f"):
    """The scheduling gate's constructed loop namespace + a real Gamma."""
    return SimpleNamespace(
        _ego_fabric=KnowledgeFabric(str(tmp_path / name), agent_id="a",
                                    kin_key="v4"),
        _game_id="g1", _actions_taken=0, _ego_agent_id="a", _ego_level=0,
        _w2b_sched=None, _w2b_narr=None, _w2b_driven=None, _w2b_key=None,
        _w4c_counters={"mint_passed": 0}, _narr_import_n=0,
        _narration=None, _narr_slots=None, _atom_verified={},
        _residual_router=None, _plan_gate={"cycles": 1},
        _narr_settle=None, _narr_mint=None, _prev_frame=None,
        _ego_seeded={}, _ego_seeded_clicks={},
        _gamma=_gamma(tmp_path, name + "_g"),
        _ego_prev_centroid=None, _ego_frontier_book=None)


def _cf(conf=0.0, speed="explore"):
    return SimpleNamespace(action_confidence=float(conf), rung_name="",
                           action_speed=str(speed))


def _plan_records(ns):
    return [r for r in ns._ego_fabric.query("personal", na.TOPIC)
            if r["point"] == na.PLAN]


class TestF2SchedulerGated:

    def test_structural_every_compose_call_sits_inside_the_engage_gate(self):
        fn = _cycle_ast()
        par = _parents(fn)
        calls = _compose_calls(fn)
        assert len(calls) == 2, (
            "exactly the two plan seams (reference + abduced) may reach the "
            "compose fallback; found %d call(s)" % len(calls))
        for call in calls:
            ifs = _ancestor_ifs(call, par)
            assert any(_test_calls(i, "_w2b_engage") for i in ifs), (
                "F2 FALSIFIED: a compose call is reachable OUTSIDE the W2b "
                "engage gate -- new engagement, the leak the scheduler "
                "exists to stop")

    def test_behavioral_a_closed_gate_narrates_the_skip_and_composes_nothing(
            self, tmp_path):
        ns = _loop_ns(tmp_path)
        f = np.zeros((4, 4), dtype=int)
        assert cl._w2b_engage(ns, f, _cf(0.0)) is True, "first engages"
        assert cl._w2b_engage(ns, f, _cf(0.0)) is False, "gate B closes"
        assert ns._w2b_narr == ("skipped", sch.SKIP_UNCHANGED)
        cl._narr_bet(ns, 6, _cf(0.0), {})
        plans = _plan_records(ns)
        assert len(plans) == 1 and plans[0]["mode"] == "skipped", (
            "a closed gate must narrate the skip, never a compose outcome")
        assert _composites(ns._gamma) == [], (
            "F2 FALSIFIED: a composite appeared with the gates closed")


# ── F3 · the fallback ordering: plan found -> NO attempt; None -> attempt ─────

class TestF3FallbackOrdering:

    def test_structural_every_compose_call_is_guarded_by_planner_none(self):
        fn = _cycle_ast()
        par = _parents(fn)
        for call in _compose_calls(fn):
            ifs = _ancestor_ifs(call, par)
            assert any(_is_none_guard(i, ("_plan", "_ap")) for i in ifs), (
                "F3 FALSIFIED: a compose call is not guarded by the "
                "planner's None -- composing beside a found plan is a new "
                "engagement, not a fallback")

    def test_behavioral_the_seam_narrates_composed_with_the_id(self, tmp_path):
        ns = _loop_ns(tmp_path)
        f = np.array([[3, 0], [0, 1]], dtype=int)
        bid = ns._gamma.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)
        assert cl._w2b_engage(ns, f, _cf(0.0)) is True, "the gate opens"
        cl._w3c_compose(ns, f, [(0, 0, 9)])
        assert ns._w2b_narr is not None and ns._w2b_narr[0] == "composed", (
            "F3 FALSIFIED: the compose outcome was not staged for the PLAN "
            "point; got %r" % (ns._w2b_narr,))
        cid = ns._w2b_narr[1]
        comps = _composites(ns._gamma)
        assert len(comps) == 1 and comps[0]["id"] == cid
        assert comps[0]["atom"]["parts"] == [bid]
        cl._narr_bet(ns, 6, _cf(0.0), {})
        plans = _plan_records(ns)
        assert len(plans) == 1, "one PLAN record per cycle"
        assert plans[0]["mode"] == "composed" and plans[0]["gate"] == cid, (
            "the PLAN record must carry mode=composed + the composite id")

    def test_behavioral_the_none_outcome_narrates_its_reason(self, tmp_path):
        ns = _loop_ns(tmp_path)                 # empty Gamma: no candidates
        f = np.array([[3, 0]], dtype=int)
        cl._w3c_compose(ns, f, [(0, 0, 9)])
        assert ns._w2b_narr == ("compose-none", C.R_NO_CANDIDATES), (
            "the None outcome must narrate the attempt's fixed reason; got "
            "%r" % (ns._w2b_narr,))
        assert _composites(ns._gamma) == []


# ── F4 · simulation honesty: the scope's boundary is gated ────────────────────

class TestF4SimulationHonesty:

    def test_a_body_action_with_no_minted_atom_never_mints(self, tmp_path):
        """The stated scope: a movement chain simulates ONLY through minted
        TRANSLATE atoms. Without one there is nothing to apply AND nothing
        to compose -- proposed-unverified, never minted."""
        f, g, ids, want = _two_shelf_world(tmp_path, "f4a", with_body=False)
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        assert res["composite"] is None and res["reason"] == C.R_UNVERIFIED, (
            "F4 FALSIFIED: an unsimulable movement chain produced %r" % (res,))
        assert res["proposed"] == 1 and res["verified"] == 0, (
            "the algebra PROPOSES (the chain is counted) and the simulation "
            "boundary gates it (never verified)")
        assert _composites(g) == [], (
            "F4 FALSIFIED: an unverifiable chain reached Gamma.compose")

    def test_a_wall_the_mask_does_not_know_fails_the_seam_never_mints(
            self, tmp_path):
        """Seat 4's amendment run end-to-end: the delta algebra proposes the
        straight chain (the wall is not in the fatal mask); the simulation's
        seam/endpoint check rejects it; nothing mints."""
        f, g, ids, want = _two_shelf_world(tmp_path, "f4b", obstacle=(0, 2))
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        assert res["proposed"] >= 1, (
            "construction: the chain must be PROPOSED -- the wall is unknown "
            "to the mask (the agent has not died on it)")
        assert res["composite"] is None and res["reason"] == C.R_UNVERIFIED, (
            "F4 FALSIFIED: the simulation did not reject the blocked chain "
            "-- %r" % (res,))
        assert _composites(g) == []

    def test_the_wrong_patch_moving_fails_the_endpoint_check(self, tmp_path):
        """A decoy avatar earlier in row-major order: apply_effect moves IT,
        the endpoint check sees the predicted cells untouched, and the chain
        degrades to proposed-unverified -- movement simulation is exact or
        it is nothing."""
        f = np.zeros((3, 6), dtype=int)
        f[0, 0] = 7                             # the decoy (first row-major)
        f[1, 0] = 7                             # the avatar the reach plans for
        f[2, 4] = 3
        g = _gamma(tmp_path, "f4c")
        g.add(_mv_right(), "g1", 1)
        g.add(_click_atom([[3]], [[9]], "click-b", -1, 0), "g1", 1)
        # avatar (1,0); act cell (1,4): reach proposes right-steps along row 1,
        # but apply moves the (0,0) decoy -- endpoint cells (1,*) untouched.
        res = C.compose_attempt([(2, 4, 9)], f, g, (1, 0), DELTAS4, set(),
                                "g1", 1)
        assert res["composite"] is None and res["reason"] == C.R_UNVERIFIED, (
            "F4 FALSIFIED: the wrong patch moved and the chain still "
            "verified -- %r" % (res,))
        assert _composites(g) == []


# ── F5 · price-ranked: the cheaper of two viable chains mints ─────────────────

class TestF5PriceRanked:

    def test_the_cheaper_verified_chain_mints(self, tmp_path):
        f = np.array([[3, 0], [0, 4]], dtype=int)
        g = _gamma(tmp_path, "f5")
        # the DEAR chain first (insertion order must not decide): a 2x2
        # context retaining 3 unchanged cells -> price 3 + 0 + 1 = 4
        dear = g.add(_atom([[3, 0], [0, 4]], [[9, 0], [0, 4]], "eff-dear"),
                     "g1", 1)
        # the CHEAP chain: 1x1 fully-changed context -> price 0 + 0 + 1 = 1
        cheap = g.add(_atom([[3]], [[9]], "eff-cheap"), "g1", 1)
        res = C.compose_attempt([(0, 0, 9)], f, g, None, {}, set(), "g1", 1)
        assert res["reason"] == C.COMPOSED and res["verified"] == 2, (
            "construction: BOTH chains must verify; got %r" % (res,))
        assert res["chain"] == [cheap] and res["price"] == 1, (
            "F5 FALSIFIED: the derived price did not pick the cheap chain "
            "(got %r price=%r; dear=%r)" % (res["chain"], res["price"], dear))
        assert _composites(g)[-1]["atom"]["parts"] == [cheap]


# ── R4 · exact outcomes on constructed worlds ─────────────────────────────────

class TestR4ExactOutcomes:

    def test_avatar_already_at_the_act_cell_composes_the_atom_alone(
            self, tmp_path):
        f = np.array([[7, 3]], dtype=int)
        g = _gamma(tmp_path, "r4a")
        bid = g.add(_click_atom([[3]], [[9]], "click-b", 0, -1), "g1", 1)
        res = C.compose_attempt([(0, 1, 9)], f, g, (0, 0), DELTAS4, set(),
                                "g1", 1)
        assert res["reason"] == C.COMPOSED, "must compose without movement"
        assert res["chain"] == [bid] and res["actions"] == [], (
            "R4 FALSIFIED: avatar at the act cell needs NO body prefix; got "
            "%r" % (res,))

    def test_a_no_anchor_candidate_composes_through_the_enables_edge(
            self, tmp_path):
        """The within-Gamma instrument consumed: B (writes the WANT) has no
        anchor in the frame; A writes B's missing colour; the edge A -> B
        supplies the chain [A, B], simulated and minted exactly."""
        f = np.array([[1]], dtype=int)
        g = _gamma(tmp_path, "r4b")
        aid = g.add(_atom([[1]], [[5]], "eff-a"), "g1", 1)   # writes 5
        bid = g.add(_atom([[5]], [[9]], "eff-b"), "g1", 1)   # needs 5, writes 9
        res = C.compose_attempt([(0, 0, 9)], f, g, None, {}, set(), "g1", 1)
        assert res["reason"] == C.COMPOSED, (
            "R4 FALSIFIED: the enabler chain did not compose -- %r" % (res,))
        assert res["chain"] == [aid, bid], (
            "R4 FALSIFIED: exact parts [enabler, candidate] expected; got "
            "%r" % (res["chain"],))


# ── known-negatives: every refusal is a stated reason, never a mint ───────────

class TestKnownNegatives:

    def test_empty_want_is_stated(self, tmp_path):
        g = _gamma(tmp_path, "kn0")
        g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)
        f = np.array([[3]], dtype=int)
        res = C.compose_attempt([], f, g, None, {}, set(), "g1", 1)
        assert res["composite"] is None and res["reason"] == C.R_EMPTY_WANT
        assert C.compose_attempt(None, f, g, None, {}, set(), "g1",
                                 1)["reason"] == C.R_EMPTY_WANT

    def test_a_want_nobody_writes_is_no_candidates(self, tmp_path):
        g = _gamma(tmp_path, "kn1")
        g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)         # writes 9, not 8
        res = C.compose_attempt([(0, 0, 8)], np.array([[3]], dtype=int), g,
                                None, {}, set(), "g1", 1)
        assert res["composite"] is None and res["reason"] == C.R_NO_CANDIDATES
        assert _composites(g) == []

    def test_fatal_masked_anchors_are_unreachable(self, tmp_path):
        """The act cell is fatal-banked: the reach refuses (the mask is
        honest, stage-2 F2) and the attempt states 'unreachable'."""
        f, g, ids, want = _two_shelf_world(tmp_path, "kn2")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, {(0, 4)},
                                "g1", 1)
        assert res["composite"] is None and res["reason"] == C.R_UNREACHABLE, (
            "a masked-out act cell must be UNREACHABLE, never guessed; got "
            "%r" % (res,))
        assert res["candidates"] == 1 and res["proposed"] == 0
        assert _composites(g) == []

    def test_a_colourless_predicate_is_want_underivable(self, tmp_path):
        g = _gamma(tmp_path, "kn3")
        g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)
        res = C.compose_attempt({"kind": "region_uniform", "region": "full"},
                                np.array([[3]], dtype=int), g, None, {},
                                set(), "g1", 1)
        assert res["composite"] is None
        assert res["reason"] == C.R_WANT_UNDERIVABLE, (
            "the written-colours edge cannot see uniformity -- stated, "
            "never guessed; got %r" % (res,))

    def test_a_colour_naming_predicate_composes(self, tmp_path):
        """The abduced-WANT path end-to-end: colour_present names the target
        and the planner's own stopping test decides the simulation."""
        g = _gamma(tmp_path, "kn4")
        bid = g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)
        res = C.compose_attempt({"kind": "colour_present", "colour": 9},
                                np.array([[3, 0]], dtype=int), g, None, {},
                                set(), "g1", 1)
        assert res["reason"] == C.COMPOSED and res["chain"] == [bid]

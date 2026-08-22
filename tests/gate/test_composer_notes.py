"""D-12's INSTRUMENT (PORT_LOG 2026-08-21): the two notes compose-none lacked.

sp80 live narrated `compose-none reason=unreachable candidates=17 proposed=0
notes={}` on every cycle. notes={} ruled out the two NOTED non-proposal
branches (no-act-offset, no-avatar), so all 17 candidates fell through the
two UNNOTED ones -- and the label "unreachable" conflates NO-ANCHOR (the
candidate matches nowhere on the plan-time frame, and no enabler anchors
either) with NO-PATH (anchored, offset-bearing, avatar known, but
enables.cross_shelf_reach found no chain). Two `_note` tokens now separate
the causes; the reason label is UNCHANGED (the notes name the branch, the
label stays the attempt's verdict).

Gated here:
  NO-ANCHOR   constructed: candidates > 0, no candidate anchor, no enabler
              anchor -> notes == {"no-anchor": n}, reason "unreachable";
              n counts per candidate, and an enabler that EXISTS but does not
              anchor still counts (the note means "nothing anchored").
  NO-REACH    constructed: anchor present, act_offset present, avatar
              present, cross_shelf_reach returning None (monkeypatched) ->
              notes == {"no-reach": n}, reason "unreachable"; and the real,
              unpatched reach on a fatal-masked act cell (stage 3's
              known-negative) notes the same token.
  KNOWN-NEGATIVES: the already-noted branches are untouched -- a no-avatar
              case notes ONLY no-avatar; an anchored enabler chain notes
              NOTHING (a proposal is not a non-proposal); a composed attempt
              carries notes == {}.
  TOKENS      the two constants sit in composer.__all__ with their fixed
              string values, and each is emitted from exactly one site.

Seeded with a FIXED CONSTANT (the build date), never a clock.
"""
from __future__ import annotations

import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import composer as C  # noqa: E402
from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric import enables as EN  # noqa: E402
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
    return _atom([[7, 0]], [[0, 7]], key, action=4, ttype="TRANSLATE",
                 params={"dx": 0, "dy": 1, "fill": 0})


def _two_shelf_world(tmp_path, name, obstacle=None):
    """Avatar 7 at (0,0); button 3 at (2,4); atom B (writes 9) anchored on
    the button with act cell (0,4) = anchor + (-2, 0). WANT = 9 at (2,4)."""
    f = np.zeros((3, 6), dtype=int)
    f[0, 0] = 7
    f[2, 4] = 3
    if obstacle is not None:
        f[obstacle] = 5
    g = _gamma(tmp_path, name)
    ids = {"mv": g.add(_mv_right(), "g1", 1),
           "B": g.add(_click_atom([[3]], [[9]], "click-b", -2, 0), "g1", 1)}
    return f, g, ids, [(2, 4, 9)]


def _composites(g):
    return [r for r in g.fabric.query("collective", g.TOPIC)
            if (r.get("atom") or {}).get("kind") == "COMPOSITE"]


# ── the tokens ────────────────────────────────────────────────────────────────

class TestTokens:

    def test_fixed_values_and_exported(self):
        assert C.NO_ANCHOR == "no-anchor" and C.NO_REACH == "no-reach"
        assert "NO_ANCHOR" in C.__all__ and "NO_REACH" in C.__all__
        # distinct from every other fixed token in the module
        others = {C.R_UNREACHABLE, C.R_NO_AVATAR, C.NO_ACT_OFFSET,
                  C.R_NO_CANDIDATES, C.R_UNVERIFIED}
        assert not ({C.NO_ANCHOR, C.NO_REACH} & others)

    def test_each_token_has_exactly_one_note_site(self):
        src = open(os.path.join(REPO, "engines", "egocentric", "composer.py"),
                   encoding="utf-8").read()
        assert src.count("_note(NO_ANCHOR)") == 1
        assert src.count("_note(NO_REACH)") == 1


# ── NO-ANCHOR ─────────────────────────────────────────────────────────────────

class TestNoAnchor:

    def test_no_candidate_anchor_no_enabler_is_noted(self, tmp_path):
        g = _gamma(tmp_path, "na0")
        g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)      # writes 9; needs a 3
        f = np.zeros((2, 2), dtype=int)                    # no 3 anywhere
        res = C.compose_attempt([(0, 0, 9)], f, g, None, {}, set(), "g1", 1)
        assert res["composite"] is None
        assert res["reason"] == C.R_UNREACHABLE, (
            "the LABEL must not move -- the notes separate the causes; got %r"
            % (res,))
        assert res["candidates"] == 1 and res["proposed"] == 0
        assert res["notes"] == {C.NO_ANCHOR: 1}, (
            "D-12: a candidate that anchors nowhere (and has no enabler) must "
            "say so; got notes=%r" % (res["notes"],))
        assert _composites(g) == []

    def test_n_counts_per_candidate(self, tmp_path):
        g = _gamma(tmp_path, "na1")
        g.add(_atom([[3]], [[9]], "eff-b1"), "g1", 1)
        g.add(_atom([[4]], [[9]], "eff-b2"), "g1", 1)
        g.add(_atom([[6, 6]], [[8, 9]], "eff-b3"), "g1", 1)
        f = np.zeros((2, 2), dtype=int)
        res = C.compose_attempt([(0, 0, 9)], f, g, None, {}, set(), "g1", 1)
        assert res["candidates"] == 3 and res["proposed"] == 0
        assert res["reason"] == C.R_UNREACHABLE
        assert res["notes"] == {C.NO_ANCHOR: 3}

    def test_an_enabler_that_exists_but_does_not_anchor_still_notes(self, tmp_path):
        """The within-Gamma edge A -> B exists (A writes the 3 B needs and the
        frame lacks it), but A itself anchors nowhere: nothing is proposed,
        and that is a NO-ANCHOR non-proposal, stated."""
        g = _gamma(tmp_path, "na2")
        g.add(_atom([[5]], [[3]], "eff-a"), "g1", 1)      # writes 3; needs a 5
        g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)      # writes 9; needs a 3
        f = np.zeros((2, 2), dtype=int)                    # neither 5 nor 3
        res = C.compose_attempt([(0, 0, 9)], f, g, None, {}, set(), "g1", 1)
        assert res["candidates"] == 1 and res["proposed"] == 0
        assert res["reason"] == C.R_UNREACHABLE
        assert res["notes"] == {C.NO_ANCHOR: 1}

    def test_an_anchored_enabler_chain_is_a_proposal_not_a_note(self, tmp_path):
        """KNOWN-NEGATIVE: where the enabler anchors, [A, B] is proposed and
        NO note is written -- a proposal is never a non-proposal."""
        g = _gamma(tmp_path, "na3")
        g.add(_atom([[5]], [[3]], "eff-a"), "g1", 1)
        g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)
        f = np.array([[5, 0]], dtype=int)                  # A anchors at (0,0)
        res = C.compose_attempt([(0, 0, 9)], f, g, None, {}, set(), "g1", 1)
        assert res["proposed"] >= 1
        assert C.NO_ANCHOR not in res["notes"] and C.NO_REACH not in res["notes"]


# ── NO-REACH ──────────────────────────────────────────────────────────────────

class TestNoReach:

    def test_reach_none_is_noted(self, tmp_path, monkeypatch):
        f, g, ids, want = _two_shelf_world(tmp_path, "nr0")
        calls = []

        def _no_reach(*args, **kwargs):
            calls.append(1)
            return None
        monkeypatch.setattr(EN, "cross_shelf_reach", _no_reach)
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        assert calls, "the construction must actually reach the reach call"
        assert res["composite"] is None
        assert res["reason"] == C.R_UNREACHABLE, (
            "the LABEL must not move; got %r" % (res,))
        assert res["candidates"] == 1 and res["proposed"] == 0
        assert res["notes"] == {C.NO_REACH: 1}, (
            "D-12: anchored + offset + avatar, no path -> no-reach; got "
            "notes=%r" % (res["notes"],))
        assert _composites(g) == []

    def test_n_counts_per_candidate(self, tmp_path, monkeypatch):
        f, g, ids, want = _two_shelf_world(tmp_path, "nr1")
        f[2, 1] = 3                                        # a second button
        g.add(_click_atom([[3]], [[9]], "click-b2", -2, 0), "g1", 1)
        monkeypatch.setattr(EN, "cross_shelf_reach", lambda *a, **k: None)
        res = C.compose_attempt([(2, 4, 9), (2, 1, 9)], f, g, (0, 0), DELTAS4,
                                set(), "g1", 1)
        assert res["candidates"] == 2 and res["proposed"] == 0
        assert res["reason"] == C.R_UNREACHABLE
        assert res["notes"] == {C.NO_REACH: 2}

    def test_the_real_reach_on_a_fatal_masked_act_cell_notes_no_reach(self, tmp_path):
        """Stage 3's known-negative (unchanged label), now with its cause
        named: the act cell (0,4) is fatal-banked, the UNPATCHED reach
        returns None, and the attempt notes no-reach."""
        f, g, ids, want = _two_shelf_world(tmp_path, "nr2")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, {(0, 4)}, "g1", 1)
        assert res["reason"] == C.R_UNREACHABLE and res["proposed"] == 0
        assert res["notes"] == {C.NO_REACH: 1}
        assert _composites(g) == []


# ── the already-noted branches and the composed path are untouched ───────────

class TestKnownNegatives:

    def test_no_avatar_notes_only_no_avatar(self, tmp_path):
        f, g, ids, want = _two_shelf_world(tmp_path, "kn0")
        res = C.compose_attempt(want, f, g, None, DELTAS4, set(), "g1", 1)
        assert res["reason"] == C.R_UNREACHABLE
        assert res["notes"] == {C.R_NO_AVATAR: 1}

    def test_a_composed_attempt_carries_no_notes(self, tmp_path):
        f, g, ids, want = _two_shelf_world(tmp_path, "kn1")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        assert res["reason"] == C.COMPOSED and res["composite"]
        assert res["notes"] == {}

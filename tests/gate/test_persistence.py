"""PERSISTENCE MONITOR GATE (PREREG_PERSISTENCE_MONITOR.md, Seat 3 APPROVED
2026-08-21): the achievement gap -- persisting in what isn't working is a TREND
no single-event bin can express; a counter over narration, not a fifth bin.

Under test, the prereg's falsifiers by name:
  F1 · EXACTLY k      -- identical (rho, sigma) for 2k steps fires ONE PERSISTENCE
                         record at step k: none before, none after within the run.
  F2 · RESET          -- sigma changed at step k-1 (rung / bet shape / plan gate /
                         plan mode / bet bin, EACH separately) never fires; the
                         resumed identity counts from 1.
  F3 · NON-REPEATING  -- alternating bins or rungs never fires at any k.
  F4 · CONSUMER ONLY  -- the input is the record sequence: replay over the JSONL
                         equals the online emission byte for byte; the ALLOWLIST
                         entry is gone and the R3 scanner sees the reader.
  F5 · NO PRICE READS -- the price modules carry no reference to the channel or
                         the token (AST, exact names -- no name-alike); persist
                         moves explore_boost and the stuck measure and NOTHING
                         else, by identity of the sinks.
  F6 · THE WIRE CHECK -- a constructed run at k flips an explore choice at the
                         loop's OWN site (_act's rotation window) wired vs unwired.
  R4                  -- TRANSFERRED at j < k resets; NOVEL never starts a run; a
                         [REPLAY] step resets (bin None).
  KNOWN-NEGATIVE      -- k undefined: counts, never fires, readout `unarmed`.
  Plus: the level reset and the k derivation (OWN median, [COL] fallback,
  recomputed at a crossing, FROZEN within a level); records without `level`
  cannot reset on level and the readout says so; the hot path reads no stream;
  the record is deterministic.
"""
from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import os
import sys
from types import SimpleNamespace

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import cognitive_loop as cl  # noqa: E402
from engines.egocentric import affect as af  # noqa: E402
from engines.egocentric import goal as go  # noqa: E402
from engines.egocentric import narration as na  # noqa: E402
from engines.egocentric import persistence as pm  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402

GAME = "g1"
BM, BR = na.BROKEN_MECHANISM, na.BROKEN_REBINDING


def _r3():
    """The R3 consumer gate's scanner, loaded by path (its inventory is the
    authority on who reads what)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "test_consumers.py")
    spec = importlib.util.spec_from_file_location("_r3_consumers_gate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fab(tmp_path, name="f"):
    return KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4")


def _step(sp, step, *, bin=BM, rung="explore", slots=("WORKSPACE",),
          mode="no-steps", gate="g1", level=0, staked=True, rng=na.EP):
    """One complete narrated step at the spine: BET -> PLAN -> ACT, then
    PERCEIVE -> ROUTE -> MINT -> ECHO closing against the bet. The unit the
    monitor reads is (ROUTE.bin + fact; ACT.rung, BET.bin, slot shape,
    PLAN.mode, PLAN.gate) -- every component is a parameter here."""
    sp.start_step(step)
    pb, why = na.predict_bin(staked, True)
    sp.bet(slots={s: {"predicted": "holds"} for s in slots}, route_bin=pb,
           why_not=why, mint_candidate=None, guard_zero=na.GUARD_SUPPORT,
           rng=rng, level=level)
    sp.plan(mode, gate, rng=rng)
    sp.act(6, rung, rng=rng)
    sp.perceive({s: {"bet": staked, "residual": 1.0, "bin": bin}
                 for s in slots}, rng=rng)
    sp.route(bin, na.route_why_not(bin), dict.fromkeys(slots, bin), rng=rng)
    sp.mint_point(None, None, na.GUARD_SUPPORT, None, rng=rng)
    sp.echo("settled", {}, rng=rng)


def _history(sp, counts):
    """A prior episode's level ledger on `sp`'s game: BET records whose
    `level` field crosses so that the per-level step counts equal `counts`
    (one trailing step on the final level stays uncounted -- never crossed)."""
    step, lv = 0, 0
    for n in counts:
        for _ in range(n):
            _step(sp, step, bin=na.TRANSFERRED, level=lv)
            step += 1
        lv += 1
    _step(sp, step, bin=na.TRANSFERRED, level=lv)


def _armed(tmp_path, name="f", counts=(3, 4, 6), game=GAME):
    """An agent with OWN history on `game` (a prior episode with level
    crossings -> k = the upper median of `counts`), then a NEW episode's
    spine with the monitor attached and primed from the stream, the episode
    boundary marked by the ARM record exactly as the loop emits it."""
    fab = _fab(tmp_path, name)
    prior = na.NarrationSpine(fab, game=game)
    prior.narrate_arm(na.ARM_W, step=0)
    _history(prior, counts)
    sp = na.NarrationSpine(fab, game=game)
    sp.monitor = pm.PersistenceMonitor.from_fabric(fab)
    sp.narrate_arm(na.ARM_W, step=0)
    return fab, sp


def _recs(fab, point=None):
    out = fab.query("personal", na.TOPIC)
    return out if point is None else [r for r in out if r["point"] == point]


def _k(sp):
    k = sp.monitor.readout(sp.game)["k"]
    assert k is not None and k >= pm.K_FLOOR
    return k


# ---------------------------------------------------------------------------
# F1 -- EXACTLY k
# ---------------------------------------------------------------------------

class TestF1ExactlyK:

    def test_one_record_at_k_none_before_none_after(self, tmp_path):
        fab, sp = _armed(tmp_path)
        k = _k(sp)
        assert k == 4, "the constructed OWN history (3, 4, 6) has upper median 4"
        for i in range(2 * k):
            _step(sp, i)
        recs = _recs(fab, na.PERSISTENCE)
        assert len(recs) == 1, (
            "ONE record per run: fires at k, not again at k+1 (%d records)"
            % len(recs))
        r = recs[0]
        assert r["step"] == k - 1, "fires at the run's k-th step, not before"
        assert r["side"] == na.SIDE_MONITOR and r["point"] == na.PERSISTENCE
        assert r["k"] == k and r["run"] == k
        assert r["first_step"] == 0 and r["last_step"] == k - 1
        assert r["game"] == GAME and r["range"] == na.EP
        first_bet = [b for b in _recs(fab, na.BET) if b["step"] == 0][-1]
        assert r["ref"] == first_bet["id"], (
            "ref = the run's first BET id (this episode's step-0 bet)")
        assert r["rho"] == {"bin": BM, "fact": na.NEIGHBOUR[BM][1]}
        assert r["sigma"] == {"rung": "explore", "bin": na.TRANSFERRED,
                              "slots": ["WORKSPACE"], "mode": "no-steps",
                              "gate": "g1"}
        assert r["gloss"] == r["gloss"].upper() and r["gloss"]
        route = [x for x in _recs(fab, na.ROUTE) if x["step"] == k - 1][-1]
        assert r["sq"] == route["sq"] + 1, (
            "the record lands right after the ROUTE that closed the k-th step")
        ro = sp.monitor.readout(GAME)
        assert ro["status"] == pm.PERSISTING and ro["run"] == 2 * k
        assert ro["persist"] == 1.0, "the live state holds until the run resets"

    def test_w1_f1_untouched_one_bet_per_step_and_the_record_is_never_a_bet(
            self, tmp_path):
        fab, sp = _armed(tmp_path)
        k = _k(sp)
        for i in range(k + 1):
            _step(sp, i)
        recs = _recs(fab)
        arm_at = max(i for i, r in enumerate(recs) if r["point"] == na.ARM)
        episode = recs[arm_at + 1:]          # this episode's records only
        fired = [r for r in episode if r["point"] == na.PERSISTENCE]
        assert len(fired) == 1
        assert fired[0]["side"] != na.SIDE_BET and fired[0]["point"] != na.BET
        bets = [r for r in episode if r["point"] == na.BET]
        assert sorted(b["step"] for b in bets) == list(range(k + 1)), (
            "W1's F1 holds: exactly one BET per step, the finding is no bet")
        acts = [r for r in episode if r["point"] == na.ACT]
        by_id = {r["id"]: r for r in episode}
        assert all(by_id[a["ref"]]["sq"] < a["sq"] for a in acts), (
            "F1 precedence holds with the monitor attached")

    def test_persist_channel_is_run_over_k_bounded(self, tmp_path):
        fab, sp = _armed(tmp_path)
        k = _k(sp)
        seen = []
        for i in range(2 * k):
            _step(sp, i)
            seen.append(sp.monitor.persist(GAME))
        assert seen[:k] == [min(1.0, (i + 1) / k) for i in range(k)]
        assert all(v == 1.0 for v in seen[k:]), "bounded at 1 past k"


# ---------------------------------------------------------------------------
# F2 -- RESET on each sigma component, separately
# ---------------------------------------------------------------------------

class TestF2Reset:

    CHANGES = {
        "rung": {"rung": "wall"},
        "shape": {"slots": ("BODY", "WORKSPACE")},
        "gate": {"gate": "g4"},
        "mode": {"mode": "shadowed"},
        "bin": {"staked": False},          # BET.bin NOVEL; ROUTE unchanged
    }

    @pytest.mark.parametrize("component", sorted(CHANGES))
    def test_a_sigma_change_at_k_minus_1_never_fires_and_counts_from_1(
            self, tmp_path, component):
        fab, sp = _armed(tmp_path, name=component)
        k = _k(sp)
        n = 2 * k - 2
        for i in range(n):
            _step(sp, i, **(self.CHANGES[component] if i == k - 2 else {}))
        assert _recs(fab, na.PERSISTENCE) == [], (
            "sigma.%s changed at step k-1 -- the run must reset" % component)
        ro = sp.monitor.readout(GAME)
        assert ro["run"] == k - 1, (
            "resumed identity counts from 1 (k-1 steps since the change)")
        assert ro["status"] == pm.COUNTING

    def test_a_rho_change_resets_too(self, tmp_path):
        fab, sp = _armed(tmp_path)
        k = _k(sp)
        for i in range(2 * k - 2):
            _step(sp, i, bin=(BR if i == k - 2 else BM))
        assert _recs(fab, na.PERSISTENCE) == []
        assert sp.monitor.readout(GAME)["run"] == k - 1


# ---------------------------------------------------------------------------
# F3 -- NON-REPEATING never fires
# ---------------------------------------------------------------------------

class TestF3NonRepeating:

    def test_alternating_bins_never_fire(self, tmp_path):
        fab, sp = _armed(tmp_path)
        k = _k(sp)
        for i in range(3 * k):
            _step(sp, i, bin=(BM if i % 2 == 0 else BR))
        assert _recs(fab, na.PERSISTENCE) == []
        assert sp.monitor.readout(GAME)["run"] == 1

    def test_alternating_rungs_never_fire(self, tmp_path):
        fab, sp = _armed(tmp_path)
        k = _k(sp)
        for i in range(3 * k):
            _step(sp, i, rung=("explore" if i % 2 == 0 else "wall"))
        assert _recs(fab, na.PERSISTENCE) == []
        assert sp.monitor.readout(GAME)["run"] == 1


# ---------------------------------------------------------------------------
# F4 -- CONSUMER ONLY: replay == online; the allowlist entry is gone
# ---------------------------------------------------------------------------

def _strip_seq(recs):
    return [{k: v for k, v in r.items() if k != "seq"} for r in recs]


class TestF4ConsumerOnly:

    def test_replay_over_the_jsonl_equals_the_online_emission(self, tmp_path):
        fab, sp = _armed(tmp_path)
        k = _k(sp)
        # two runs in one episode (a sigma change between them) + a second
        # episode: three firings, each reconstructed byte for byte
        for i in range(k):
            _step(sp, i)
        for i in range(k, 2 * k):
            _step(sp, i, rung="wall")
        sp2 = na.NarrationSpine(fab, game=GAME)
        sp2.monitor = pm.PersistenceMonitor.from_fabric(fab)
        sp2.narrate_arm(na.ARM_W, step=0)
        for i in range(k + 2):
            _step(sp2, i, gate="g3")
        online = _strip_seq(_recs(fab, na.PERSISTENCE))
        assert len(online) == 3
        replayed = pm.replay(fab)
        assert replayed == online, "the replay is not the online emission"
        assert ([json.dumps(r, ensure_ascii=False) for r in replayed]
                == [json.dumps(r, ensure_ascii=False) for r in online]), (
            "byte-identical means the serialised bytes, key order included")
        assert pm.replay(fab, game="other") == []

    def test_the_allowlist_entry_is_gone_and_the_scanner_sees_the_reader(self):
        r3 = _r3()
        assert "narration" not in r3.ALLOWLIST, (
            "the consumer landed: the `narration` entry must be DELETED")
        writes, reads = r3._scan()
        assert "narration" in writes, "the spine's writer vanished"
        outside = r3._outside_readers("narration", writes, reads)
        assert outside, "narration lost its consumer"
        assert any("persistence" in path for path, _fn in outside), (
            "the reader is not the persistence monitor: %r" % (outside,))
        assert not any("persistence" in path
                       for sites in writes.values() for path, _fn in sites), (
            "the monitor WRITES a stream -- it is a read-only consumer")

    def test_the_hot_path_reads_no_stream(self):
        for fn in (pm.PersistenceMonitor.observe, pm.PersistenceMonitor._observe,
                   pm.PersistenceMonitor.persist):
            src = inspect.getsource(fn)
            assert "query" not in src and "open(" not in src, (
                "%s reads a stream on the hot path" % fn.__name__)
        src = open(os.path.join(REPO, "engines", "egocentric", "narration.py"),
                   encoding="utf-8").read()
        assert src.count(".observe(") == 1, "ONE observer hook in the spine"
        assert src.count(".append(") == 1 and ".query" not in src

    def test_the_monitor_survives_a_hostile_record_and_counts_the_error(self):
        mon = pm.PersistenceMonitor()
        assert mon.observe({"point": na.BET}) == []
        assert mon.observe(None) == [] and mon.errors == 1


# ---------------------------------------------------------------------------
# F5 -- NO PRICE READS IT (structural + identity of the sinks)
# ---------------------------------------------------------------------------

PRICE_MODULES = (
    "engines/egocentric/mint.py",          # the MDL terms
    "engines/egocentric/pricing.py",       # salience + the iced marketplace
    "engines/egocentric/consumer.py",      # admission price, echo bookkeeping
    "engines/egocentric/fabric.py",        # reputation
    "engines/egocentric/effects.py",       # encoding cost, Gamma
    "engines/egocentric/bank.py",
    "engines/egocentric/betting.py",
    "engines/egocentric/composer.py",      # the local mint's bargain
    "engines/egocentric/gate.py",          # standing
    "evolutionary_engine.py",              # tournament weighting / breeding
    "cognitive_game_player.py",
)
CHANNEL_NAMES = {"persist", "PERSISTENCE", "persistence", "PersistenceMonitor"}


class TestF5NoPriceReadsIt:

    @pytest.mark.parametrize("rel", PRICE_MODULES)
    def test_no_reference_to_the_channel_or_the_token(self, rel):
        path = os.path.join(REPO, rel)
        assert os.path.exists(path), rel
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
        hits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in CHANNEL_NAMES:
                hits.append("name %s:%d" % (node.id, node.lineno))
            elif isinstance(node, ast.Attribute) and node.attr in CHANNEL_NAMES:
                hits.append("attr %s:%d" % (node.attr, node.lineno))
            elif (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and node.value in ("persist", "PERSISTENCE")):
                hits.append("str %r:%d" % (node.value, node.lineno))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names]
                mod = getattr(node, "module", None) or ""
                if "persistence" in mod or "persistence" in names:
                    hits.append("import:%d" % node.lineno)
        assert not hits, "%s references the persistence channel/token: %r" % (
            rel, hits)

    def test_the_sinks_by_identity(self, tmp_path, monkeypatch):
        """A REAL monitor at a full run vs none: explore_boost and the stall
        clock move; seed_bias, mint_bar and the lp order do not."""
        monkeypatch.delenv("LP_DRIVE_ARM", raising=False)
        _fab_, sp = _armed(tmp_path, name="m")
        k = _k(sp)
        for i in range(k):
            _step(sp, i)
        assert sp.monitor.persist(GAME) == 1.0
        wired, unwired = af.AffectGains(_fab(tmp_path, "w")), af.AffectGains(
            _fab(tmp_path, "u"))
        wired.monitor = sp.monitor
        gw, gu = wired.gains(), unwired.gains()
        assert set(gw) == {"seed_bias", "mint_bar", "persist"}
        assert gw["persist"] == 1.0 and gu["persist"] == 0.0
        assert gw["seed_bias"] == gu["seed_bias"], "seed_bias is not a sink"
        assert gw["mint_bar"] == gu["mint_bar"], "the mint bar is not a sink"
        sw, su = (wired.starvation_steer(GAME)["explore_boost"],
                  unwired.starvation_steer(GAME)["explore_boost"])
        assert su == 1.0 and sw == 1.0 + af.AffectGains.STARVE_STEP, (
            "a full run widens explore effort by exactly one STARVE_STEP")
        assert sw <= af.AffectGains.STARVE_CEIL
        cands = [((5, 5), 0.9), ((2, 2), 0.5)]
        assert wired.lp_steer(list(cands), GAME) == unwired.lp_steer(
            list(cands), GAME), "the lp order is not a sink"
        # the goal stuck measure: the stall clock runs at most twice as fast
        def _stall(persist):
            gm = go.GoalManager(stall_steps=6)
            gm.propose([((1, 1), 0), ((2, 2), 1)])
            first = gm.active_goal()
            n = 0
            while gm.active == first and n < 50:
                gm.observe(False, False, persist=persist)
                n += 1
            return n
        assert _stall(0.0) == 6 and _stall(1.0) == 3, (
            "persist=1 must halve the steps to abandonment; persist=0 is today")
        assert _stall(0.5) == 4


# ---------------------------------------------------------------------------
# F6 -- THE WIRE CHECK: the channel flips an explore choice at the loop's site
# ---------------------------------------------------------------------------

class _Map:
    def __init__(self, productive):
        self._p = list(productive)

    def get_productive_targets(self):
        return list(self._p)


class TestF6WireCheck:

    PRODUCTIVE = [((1, 1), 0.9), ((2, 2), 0.8), ((3, 3), 0.7), ((4, 4), 0.6)]

    def _choice(self, tmp_path, monitor, name):
        """Drive the loop's OWN explore seam (_act, strategy=explore) with
        the affect gains wired to `monitor` (None = unwired, today), the
        rotation window computed by the loop's own B5 line."""
        aff = af.AffectGains(_fab(tmp_path, name))
        aff.monitor = monitor
        s = SimpleNamespace(
            _causal_map=_Map(self.PRODUCTIVE), _available_actions=[6],
            _goal_cells_total=1, _affect=aff, _game_id=GAME,
            _ego_explore_widen=float(aff.seed_gain(GAME)["boost"]),
            _productive_rotation_index=3, _decision_system=None,
            _agent_position=None)
        cf = SimpleNamespace()
        a, data = cl.CognitiveLoop._act(s, None, "explore", 0.0, None, None,
                                        "a", "r", 0.0, 0.0, cf)
        assert a == 6 and cf.action_speed == "explore"
        return (data["x"], data["y"])

    def test_a_run_at_k_flips_the_explore_choice(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LP_DRIVE_ARM", raising=False)
        _fab_, sp = _armed(tmp_path, name="run")
        k = _k(sp)
        for i in range(k):
            _step(sp, i)
        assert sp.monitor.persist(GAME) == 1.0
        unwired = self._choice(tmp_path, None, "u")
        wired = self._choice(tmp_path, sp.monitor, "w")
        assert unwired == (1, 1), "today: a 3-wide rotation window"
        assert wired == (4, 4), (
            "the channel did not flip the explore choice -- the wire is thin")
        assert wired != unwired

    def test_below_k_nothing_flips(self, tmp_path, monkeypatch):
        """Specificity: a run short of k is a number, not a takeover -- at
        this window the choice is unchanged until the run fills."""
        monkeypatch.delenv("LP_DRIVE_ARM", raising=False)
        _fab_, sp = _armed(tmp_path, name="short")
        _step(sp, 0)
        assert 0.0 < sp.monitor.persist(GAME) < 1.0
        assert self._choice(tmp_path, sp.monitor, "w") == self._choice(
            tmp_path, None, "u")

    def test_the_live_seam_is_the_loops_own(self):
        src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                   errors="replace").read()

        def body(name):
            i = src.find("def %s" % name)
            assert i != -1, name
            j = src.find("\n    def ", i + 10)
            return src[i:j if j != -1 else len(src)]

        assert 'self._ego_explore_widen = float(_sg["boost"])' in body(
            "record_result"), "B5's applied-bias line moved"
        assert '3 * getattr(self, "_ego_explore_widen", 1.0)' in body("_act"), (
            "the rotation window no longer reads the widen")
        nb = body("_narr_bet")
        assert "_pm_attach(loop, _nsp)" in nb, "the monitor is not attached"
        assert "level=int(getattr(loop, \"_ego_level\", 0) or 0)" in nb, (
            "the BET record does not carry the loop's level")
        assert "PersistenceMonitor.from_fabric(" in body("_pm_attach")

    def test_the_loop_seam_attaches_and_stamps_level(self, tmp_path):
        s = SimpleNamespace(
            _ego_fabric=_fab(tmp_path), _game_id=GAME, _actions_taken=0,
            _ego_agent_id="a", _ego_level=2, _w2b_narr=None, _narr_import_n=0,
            _narration=None, _narr_slots=None, _atom_verified={},
            _residual_router=None, _plan_gate={"cycles": 1},
            _affect=af.AffectGains(_fab(tmp_path, "aff")))
        cf = SimpleNamespace(action_confidence=0.0, rung_name="",
                             action_speed="explore")
        cl._narr_bet(s, 6, cf, {})
        assert isinstance(s._narration.monitor, pm.PersistenceMonitor)
        assert s._affect.monitor is s._narration.monitor, (
            "the affect gains read a different fold than the spine feeds")
        bet = _recs(s._ego_fabric, na.BET)[0]
        assert bet["level"] == 2, "the additive level field from _ego_level"


# ---------------------------------------------------------------------------
# R4 -- TRANSFERRED resets; NOVEL never starts; [REPLAY] resets
# ---------------------------------------------------------------------------

class TestR4:

    def test_transferred_at_j_below_k_resets(self, tmp_path):
        fab, sp = _armed(tmp_path)
        k = _k(sp)
        for i in range(k - 1):
            _step(sp, i)
        assert sp.monitor.readout(GAME)["run"] == k - 1
        _step(sp, k - 1, bin=na.TRANSFERRED)
        assert sp.monitor.readout(GAME)["run"] == 0, "success resets"
        for i in range(k, 2 * k - 1):
            _step(sp, i)
        assert _recs(fab, na.PERSISTENCE) == []
        assert sp.monitor.readout(GAME)["run"] == k - 1

    def test_novel_never_starts_a_run(self, tmp_path):
        fab, sp = _armed(tmp_path)
        k = _k(sp)
        for i in range(2 * k):
            _step(sp, i, bin=na.NOVEL, staked=False)
        assert _recs(fab, na.PERSISTENCE) == []
        ro = sp.monitor.readout(GAME)
        assert ro["run"] == 0 and ro["persist"] == 0.0

    def test_a_replay_step_resets(self, tmp_path):
        fab, sp = _armed(tmp_path)
        k = _k(sp)
        for i in range(k - 1):
            _step(sp, i)
        sp.replay(3, step=k - 1)
        assert sp.monitor.readout(GAME)["run"] == 0, "[REPLAY]: bin None"
        for i in range(k, 2 * k - 1):
            _step(sp, i)
        assert _recs(fab, na.PERSISTENCE) == []
        assert sp.monitor.readout(GAME)["run"] == k - 1

    def test_a_level_change_resets(self, tmp_path):
        fab, sp = _armed(tmp_path)
        k = _k(sp)
        for i in range(k - 1):
            _step(sp, i, level=0)
        for i in range(k - 1, 2 * k - 2):
            _step(sp, i, level=1)
        assert _recs(fab, na.PERSISTENCE) == []
        ro = sp.monitor.readout(GAME)
        assert ro["run"] == k - 1 and ro["level_reset"] == pm.LEVEL_RESET_ON


# ---------------------------------------------------------------------------
# KNOWN-NEGATIVE + k: derived, fallbacks stated, frozen within a level
# ---------------------------------------------------------------------------

class TestKnownNegativeAndK:

    def test_k_undefined_counts_never_fires_readout_unarmed(self, tmp_path):
        fab = _fab(tmp_path)
        sp = na.NarrationSpine(fab, game=GAME)
        sp.monitor = pm.PersistenceMonitor.from_fabric(fab)
        for i in range(12):
            _step(sp, i)
        assert _recs(fab, na.PERSISTENCE) == []
        ro = sp.monitor.readout(GAME)
        assert ro["status"] == pm.UNARMED and ro["k"] is None
        assert ro["run"] == 12, "it counts"
        assert ro["persist"] == 0.0 and sp.monitor.persist(GAME) == 0.0
        a = af.AffectGains(fab)
        a.monitor = sp.monitor
        assert a.persist(GAME) == 0.0 and a.gains()["persist"] == 0.0

    def test_k_is_the_upper_median_floored_at_two(self):
        assert pm.derive_k([3, 4, 6], []) == (4, na.OWN)
        assert pm.derive_k([1, 1, 1], []) == (pm.K_FLOOR, na.OWN)
        assert pm.derive_k([], [5, 7]) == (7, na.COL)
        assert pm.derive_k([], []) == (None, None)
        assert pm.K_FLOOR == 2, "pinned by the prereg: repetition is the trend"

    def test_col_fallback_when_own_has_no_crossing(self, tmp_path):
        fab = _fab(tmp_path)
        other = na.NarrationSpine(fab, game="g2")
        other.narrate_arm(na.ARM_W, step=0)
        _history(other, (5, 7))
        sp = na.NarrationSpine(fab, game=GAME)
        sp.monitor = pm.PersistenceMonitor.from_fabric(fab)
        sp.narrate_arm(na.ARM_W, step=0)
        _step(sp, 0)
        ro = sp.monitor.readout(GAME)
        assert (ro["k"], ro["k_source"]) == (7, na.COL)

    def test_k_recomputed_at_a_crossing_and_frozen_within_a_level(
            self, tmp_path):
        fab, sp = _armed(tmp_path, counts=(2, 2, 9))
        assert _k(sp) == 2
        for i in range(6):
            _step(sp, i, bin=na.TRANSFERRED, level=0)
        assert sp.monitor.readout(GAME)["k"] == 2, "frozen within the level"
        _step(sp, 6, bin=na.TRANSFERRED, level=1)
        ro = sp.monitor.readout(GAME)
        assert ro["level_counts"] == [2, 2, 9, 6]
        assert ro["crossings"] == 4, "3 prior-episode crossings + this one"
        assert (ro["k"], ro["k_source"]) == (6, na.OWN), "recomputed at the crossing"
        for i in range(7, 20):
            _step(sp, i, bin=na.TRANSFERRED, level=1)
        assert sp.monitor.readout(GAME)["k"] == 6, "the run never moves its bar"

    def test_records_without_level_cannot_reset_on_level_and_say_so(
            self, tmp_path):
        fab = _fab(tmp_path)
        sp = na.NarrationSpine(fab, game=GAME)
        sp.monitor = pm.PersistenceMonitor.from_fabric(fab)
        sp.start_step(0)
        b, w = na.predict_bin(True, True)
        sp.bet({}, b, w, None, na.GUARD_SUPPORT, rng=na.EP)
        assert "level" not in _recs(fab, na.BET)[0], "additive: absent when not given"
        ro = sp.monitor.readout(GAME)
        assert ro["level_reset"] == pm.LEVEL_RESET_OFF
        assert ro["status"] == pm.UNARMED


# ---------------------------------------------------------------------------
# THE RECORD IS DETERMINISTIC (no wall-clock; the same construction twice)
# ---------------------------------------------------------------------------

class TestDeterminism:

    def test_the_same_construction_yields_the_same_bytes(self, tmp_path):
        outs = []
        for name in ("a", "b"):
            fab, sp = _armed(tmp_path, name=name)
            for i in range(_k(sp) + 1):
                _step(sp, i)
            outs.append([json.dumps(r, ensure_ascii=False)
                         for r in _strip_seq(_recs(fab, na.PERSISTENCE))])
        assert outs[0] == outs[1] and len(outs[0]) == 1
        rec = json.loads(outs[0][0])
        for key in rec:
            assert not any(s == key.lower() or key.lower().endswith("_" + s)
                           for s in ("time", "timestamp", "ts", "wall", "date",
                                     "now")), key
        assert na.PERSISTENCE in na.POINTS and (
            na.PERSISTENCE, na.SIDE_MONITOR) in na.GLOSS

"""The agent cleanup must actually delete, and a cleanup that fails must be LOUD.

`AgentLifecycleManager.cleanup_ancient_inactive_agents` ran every 50th
generation and threw `FOREIGN KEY constraint failed` EVERY time: `agents.agent_id`
is referenced by 54 foreign keys across 50 child tables on a real box DB and the
method issued a bare `DELETE FROM agents`. The exception's only reader was
`if self.verbose: print(...)` in evolution_runner, so the population bound was
never enforced and nothing said so above a debug line -- 28,892 agents fleet-wide,
26,397 of them inactive and uncullable, per-box DBs at 145-935 MB.

What these tests pin:
  F1  the cascade works and leaves no orphan and no FK violation
  F2  the PRE-FIX delete path is the oracle -- it raises on the same fixture,
      so F1 is proof the fix changed something real and not proof of an
      accidentally-easy fixture
  F3  a failing cleanup is recorded on a NAMED consumer, asserted BY IDENTITY
      (`manager.cleanup_failures`), never by capturing stdout
  F4  an active agent and a recent inactive one both survive
  F5  idempotence: the second pass deletes nothing and does not error
  KN  the known negative -- with `discovery_prestige` and
      `best_single_game_score` permanently 0 (the real fleet condition) tiers 2
      and 3 select NOBODY and tier 1 selects the whole ancient inactive set

LAWS. ASSERTED here: FIGURE 10 (the loud consumer is checkable -- F3 fails if
the failure is swallowed) and FIGURE 3 (the cleanup now has an instrument; F1/F5
read it). ASSUMED, not asserted: FIGURE 1 -- that deletion counts are frame-
internal bookkeeping and never progress is a claim about how the numbers are
READ, which no test in this file can check.
"""
from __future__ import annotations

import ast
import os
import sqlite3
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

CURRENT_GENERATION = 100          # tier-1 threshold lands at generation 50
ANCIENT = (1, 2)                  # generations well inside every tier window


# --------------------------------------------------------------------------
# fixture: a miniature of the real shape -- an OWNED child (NOT NULL), an
# OWNED-BY-PRIMARY-KEY child, an ATTRIBUTION child (nullable provenance), and
# a GRANDCHILD reachable only through another child. All four dispositions.
# --------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    genome TEXT, epigenetics TEXT, sensation_profile TEXT,
    generation INTEGER,
    total_games_played INTEGER DEFAULT 0,
    total_games_won INTEGER DEFAULT 0,
    best_single_game_score REAL DEFAULT 0,
    discovery_prestige REAL DEFAULT 0,
    social_rule_adherence REAL DEFAULT 0,
    is_active BOOLEAN DEFAULT 1
);

CREATE TABLE agent_archive (
    agent_id TEXT PRIMARY KEY,
    archived_at TEXT NOT NULL,
    final_prestige REAL,
    final_performance REAL,
    network_median_at_sunset REAL,
    knowledge_transfer_rate REAL,
    reasoning_summary TEXT,
    revival_candidate BOOLEAN DEFAULT 0,
    sunset_reason TEXT
);

CREATE TABLE archived_agent_discoveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL, discovery_type TEXT NOT NULL,
    discovery_data TEXT, archived_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE agent_object_control (
    agent_id TEXT, game_id TEXT, level_number INTEGER,
    controlled_objects TEXT, confidence REAL
);

-- OWNED: agent_id NOT NULL, so the row cannot outlive its agent.
CREATE TABLE agent_operating_modes (
    mode_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    operating_mode TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- OWNED BY PRIMARY KEY: nullable in SQLite's quirky sense, but it IS the key,
-- so releasing it to NULL would leave a row keyed by nothing.
CREATE TABLE agent_meta_learning (
    agent_id TEXT PRIMARY KEY,
    strategy TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- ATTRIBUTION: nullable provenance. The knowledge outlives the knower.
CREATE TABLE knowledge_graph_edges (
    edge_id INTEGER PRIMARY KEY,
    claim TEXT,
    discovered_by_agent TEXT,
    FOREIGN KEY (discovered_by_agent) REFERENCES agents(agent_id)
);

-- OWNED, and itself a parent: forces the walk to descend before it deletes.
CREATE TABLE collective_action_proposals (
    proposal_id TEXT PRIMARY KEY,
    proposing_agent_id TEXT NOT NULL,
    FOREIGN KEY (proposing_agent_id) REFERENCES agents(agent_id)
);

-- GRANDCHILD: reachable from agents only through the proposal. Note the voter
-- here SURVIVES the cull -- the vote dies because its PROPOSAL died.
CREATE TABLE collective_votes (
    vote_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    voting_agent_id TEXT NOT NULL,
    FOREIGN KEY (proposal_id) REFERENCES collective_action_proposals(proposal_id),
    FOREIGN KEY (voting_agent_id) REFERENCES agents(agent_id)
);
"""

# (agent_id, generation, is_active) -- the two ancients are the only cull targets
_AGENTS = [
    ("ancient_a", ANCIENT[0], 0),
    ("ancient_b", ANCIENT[1], 0),
    ("active_now", ANCIENT[0], 1),          # ancient generation, but ACTIVE
    ("recent_inactive", 80, 0),             # inactive, but inside the window
    ("survivor_voter", ANCIENT[0], 1),      # active; votes on a doomed proposal
]


def _connect(tmp_path) -> sqlite3.Connection:
    con = sqlite3.connect(os.path.join(str(tmp_path), "lifecycle.db"))
    con.row_factory = sqlite3.Row          # as DatabaseInterface._get_connection does
    con.executescript(_SCHEMA)
    con.execute("PRAGMA foreign_keys=ON")  # as DatabaseInterface._get_connection does
    con.executemany(
        "INSERT INTO agents (agent_id, genome, generation, is_active, "
        "total_games_won, best_single_game_score, discovery_prestige) "
        "VALUES (?, 'g', ?, ?, 0, 0, 0)", _AGENTS)

    # every agent owns an operating mode -- this is why "delete only childless
    # agents" is not an option: on the measured box, 0 of 2,459 were childless
    con.executemany(
        "INSERT INTO agent_operating_modes (mode_id, agent_id, operating_mode) VALUES (?,?,?)",
        [(f"m_{a}", a, "pioneer") for a, _, _ in _AGENTS])
    con.execute("INSERT INTO agent_meta_learning (agent_id, strategy) VALUES ('ancient_a','s')")
    con.execute("INSERT INTO knowledge_graph_edges (edge_id, claim, discovered_by_agent) "
                "VALUES (1, 'a claim worth keeping', 'ancient_a')")
    con.execute("INSERT INTO collective_action_proposals (proposal_id, proposing_agent_id) "
                "VALUES ('p1', 'ancient_a')")
    con.execute("INSERT INTO collective_votes (vote_id, proposal_id, voting_agent_id) "
                "VALUES ('v1', 'p1', 'survivor_voter')")
    con.execute("INSERT INTO agent_object_control "
                "(agent_id, game_id, level_number, controlled_objects, confidence) "
                "VALUES ('ancient_a', 'gid', 1, '[]', 0.5)")
    con.commit()
    return con


class _StubDB:
    """Minimal stand-in for DatabaseInterface: the cleanup only ever calls
    `_get_connection()`."""

    def __init__(self, con):
        self._con = con

    def _get_connection(self):
        return self._con


def _manager(con):
    from agent_lifecycle_manager import AgentLifecycleManager
    return AgentLifecycleManager(_StubDB(con))


def _ids(con, table, col="agent_id"):
    return {r[0] for r in con.execute(f"SELECT {col} FROM {table}")}  # noqa: S608 - fixed identifiers


def _count(con, table):
    return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608 - fixed identifiers


def _runner_ast() -> ast.Module:
    """The call site lives in the runner's every-50-gen cadence; these checks
    read it structurally rather than by importing it (evolution_runner pulls in
    the whole cognitive stack)."""
    with open(os.path.join(REPO, "evolution_runner.py"), encoding="utf-8",
              errors="replace") as handle:
        return ast.parse(handle.read())


# --------------------------------------------------------------------------
# F2 -- THE ORACLE. Run FIRST in the file for the same reason a control is run
# first: if this ever stops raising, every other test here is measuring nothing.
# --------------------------------------------------------------------------

class TestThePreFixPathIsTheOracle:

    def test_todays_delete_path_raises_foreign_key_constraint_failed(self, tmp_path):
        """A LITERAL transcription of the shipped delete path (agent_lifecycle_manager.py
        :107-180 before this build): select the tier, then `DELETE FROM agents`
        with no cascade. On this fixture it must raise exactly what 16 worker
        logs recorded 31 times."""
        con = _connect(tmp_path)
        rows = con.execute("""
            SELECT agent_id, generation, best_single_game_score, discovery_prestige
            FROM agents
            WHERE is_active = 0
                AND generation <= ?
                AND COALESCE(best_single_game_score, 0) = 0
                AND COALESCE(total_games_won, 0) = 0
                AND COALESCE(discovery_prestige, 0) < 10
        """, (CURRENT_GENERATION - 50,)).fetchall()
        assert len(rows) == 2, "the oracle needs the same targets the fix gets"

        with pytest.raises(sqlite3.IntegrityError) as caught:
            for agent_id, _gen, _score, _prestige in rows:
                con.execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,))
        assert "FOREIGN KEY constraint failed" in str(caught.value), (
            "the pre-fix path did NOT reproduce the fleet failure -- the fixture "
            "is easier than production and F1 proves nothing")

    def test_the_oracle_needs_foreign_keys_actually_enforced(self, tmp_path):
        """The falsifier for the oracle: with enforcement off the same statement
        succeeds. Proof that F2 measures the constraint and not a typo."""
        con = _connect(tmp_path)
        con.execute("PRAGMA foreign_keys=OFF")
        con.execute("DELETE FROM agents WHERE agent_id = 'ancient_a'")
        assert "ancient_a" not in _ids(con, "agents")


# --------------------------------------------------------------------------
# F1 / F4 / F5 -- the fix
# --------------------------------------------------------------------------

class TestCleanupActuallyDeletes:

    def test_f1_deletes_agents_and_leaves_no_orphan_and_no_fk_violation(self, tmp_path):
        con = _connect(tmp_path)
        stats = _manager(con).cleanup_ancient_inactive_agents(CURRENT_GENERATION)

        assert stats["total_deleted"] == 2, (
            "cleanup deleted %r agents -- the whole defect was that it deleted "
            "zero" % stats["total_deleted"])
        assert _ids(con, "agents") == {"active_now", "recent_inactive", "survivor_voter"}
        assert not con.execute("PRAGMA foreign_key_check").fetchall(), (
            "the DB is left with foreign key violations -- the cascade orphaned rows")

        # no orphaned children of the deleted agents, by direct check
        survivors = _ids(con, "agents")
        assert _ids(con, "agent_operating_modes") <= survivors
        assert _ids(con, "agent_meta_learning") <= survivors
        assert _count(con, "collective_action_proposals") == 0
        assert _count(con, "collective_votes") == 0, (
            "the GRANDCHILD survived: the walk deleted the proposal but not the "
            "vote that referenced it")
        assert stats["failures"] == 0 and stats["failure_detail"] == []

    def test_f1_attribution_is_released_not_destroyed(self, tmp_path):
        """A nullable provenance reference means the schema always intended the
        row to outlive the agent. Shared knowledge must survive its discoverer."""
        con = _connect(tmp_path)
        _manager(con).cleanup_ancient_inactive_agents(CURRENT_GENERATION)

        edge = con.execute("SELECT claim, discovered_by_agent FROM knowledge_graph_edges "
                           "WHERE edge_id = 1").fetchone()
        assert edge is not None, "a nullable-FK knowledge row was DELETED with its discoverer"
        assert edge[0] == "a claim worth keeping"
        assert edge[1] is None, "the dead agent is still named as discoverer"

    def test_the_archive_is_meaningful_not_archived_into_a_failing_delete(self, tmp_path):
        """`_archive_agent_knowledge` inserted columns that have never existed
        (`agent_data`, `generation`) and swallowed the error into logger.debug;
        `agent_archive` holds 0 rows fleet-wide. If the archive is empty after a
        purge, the deletion ate evidence."""
        con = _connect(tmp_path)
        _manager(con).cleanup_ancient_inactive_agents(CURRENT_GENERATION)

        archived = {r[0] for r in con.execute("SELECT agent_id FROM agent_archive")}
        assert archived == {"ancient_a", "ancient_b"}, (
            "archive holds %r -- agents were deleted without being archived" % archived)
        row = con.execute("SELECT reasoning_summary, sunset_reason FROM agent_archive "
                          "WHERE agent_id = 'ancient_a'").fetchone()
        assert row[0] and "genome" in row[0], "the archived blob carries no genetic material"
        assert row[1] == "lifecycle_cleanup"
        assert _count(con, "archived_agent_discoveries") == 1, (
            "the object-control discovery was not archived before its agent died")

    def test_f4_active_and_recent_inactive_agents_survive(self, tmp_path):
        con = _connect(tmp_path)
        _manager(con).cleanup_ancient_inactive_agents(CURRENT_GENERATION)
        survivors = _ids(con, "agents")

        assert "active_now" in survivors, (
            "an ACTIVE agent was deleted -- the cull is eating the live population")
        assert "recent_inactive" in survivors, (
            "an inactive agent INSIDE the generation window was deleted -- the "
            "threshold is not being applied")
        assert "survivor_voter" in survivors

    def test_f5_second_pass_deletes_nothing_and_does_not_error(self, tmp_path):
        con = _connect(tmp_path)
        manager = _manager(con)
        first = manager.cleanup_ancient_inactive_agents(CURRENT_GENERATION)
        second = manager.cleanup_ancient_inactive_agents(CURRENT_GENERATION)

        assert first["total_deleted"] == 2
        assert second["total_deleted"] == 0, "the second pass deleted again -- not idempotent"
        assert second["failures"] == 0, "the second pass raised: %r" % (second["failure_detail"],)
        assert manager.cleanup_failures == []
        assert not con.execute("PRAGMA foreign_key_check").fetchall()

    def test_dry_run_deletes_nothing_but_still_counts_the_eligible(self, tmp_path):
        con = _connect(tmp_path)
        stats = _manager(con).cleanup_ancient_inactive_agents(CURRENT_GENERATION, dry_run=True)
        assert stats["total_deleted"] == 0
        assert stats["zero_score_eligible"] == 2
        assert len(_ids(con, "agents")) == len(_AGENTS)


# --------------------------------------------------------------------------
# F3 -- the loud consumer, asserted BY IDENTITY
# --------------------------------------------------------------------------

class TestAFailingCleanupIsLoud:

    def test_f3_archive_failure_lands_on_the_named_consumer(self, tmp_path):
        """Inject a real failure (the archive table is gone) and assert the
        consumer recorded it. No stdout capture: the point of the fix is that
        the failure has a reader that is not a print."""
        con = _connect(tmp_path)
        con.execute("DROP TABLE agent_archive")
        con.commit()
        manager = _manager(con)

        stats = manager.cleanup_ancient_inactive_agents(CURRENT_GENERATION)

        assert manager.cleanup_failures, (
            "cleanup failed and `cleanup_failures` is EMPTY -- the exception was "
            "swallowed again, which is the defect this build exists to remove")
        assert len(manager.cleanup_failures) == 2
        assert {f["agent_id"] for f in manager.cleanup_failures} == {"ancient_a", "ancient_b"}
        assert all(f["phase"] == "archive" for f in manager.cleanup_failures)
        assert all(f["generation"] == CURRENT_GENERATION for f in manager.cleanup_failures)
        assert stats["failures"] == 2
        assert stats["failure_detail"] == manager.cleanup_failures

        assert stats["total_deleted"] == 0, "an agent that could not be archived was DELETED"
        assert _ids(con, "agents") >= {"ancient_a", "ancient_b"}

    def test_f3_delete_failure_lands_on_the_named_consumer(self, tmp_path, monkeypatch):
        """The historical failure itself: the delete path raises FOREIGN KEY.
        It must be recorded, the transaction must roll back, and nothing may be
        half-deleted."""
        import agent_lifecycle_manager as alm

        con = _connect(tmp_path)
        manager = _manager(con)

        def _boom(*_a, **_k):
            raise sqlite3.IntegrityError("FOREIGN KEY constraint failed")

        monkeypatch.setattr(alm, "_cascade_dependents", _boom)
        stats = manager.cleanup_ancient_inactive_agents(CURRENT_GENERATION)

        assert len(manager.cleanup_failures) == 1
        failure = manager.cleanup_failures[0]
        assert failure["phase"] == "delete"
        assert "FOREIGN KEY constraint failed" in failure["reason"]
        assert stats["failures"] == 1 and stats["total_deleted"] == 0
        assert _ids(con, "agents") == {a for a, _, _ in _AGENTS}, (
            "the failed purge left the agents table half-modified -- no rollback")

    def test_the_consumer_exists_before_anything_fails(self, tmp_path):
        """FIGURE 10: an instrument that only appears once something is wrong is
        a thing nobody can check the absence of a fault with."""
        con = _connect(tmp_path)
        manager = _manager(con)
        assert manager.cleanup_failures == []
        assert isinstance(manager.cleanup_failures, list)

    def test_the_runner_owns_a_run_level_counter(self):
        """The call site's `except` used to be `if self.verbose: print(...)`.
        Assert the counter it was replaced with exists on the runner by name."""
        tree = _runner_ast()
        swallowed = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "lifecycle_cleanup_failures"]
        assert len(swallowed) >= 3, (
            "the counter is referenced %d times -- it must be initialised, "
            "incremented on a returned failure count, and incremented on a "
            "raise" % len(swallowed))

    def test_the_swallow_cannot_come_back(self):
        """FIGURE 10, the whole point: this must be a bound something CAN
        violate. The defect was `except Exception: if self.verbose: print(...)`
        -- so the gate goes red if any handler that owns the lifecycle counter
        hides its report behind a flag again. Without this assertion the fix is
        a convention, which is the thing that failed for weeks."""
        handlers = [
            node for node in ast.walk(_runner_ast())
            if isinstance(node, ast.ExceptHandler)
            and any(isinstance(sub, ast.Attribute)
                    and sub.attr == "lifecycle_cleanup_failures"
                    for sub in ast.walk(node))]
        assert handlers, "no exception handler references the lifecycle failure counter"

        for handler in handlers:
            guards = [
                sub for sub in ast.walk(handler)
                if isinstance(sub, ast.If)
                and any(isinstance(test, ast.Attribute) and test.attr == "verbose"
                        for test in ast.walk(sub.test))]
            assert not guards, (
                "the lifecycle cleanup failure handler is gated on `self.verbose` "
                "again at line %d -- an exception whose only reader is a print "
                "behind a flag is the defect, not the report of it"
                % guards[0].lineno)


# --------------------------------------------------------------------------
# KNOWN NEGATIVE -- the real fleet condition, pinned rather than assumed
# --------------------------------------------------------------------------

class TestTierBehaviourUnderPermanentlyZeroFields:
    """`discovery_prestige` and `best_single_game_score` are 0 for all 28,892
    agents fleet-wide because NOTHING IN PRODUCTION WRITES EITHER. That is a
    separate finding and deliberately not fixed here -- so the tier behaviour it
    implies is pinned here instead of assumed."""

    def test_tier_one_takes_the_whole_ancient_inactive_set(self, tmp_path):
        con = _connect(tmp_path)
        stats = _manager(con).cleanup_ancient_inactive_agents(CURRENT_GENERATION, dry_run=True)
        assert stats["zero_score_eligible"] == 2

    def test_tiers_two_and_three_select_nobody_ever(self, tmp_path):
        con = _connect(tmp_path)
        stats = _manager(con).cleanup_ancient_inactive_agents(CURRENT_GENERATION, dry_run=True)
        assert stats["low_score_eligible"] == 0, (
            "tier 2 matched somebody -- it requires best_single_game_score > 0, "
            "which nothing writes")
        assert stats["good_player_eligible"] == 0, (
            "tier 3 matched somebody -- it requires best_single_game_score >= 1.0, "
            "which nothing writes")

    def test_the_tiers_are_not_dead_code_if_a_writer_ever_appears(self, tmp_path):
        """The falsifier: give one ancient agent a real score, open tier 2's
        window, and it wakes up. Proves the zero-selection above is the FIELD
        being zero and not the tier predicate being broken.

        Note the SECOND gate on tiers 2 and 3, found by this test failing first:
        their windows are 200 and 500 generations, so even with a writer they
        cannot fire before those generations regardless of score. Boxes have
        reached generations 190-446 -- tier 3 has never had an open window on
        any box on the fleet."""
        con = _connect(tmp_path)
        con.execute("UPDATE agents SET best_single_game_score = 0.5 WHERE agent_id = 'ancient_a'")
        con.commit()
        late = 600  # every tier window open: thresholds 550 / 400 / 100
        stats = _manager(con).cleanup_ancient_inactive_agents(late, dry_run=True)
        assert stats["low_score_eligible"] == 1, "tier 2 stayed empty with a scored agent in range"
        assert stats["zero_score_eligible"] == 2  # ancient_b and recent_inactive

    def test_tier_windows_cannot_open_before_their_generation(self, tmp_path):
        """Same fixture, same scored agent, at generation 100: tier 2 selects
        nobody because 100 - 200 is negative. The window, not the predicate."""
        con = _connect(tmp_path)
        con.execute("UPDATE agents SET best_single_game_score = 0.5 WHERE agent_id = 'ancient_a'")
        con.commit()
        stats = _manager(con).cleanup_ancient_inactive_agents(CURRENT_GENERATION, dry_run=True)
        assert stats["low_score_eligible"] == 0
        assert stats["zero_score_eligible"] == 1  # ancient_a moved out of tier 1

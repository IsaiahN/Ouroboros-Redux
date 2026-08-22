import os

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'  # Rule 1: Disable pycache

"""
Safe Agent Lifecycle Management

Implements "Megaman Net Navi" philosophy:
- Good players never deleted, just retired
- Zero-score agents pruned faster
- Permanent deletion only after 500+ generations of inactivity
- Agent data preserved for historical analysis

Author: Claude Code (Ouroboros System)
"""
import os

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from database_interface import DatabaseInterface

logger = logging.getLogger(__name__)

# The temp table the purge set lives in. A temp table (not an IN (?,?,...)
# list) because the eligible set is thousands of rows and SQLite's bound
# parameter limit is not a number this code should have to know.
_PURGE_SET = "_lifecycle_purge_set"

# Depth cap for the dependency walk. The measured schema is 3 deep
# (agents -> winning_sequences -> sequence_* -> ...); the cap exists so a
# cyclic schema fails LOUDLY at a named bound instead of recursing forever.
_MAX_CASCADE_DEPTH = 12


class AgentLifecycleManager:
    """
    Manage agent lifecycle from birth → retirement → eventual deletion.

    Philosophy: Net Navis should live their lives. Don't delete good players.
    """

    def __init__(self, db: DatabaseInterface):
        self.db = db

        # Lifecycle thresholds
        self.permanent_deletion_generations = 500  # Only delete after 500+ generations inactive
        self.zero_score_deletion_generations = 50  # Zero-score agents deleted faster
        self.good_player_threshold = 1.0  # Score >= 1.0 = completed at least one level

        # THE LOUD CONSUMER (FIGURE 10 / FIGURE 3).
        # For weeks this cleanup raised `FOREIGN KEY constraint failed` on every
        # single call and the ONLY reader of that exception was a print behind
        # `--verbose` in evolution_runner. An exception whose only consumer is a
        # debug print is not an instrument; the bound it was supposed to enforce
        # was a convention nothing could check. So every failure now lands HERE,
        # by identity, on a named attribute that exists whether or not anything
        # failed: a caller can assert on it, a test can assert on it, and the
        # runner reports its length unconditionally. Entries:
        #   {'agent_id', 'phase', 'reason', 'generation'}
        self.cleanup_failures: List[Dict[str, Any]] = []

    def retire_underperformers(self, generation: int, culling_config: Dict[str, Any]) -> Dict[str, int]:
        """
        Retire (deactivate) underperforming agents without deleting them.

        This is the normal evolutionary pressure mechanism.
        Agents stay in database for analysis/revival.

        Args:
            generation: Current generation
            culling_config: Configuration for culling (kept for compatibility)

        Returns:
            Dict with retirement stats
        """
        # This function is now a wrapper - actual retirement happens in evolutionary_engine
        # and autonomous_evolution_runner. This just tracks stats.

        with self.db._get_connection() as conn:
            # Count recently retired agents
            cursor = conn.execute("""
                SELECT COUNT(*)
                FROM agents
                WHERE generation = ? AND is_active = 0
            """, (generation,))

            retired_count = cursor.fetchone()[0]

            return {
                'retired': retired_count,
                'generation': generation,
                'permanent_deletions': 0  # Not done here
            }

    # The three deletion tiers, in the order they are applied. Kept as data so
    # the tier predicates are one object a test can assert against instead of
    # three near-identical SQL blocks that drift apart.
    #
    # KNOWN NEGATIVE, MEASURED (record/log/PORT_LOG.md, "FOREIGN KEY"): on the
    # real fleet `best_single_game_score` and `discovery_prestige` are 0 for
    # ALL 28,892 agents because nothing in production writes either. So tier 1
    # selects essentially every ancient inactive agent and tiers 2 and 3 select
    # NOBODY, ever. That is a separate finding (no writer) and is deliberately
    # NOT patched here; this cleanup is written to be correct given it.
    _DELETION_TIERS: Tuple[Tuple[str, str, str, str], ...] = (
        (
            'zero_score_deleted', 'zero_score',
            'zero_score_deletion_generations',
            """
                COALESCE(best_single_game_score, 0) = 0
                AND COALESCE(total_games_won, 0) = 0
                AND COALESCE(discovery_prestige, 0) < 10
            """,
        ),
        (
            'low_score_deleted', 'low_score',
            '_low_score_deletion_generations',
            """
                COALESCE(best_single_game_score, 0) > 0
                AND COALESCE(best_single_game_score, 0) < 1.0
                AND COALESCE(discovery_prestige, 0) < 50
            """,
        ),
        (
            'good_player_deleted', 'good_player',
            'permanent_deletion_generations',
            """
                COALESCE(best_single_game_score, 0) >= 1.0
                AND COALESCE(discovery_prestige, 0) < 100
            """,
        ),
    )

    _low_score_deletion_generations = 200  # tier 2 window (was inline)

    def cleanup_ancient_inactive_agents(self, current_generation: int, dry_run: bool = False) -> Dict[str, Any]:
        """
        Permanently delete ancient inactive agents.

        Deletion rules (safest possible):
        1. Zero-score agents: Deleted after 50 generations inactive
        2. Low-score agents (< 1.0): Deleted after 200 generations inactive
        3. Good players (>= 1.0): Deleted after 500 generations inactive
        4. High prestige agents: NEVER deleted (archived permanently)

        DISPOSITION: ARCHIVE, THEN CASCADE — and the cascade is READ FROM THE
        SCHEMA, not hardcoded. `agents.agent_id` is referenced by 54 foreign
        keys across 50 child tables on a real box DB, none of them declared
        `ON DELETE CASCADE`, so the bare `DELETE FROM agents` this method used
        to run threw `FOREIGN KEY constraint failed` every time it was called.

        The two alternatives were considered and REJECTED ON MEASUREMENT:
          * "delete only agents with no surviving children" — REFUTED: 0 of the
            2,459 eligible agents on the measured box are childless (every one
            has an `agent_operating_modes` row). It would delete nothing, which
            is indistinguishable from the defect it claims to fix.
          * "convert to a bounded SOFT delete" — REJECTED: it bounds nothing.
            The rows, and their 57,959 child rows, stay; the DB keeps growing;
            and it would turn a loud failure into a quiet no-op that REPORTS
            SUCCESS, which is strictly worse than the bug.

        Each child link is disposed of by what the SCHEMA ALREADY DECLARES
        about it (see `_fk_dependents`): a NOT NULL or primary-key reference
        means the row cannot exist without its agent — it is OWNED, and dies
        with the agent. A NULLABLE reference means the schema always intended
        the row to outlive the agent — it is ATTRIBUTION (`discovered_by_agent`,
        `created_by_agent`, `learned_from_agent`, ...) and is only RELEASED to
        NULL, so shared knowledge survives its discoverer. That rule is derived,
        not curated, so a table added tomorrow is handled without an edit here.

        The archive is what makes this safe, and the archive ITSELF was broken:
        `_archive_agent_knowledge` inserted into `agent_archive` columns
        (`agent_data`, `generation`) THAT HAVE NEVER EXISTED in the schema, and
        swallowed the resulting error into `logger.debug`. `agent_archive` holds
        0 rows fleet-wide. It is fixed here, and it is now STRICT: an agent that
        cannot be archived is NOT deleted.

        Args:
            current_generation: Current generation number
            dry_run: If True, only report what would be deleted

        Returns:
            Deletion statistics. `*_deleted` counts are ROWS ACTUALLY GONE, not
            rows selected — the old code reported the size of the SELECT, which
            read as success on every one of the runs that deleted nothing.
            FIGURE 1: these are frame-internal bookkeeping, never progress.
        """
        logger.info(f"[CLEANUP] Agent cleanup: Generation {current_generation}")

        failures_before = len(self.cleanup_failures)
        stats: Dict[str, Any] = {
            'zero_score_deleted': 0,
            'low_score_deleted': 0,
            'good_player_deleted': 0,
            'high_prestige_archived': 0,
            'total_deleted': 0,
            'zero_score_eligible': 0,
            'low_score_eligible': 0,
            'good_player_eligible': 0,
            'children_deleted': 0,
            'children_released': 0,
            'failures': 0,
            'failure_detail': [],
        }

        with self.db._get_connection() as conn:
            for stat_key, reason, window_attr, predicate in self._DELETION_TIERS:
                threshold = current_generation - getattr(self, window_attr)
                cursor = conn.execute(
                    "SELECT agent_id, generation, best_single_game_score, discovery_prestige "
                    "FROM agents WHERE is_active = 0 AND generation <= ? AND (" + predicate + ")",
                    (threshold,),
                )
                eligible = cursor.fetchall()
                stats[stat_key.replace('_deleted', '_eligible')] = len(eligible)

                if not dry_run and eligible:
                    stats[stat_key] = self._purge_agents(
                        conn, [row[0] for row in eligible], reason, current_generation, stats)

            # 4. Archive high-prestige agents (never delete)
            cursor = conn.execute("""
                SELECT COUNT(*)
                FROM agents
                WHERE is_active = 0
                    AND COALESCE(discovery_prestige, 0) >= 100
            """)

            stats['high_prestige_archived'] = cursor.fetchone()[0]

            stats['total_deleted'] = (
                stats['zero_score_deleted'] +
                stats['low_score_deleted'] +
                stats['good_player_deleted']
            )

        new_failures = self.cleanup_failures[failures_before:]
        stats['failures'] = len(new_failures)
        stats['failure_detail'] = new_failures

        # Logging. A dry run deletes nothing, so it must report what it SELECTED
        # -- reporting the deleted count (0) under --dry-run would be the same
        # confusion in the other direction as reporting the selected count after
        # a delete that never happened, which is what this method used to do.
        suffix = '_eligible' if dry_run else '_deleted'
        if dry_run:
            would_delete = (stats['zero_score_eligible'] + stats['low_score_eligible']
                            + stats['good_player_eligible'])
            logger.info(f"  [DRY RUN] Would delete {would_delete} agents:")
        else:
            logger.info(f"  Deleted {stats['total_deleted']} ancient agents "
                        f"({stats['children_deleted']} owned child rows deleted, "
                        f"{stats['children_released']} attribution references released):")

        logger.info(f"    Zero-score (50+ gen old): {stats['zero_score' + suffix]}")
        logger.info(f"    Low-score (200+ gen old): {stats['low_score' + suffix]}")
        logger.info(f"    Good players (500+ gen old): {stats['good_player' + suffix]}")
        logger.info(f"    High prestige archived: {stats['high_prestige_archived']} (NEVER deleted)")

        # The instrument, not a debug line: a cleanup that failed says so at
        # ERROR, every time, and the count rides out in the returned stats so
        # the runner can report it without reading a log.
        if stats['failures']:
            logger.error(
                "  [CLEANUP-FAILED] %d agent(s) could not be purged this pass "
                "(%d recorded on this manager in total); first: %r",
                stats['failures'], len(self.cleanup_failures), new_failures[0])

        return stats

    def _purge_agents(self, conn, agent_ids: Sequence[str], reason: str,
                      generation: int, stats: Dict[str, Any]) -> int:
        """
        Archive then delete `agent_ids`, cascading over the schema's own FK
        graph. Returns the number of `agents` rows ACTUALLY deleted.

        An agent whose archive fails is not deleted and is recorded on
        `self.cleanup_failures` — never archived into a delete that then fails,
        and never deleted without the archive that justified deleting it.
        """
        archived: List[str] = []
        for agent_id in agent_ids:
            try:
                self._archive_agent_knowledge(conn, agent_id)
                archived.append(agent_id)
            except Exception as exc:
                self.cleanup_failures.append({
                    'agent_id': agent_id, 'phase': 'archive',
                    'reason': f"{type(exc).__name__}: {exc}", 'generation': generation,
                })

        if not archived:
            return 0

        try:
            # Defer FK enforcement to COMMIT. This does NOT weaken the check --
            # a genuine orphan still fails, loudly, at commit time -- it removes
            # the cascade's sensitivity to intra-statement row order, which is
            # otherwise a correctness trap on self-referencing tables.
            conn.execute("PRAGMA defer_foreign_keys = ON")
            _fill_purge_set(conn, archived)
            row_filter = f'agent_id IN (SELECT agent_id FROM {_PURGE_SET})'
            released, deleted_children = _cascade_dependents(
                conn, _fk_dependents(conn), 'agents', row_filter)
            deleted = conn.execute(
                f"DELETE FROM agents WHERE {row_filter}").rowcount  # noqa: S608 - fixed identifiers
            conn.commit()
        except Exception as exc:
            conn.rollback()
            self.cleanup_failures.append({
                'agent_id': f'<{len(archived)} agents, tier={reason}>', 'phase': 'delete',
                'reason': f"{type(exc).__name__}: {exc}", 'generation': generation,
            })
            return 0

        stats['children_released'] += released
        stats['children_deleted'] += deleted_children
        logger.debug("  Purged %d %s agents (%d child rows deleted, %d released)",
                     deleted, reason, deleted_children, released)
        return deleted

    def _archive_agent_knowledge(self, conn, agent_id: str) -> None:
        """
        Archive agent's knowledge before deletion (Phase 2 of Biome Theory).

        Extracts and stores:
        - Agent metadata (genome, epigenetics, sensation profile)
        - Performance stats
        - Object control maps

        This ensures no knowledge is lost when agents die - their "genetic material"
        is released into the horizontal gene transfer pool.

        THIS METHOD HAS NEVER ARCHIVED ANYTHING. It inserted into `agent_archive`
        the columns `agent_data` and `generation`, and neither exists — not in
        `complete_database_schema.sql` and not in any box DB. Every call raised
        `no such column`, and every call swallowed it into `logger.debug`, which
        is the same genus as the FOREIGN KEY defect one frame up: raised-and-
        unread. `agent_archive` and `archived_agent_discoveries` both hold 0
        rows fleet-wide, while `manual_tools/utilities/revive_agents.py` has
        been reading `final_performance` out of that empty table the whole time.

        Fixed by writing the columns the schema ACTUALLY declares, and by
        RAISING: the caller records the failure on `self.cleanup_failures` and
        does not delete an agent it failed to archive. Neither archive table
        carries a foreign key to `agents` (verified against a box DB), so these
        rows survive the deletion that follows — which is what "archive before
        delete" was supposed to mean and never did.

        Args:
            conn: Database connection
            agent_id: Agent to archive

        Raises:
            sqlite3.Error: any archive failure. Never swallowed.
        """
        cursor = conn.execute("""
            SELECT agent_id, genome, epigenetics, sensation_profile,
                   generation, best_single_game_score, total_games_played,
                   total_games_won, discovery_prestige, social_rule_adherence
            FROM agents
            WHERE agent_id = ?
        """, (agent_id,))

        agent_data = cursor.fetchone()
        if not agent_data:
            return

        # The genetic material, as one JSON blob in the column the schema has
        # for exactly this (`reasoning_summary`).
        archive_data = {
            'genome': agent_data[1],
            'epigenetics': agent_data[2],
            'sensation_profile': agent_data[3],
            'generation': agent_data[4],
            'best_score': agent_data[5],
            'games_played': agent_data[6],
            'games_won': agent_data[7],
            'prestige': agent_data[8],
            'social_rule_adherence': agent_data[9],
        }

        conn.execute("""
            INSERT OR REPLACE INTO agent_archive
            (agent_id, archived_at, final_prestige, final_performance,
             reasoning_summary, sunset_reason, revival_candidate)
            VALUES (?, datetime('now'), ?, ?, ?, 'lifecycle_cleanup', 0)
        """, (agent_id, agent_data[8], agent_data[5], json.dumps(archive_data)))

        # Archive any object control maps this agent discovered
        conn.execute("""
            INSERT OR IGNORE INTO archived_agent_discoveries
            (agent_id, discovery_type, discovery_data, archived_at)
            SELECT agent_id, 'object_control',
                   json_object('game_id', game_id, 'level_number', level_number,
                               'controlled_objects', controlled_objects, 'confidence', confidence),
                   datetime('now')
            FROM agent_object_control
            WHERE agent_id = ?
        """, (agent_id,))

        logger.debug(f"  Archived knowledge for agent {agent_id[:12]}")

    def get_lifecycle_stats(self) -> Dict[str, Any]:
        """Get current agent lifecycle statistics."""

        with self.db._get_connection() as conn:
            # Active agents
            cursor = conn.execute("SELECT COUNT(*) FROM agents WHERE is_active = 1")
            active_count = cursor.fetchone()[0]

            # Retired agents (inactive but not deleted)
            cursor = conn.execute("SELECT COUNT(*) FROM agents WHERE is_active = 0")
            retired_count = cursor.fetchone()[0]

            # Retired by score category
            cursor = conn.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE COALESCE(best_single_game_score, 0) = 0) as zero_score,
                    COUNT(*) FILTER (WHERE COALESCE(best_single_game_score, 0) > 0 AND COALESCE(best_single_game_score, 0) < 1.0) as low_score,
                    COUNT(*) FILTER (WHERE COALESCE(best_single_game_score, 0) >= 1.0) as good_players,
                    COUNT(*) FILTER (WHERE COALESCE(discovery_prestige, 0) >= 100) as high_prestige
                FROM agents
                WHERE is_active = 0
            """)

            result = cursor.fetchone()

            return {
                'active_agents': active_count,
                'retired_agents': retired_count,
                'retired_breakdown': {
                    'zero_score': result[0],
                    'low_score': result[1],
                    'good_players': result[2],
                    'high_prestige': result[3]
                },
                'total_agents': active_count + retired_count
            }


# ---------------------------------------------------------------------------
# MODULE-BOTTOM HELPERS
#
# The cascade is DERIVED FROM THE SCHEMA, never enumerated here. A hand-written
# list of 50 child tables is a convention nothing can check (FIGURE 10): the day
# someone adds table 51, the list is silently wrong and `DELETE FROM agents`
# starts throwing FOREIGN KEY again — which is exactly how this defect survived
# for weeks. `PRAGMA foreign_key_list` is the instrument; these helpers read it.
# ---------------------------------------------------------------------------

def _fk_dependents(conn) -> Dict[str, List[Tuple[str, str, str, bool]]]:
    """
    Map every table to the rows that depend on it, read from the live schema.

    Returns `{parent_table: [(child_table, child_col, parent_col, owned), ...]}`.

    `owned` is the DISPOSITION, and it is not a judgement call — the schema
    already made it. A child column that is NOT NULL, or part of the child's
    primary key, cannot hold a row that outlives its parent: the row is OWNED
    and dies with it. A NULLABLE column is a reference the schema always
    allowed to be absent: it is ATTRIBUTION (measured, every one of them on a
    real box DB is a provenance column — `discovered_by_agent`,
    `created_by_agent`, `learned_from_agent`, `infected_by_agent`,
    `discovery_agent_id`, `source_agent_id`) and is released to NULL so the
    knowledge survives the knower.

    Raises:
        ValueError: an FK whose parent column cannot be resolved. Loud, because
            a link this code cannot read is a link it must not guess at.
    """
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]

    columns: Dict[str, Dict[str, Tuple[bool, bool]]] = {}
    sole_pk: Dict[str, Optional[str]] = {}
    for table in tables:
        info = list(conn.execute(f'PRAGMA table_info("{table}")'))
        columns[table] = {row[1]: (bool(row[3]), bool(row[5])) for row in info}
        keys = [row[1] for row in info if row[5]]
        sole_pk[table] = keys[0] if len(keys) == 1 else None

    dependents: Dict[str, List[Tuple[str, str, str, bool]]] = {}
    for table in tables:
        for row in conn.execute(f'PRAGMA foreign_key_list("{table}")'):
            parent, child_col, parent_col = row[2], row[3], row[4]
            if parent_col is None:
                parent_col = sole_pk.get(parent)
            if parent_col is None:
                raise ValueError(
                    f"foreign key {table}.{child_col} -> {parent} names no parent "
                    f"column and {parent} has no single-column primary key")
            not_null, is_pk = columns[table].get(child_col, (True, False))
            dependents.setdefault(parent, []).append(
                (table, child_col, parent_col, not_null or is_pk))
    return dependents


def _cascade_dependents(conn, dependents: Dict[str, List[Tuple[str, str, str, bool]]],
                        table: str, row_filter: str,
                        path: Optional[Set[str]] = None,
                        depth: int = 0) -> Tuple[int, int]:
    """
    Dispose of everything depending on `SELECT ... FROM table WHERE row_filter`,
    deepest dependents first. Returns `(rows_released, rows_deleted)`.

    Owned dependents are deleted (after their OWN dependents), attribution
    references are set to NULL. `row_filter` is composed, not parameterised:
    each level nests the level above it as a subquery, so the placeholder count
    never changes and the caller's params still bind. Callers pass a filter
    over a temp purge set, so in practice there are no placeholders at all.

    Raises:
        RuntimeError: the schema is deeper than `_MAX_CASCADE_DEPTH`. A cap
            that raises, rather than a recursion that hangs or a skip that
            silently orphans.
    """
    if depth > _MAX_CASCADE_DEPTH:
        raise RuntimeError(
            f"dependency walk exceeded depth {_MAX_CASCADE_DEPTH} at {table!r}: "
            "the schema is cyclic or deeper than this cascade was built for")

    seen: Set[str] = set(path or ()) | {table}
    released = deleted = 0

    for child, child_col, parent_col, owned in dependents.get(table, ()):
        # noqa: S608 throughout - every identifier here comes from sqlite_master
        # and PRAGMA output, i.e. from the schema itself, never from input.
        predicate = (f'"{child_col}" IN '
                     f'(SELECT "{parent_col}" FROM "{table}" WHERE {row_filter})')

        if not owned:
            released += conn.execute(
                f'UPDATE "{child}" SET "{child_col}" = NULL WHERE {predicate}'  # noqa: S608
            ).rowcount
            continue

        if child not in seen:
            sub_released, sub_deleted = _cascade_dependents(
                conn, dependents, child, predicate, seen, depth + 1)
            released += sub_released
            deleted += sub_deleted
        # A cyclic/self-referencing owned link is disposed of at this level
        # WITHOUT descending. It is not skipped: if the resulting statement
        # leaves a dangling reference, the deferred FK check fails at COMMIT
        # and the caller records it. Silence is the one option not taken.
        deleted += conn.execute(
            f'DELETE FROM "{child}" WHERE {predicate}'  # noqa: S608
        ).rowcount

    return released, deleted


def _fill_purge_set(conn, agent_ids: Sequence[str]) -> None:
    """
    Load the agents to purge into a temp table.

    A temp table rather than `IN (?, ?, ...)` because the eligible set runs to
    thousands of rows on a real box and SQLite's bound-parameter ceiling is not
    a number this cleanup should have to know or silently truncate against.
    """
    conn.execute(f"CREATE TEMP TABLE IF NOT EXISTS {_PURGE_SET} (agent_id TEXT PRIMARY KEY)")
    conn.execute(f"DELETE FROM {_PURGE_SET}")  # noqa: S608 - fixed identifier
    conn.executemany(
        f"INSERT OR IGNORE INTO {_PURGE_SET} (agent_id) VALUES (?)",  # noqa: S608
        [(agent_id,) for agent_id in agent_ids])


if __name__ == "__main__":
    """Test lifecycle management"""

    db = DatabaseInterface()
    manager = AgentLifecycleManager(db)

    # Get current stats
    stats = manager.get_lifecycle_stats()

    print("=" * 80)
    print("AGENT LIFECYCLE STATS")
    print("=" * 80)
    print(f"Active agents: {stats['active_agents']:,}")
    print(f"Retired agents: {stats['retired_agents']:,}")
    print(f"Total agents: {stats['total_agents']:,}")
    print()
    print("Retired breakdown:")
    print(f"  Zero-score: {stats['retired_breakdown']['zero_score']:,}")
    print(f"  Low-score: {stats['retired_breakdown']['low_score']:,}")
    print(f"  Good players: {stats['retired_breakdown']['good_players']:,}")
    print(f"  High prestige (archived): {stats['retired_breakdown']['high_prestige']:,}")
    print()

    # Check what would be deleted
    cursor = db.execute_query("SELECT MAX(generation) FROM agents")
    current_gen = cursor[0]['MAX(generation)'] if cursor else 0

    print(f"Current generation: {current_gen}")
    print()
    print("Checking cleanup eligibility (DRY RUN)...")
    cleanup_stats = manager.cleanup_ancient_inactive_agents(current_gen, dry_run=True)
    print("=" * 80)

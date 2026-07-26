"""
test_shared_gamma.py -- Γ SHARED ACROSS GAMES, and the four ways that could be a lie.

The previous beat measured the carrier before wiring it: `keys_minted_on_2plus_games = 1` (`INTENDED_FREE`, minted
independently on re86 and wa30). So a shared library has one live instance to promote, and wiring it is no longer
speculative library growth. What sharing buys is exactly one thing -- the strongest transfer claim the chain can
make, a φ minted on game A explaining a residual on game B, which was STRUCTURALLY unreachable while Γ was
per-policy. What it risks is four things, and each has a test here that must fail if the risk lands:

  (1) A LOWERED BAR. Sharing widens WHO can echo. It must not change HOW EASILY: still two DISTINCT tasks, still
      one task credited per mint. A shared Γ that also relaxed the threshold would fill from noise.
  (2) A LAUNDERED ATTEMPT. `reuse_attempted` goes True the moment Γ is non-empty for ANY reason -- including a Γ
      filled entirely by THIS game. That is a real within-game transfer test, but it is not what sharing was built
      for, and reporting it as though it were would let a shared library that never crossed a game boundary read
      exactly like one that did. Hence `reuse_attempted_foreign`, counted separately, never folded in.
  (3) AN ACCIDENTAL ARCHITECTURE VERDICT. MINTED_UNUSED is the only stage code that indicts the tether. It becomes
      reachable the instant Γ is non-empty, and a shared Γ is non-empty far more often. It must still require a
      real offer on real play -- never an empty library, never a cross-test leak.
  (4) A RACE. The swarm runs eight games concurrently in one process against ONE Γ now. Two threads promoting the
      same φ would double-count `promoted` and duplicate the library entry: a measurement corrupted by scheduling.

Nothing here is a claim that the tether fired. Γ filling and Γ being OFFERED are upstream of a firing, and a test
that a library exists is not evidence that anything transferred.
"""
from __future__ import annotations

import subprocess
import threading

import numpy as np

from newhorse.redux_arch import policy as policy_mod
from newhorse.redux_arch.consolidate import Consolidator
from newhorse.redux_arch.dsl import Context, Predicate, make_atom
from newhorse.redux_arch.minting import Mint
from newhorse.redux_arch.policy import ReduxPolicy
from newhorse.redux_arch.receipt import ResidualEvent, game_of, summary, task_id

PHI = Predicate(frozenset({make_atom("INTENDED_FREE")}))
PSI = Predicate(frozenset({make_atom("INTENDED_COLOUR", 4)}))


def _ctx(free: bool, colour: int = 4) -> Context:
    return Context(focus_rc=(2, 2), focus_colour=colour, target_rc=(5, 5), action_vec=(0, 1),
                   intended_free=free, intended_colour=(None if free else colour))


def _mixed(n: int = 8):
    """A residual with MIXED outcomes -- the precondition `_residual_pass` tests before doing anything at all."""
    return [(_ctx(i % 2 == 0), i % 2 == 0) for i in range(n)]


def _armed(gid: str) -> ReduxPolicy:
    pol = ReduxPolicy(game_id=gid)
    pol.cursor, pol.vecs, pol.passable, pol.stride = 7, {"RIGHT": (0, 1)}, {0}, 1
    for _ in range(4):
        pol.frames.append(np.zeros((5, 5), dtype=int))
        pol.acts.append("RIGHT")
        pol.chain.note_step()
    return pol


def _drive(monkeypatch, gid: str, mint, exc=None):
    """Run ONE break event on `gid` with the residual and mint forced, so the test controls exactly which game
    mints what. The wiring under test is the call ORDER inside `_residual_pass` -- offer, then mint, then bank --
    which is what the forced values leave intact."""
    pol = _armed(gid)
    monkeypatch.setattr(policy_mod, "transition_residual",
                        lambda *a, **k: list(exc if exc is not None else _mixed()))
    monkeypatch.setattr(policy_mod, "two_part_mdl", lambda e, max_size=2, report=None: mint)
    pol._close_segment("death")
    return pol, pol.receipts[-1]


# ---- (1) the bar is unchanged -------------------------------------------------------------------------------

def test_two_DIFFERENT_games_can_now_promote_one_phi_which_was_impossible_before():
    """The whole point, stated as the thing that used to be unreachable. Two policies, two game ids, one φ each --
    under a per-policy Γ neither library ever sees the other's mint and `promoted` stays 0 forever."""
    a, b = ReduxPolicy(game_id="re86-aaa"), ReduxPolicy(game_id="wa30-bbb")
    assert a.echo is b.echo, "Γ must be the SAME object across policies or nothing below means anything"
    first = a.echo.observe_mint(task_id("re86-aaa", 0, 0), Mint(predicate=PHI, saved_bits=9.0, support=8))
    second = b.echo.observe_mint(task_id("wa30-bbb", 0, 0), Mint(predicate=PHI, saved_bits=9.0, support=8))
    assert first is False, "one task cannot promote itself -- the echo bar is TWO distinct tasks"
    assert second is True, "the second GAME's independent mint is the echo"
    assert a.echo.echo_games(PHI) == ["re86-aaa", "wa30-bbb"]
    assert len(a.echo.library) == 1 and len(b.echo.library) == 1, "one φ, one entry, seen by both"


def test_sharing_widens_WHO_can_echo_never_HOW_EASILY():
    """The bar must be untouched by sharing. The same task minting the same φ twice is ONE task, shared Γ or not --
    if this ever promotes, the library will fill from repetition instead of from recurrence."""
    c = Consolidator(echo_threshold=2)
    tid = task_id("re86-aaa", 0, 3)
    assert c.observe_mint(tid, Mint(predicate=PHI, saved_bits=9.0, support=8)) is False
    assert c.observe_mint(tid, Mint(predicate=PHI, saved_bits=9.0, support=8)) is False
    assert c.library == [] and c.echo_tasks(PHI) == [tid]


def test_echo_games_does_not_read_four_segments_of_one_game_as_cross_game():
    """`echo_tasks` counts TASKS and a within-game run produces many. Judged by task count a shared Γ would look
    like it had crossed games on the strength of one game replaying itself."""
    c = Consolidator(echo_threshold=2)
    for seg in range(4):
        c.observe_mint(task_id("ka59-zzz", 0, seg), Mint(predicate=PHI, saved_bits=9.0, support=8))
    assert len(c.echo_tasks(PHI)) == 4
    assert c.echo_games(PHI) == ["ka59-zzz"], "four tasks, ONE game -- the transfer claim is within-game"


# ---- (2) a same-game library is not a cross-game one ---------------------------------------------------------

def test_foreign_is_the_librarys_real_size_for_a_game_and_ignores_its_own_phi():
    c = Consolidator(echo_threshold=2)
    for seg in (0, 1):                                          # ka59 promotes PSI by itself, across segments
        c.observe_mint(task_id("ka59-zzz", 0, seg), Mint(predicate=PSI, saved_bits=9.0, support=8))
    for g in ("re86-aaa", "wa30-bbb"):                          # PHI crosses two games
        c.observe_mint(task_id(g, 0, 0), Mint(predicate=PHI, saved_bits=9.0, support=8))
    assert len(c.library) == 2
    assert [str(p) for p in c.foreign("ka59-zzz")] == [str(PHI)], "its own PSI is not a transfer opportunity"
    assert sorted(str(p) for p in c.foreign("sp80-qqq")) == sorted([str(PHI), str(PSI)]), "an outsider sees both"
    assert c.foreign("re86-aaa") == [p for p in c.library if str(p) == str(PSI)]


def test_an_offer_from_a_gamma_this_game_filled_alone_is_NOT_counted_as_foreign(monkeypatch):
    """THE ANTI-LAUNDERING TEST. The offer still happens and `reuse_attempted` is still True -- a within-game echo
    is a real transfer across tasks. But `reuse_attempted_foreign` must stay False, or a shared Γ that never
    crossed a game boundary reports identically to one that did, and the undo below can never fire."""
    mint = Mint(predicate=PSI, saved_bits=9.0, support=8)
    for seg in range(2):                                        # ONE game fills Γ by itself
        policy_mod.SHARED_ECHO.observe_mint(task_id("ka59-zzz", 0, seg), mint)
    assert len(policy_mod.SHARED_ECHO.library) == 1
    _, ev = _drive(monkeypatch, "ka59-zzz", None)
    assert ev.reuse_attempted is True, "a non-empty Γ is still offered the residual"
    assert ev.library_size_before == 1 and ev.library_foreign_before == 0
    assert ev.reuse_attempted_foreign is False, "same-game φ is not a cross-game offer"


def test_an_offer_of_another_games_phi_IS_counted_as_foreign(monkeypatch):
    mint = Mint(predicate=PHI, saved_bits=9.0, support=8)
    for g in ("re86-aaa", "wa30-bbb"):
        policy_mod.SHARED_ECHO.observe_mint(task_id(g, 0, 0), mint)
    _, ev = _drive(monkeypatch, "sp80-qqq", None)
    assert ev.reuse_attempted and ev.reuse_attempted_foreign
    assert ev.library_foreign_before == 1


def test_the_pooled_summary_never_folds_foreign_offers_into_the_attempt_total():
    evs = [ResidualEvent(diff_ran=True, residual_nonempty=True, reuse_attempted=True, reuse_attempted_foreign=False),
           ResidualEvent(diff_ran=True, residual_nonempty=True, reuse_attempted=True, reuse_attempted_foreign=True)]
    s = summary(evs)
    assert s["reuse_attempted"] == 2 and s["reuse_attempted_foreign"] == 1


# ---- (3) the architecture verdict stays unreachable by bookkeeping -------------------------------------------

def test_an_empty_gamma_is_still_not_an_attempt_however_shared_it_is(monkeypatch):
    """MINTED_UNUSED is the only code that indicts the tether. Offering a residual to an EMPTY library and calling
    it an attempt would manufacture that verdict out of wiring. Sharing must not weaken this by one line."""
    assert policy_mod.SHARED_ECHO.library == []
    _, ev = _drive(monkeypatch, "re86-aaa", Mint(predicate=PHI, saved_bits=9.0, support=8))
    assert ev.minted is True
    assert ev.reuse_attempted is False and ev.reuse_attempted_foreign is False
    assert ev.stage == "REUSE_UNWIRED", "minted with nothing to offer is a WIRING report, not an architecture one"


def test_gamma_is_rebuilt_from_live_play_and_never_persisted(tmp_path, monkeypatch):
    """Γ holds CONCLUSIONS. The residual bank persists because it holds EVIDENCE that must still pass the mint
    gate; a conclusions-store that accumulates across builder runs is an answer key with a slow fuse -- one bad
    promotion outlives every run that could have overturned it. So Γ must own no path and write nothing."""
    monkeypatch.chdir(tmp_path)
    before = set(p.name for p in tmp_path.iterdir())
    for g in ("re86-aaa", "wa30-bbb"):
        policy_mod.SHARED_ECHO.observe_mint(task_id(g, 0, 0), Mint(predicate=PHI, saved_bits=9.0, support=8))
    assert policy_mod.SHARED_ECHO.library, "the promotion really happened"
    assert set(p.name for p in tmp_path.iterdir()) == before, "Γ wrote something to disk"
    assert not any(hasattr(policy_mod.SHARED_ECHO, a) for a in ("root", "path", "file")), "Γ must own no location"


def test_reset_exists_for_tests_only_and_has_no_call_site_in_the_build():
    """A Γ the agent can clear is a Γ the agent can launder: drop the promotions that would have been offered on a
    fresh task and every stall drops back from MINTED_UNUSED to REUSE_UNWIRED -- an architecture verdict deleted by
    housekeeping. The grep is the enforcement, exactly as for the bank's evidence-not-conclusions rule."""
    out = subprocess.run(["grep", "-rn", "SHARED_ECHO.reset\\|echo.reset", "src"],
                         capture_output=True, text=True, cwd=_repo_root())
    assert out.stdout.strip() == "", "Γ.reset() must never be called from the build:\n%s" % out.stdout


def _repo_root() -> str:
    import os
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---- (4) the race ------------------------------------------------------------------------------------------

def test_concurrent_mints_of_one_phi_promote_exactly_once():
    """The swarm runs eight games at once against ONE Γ. Unguarded, two threads can both read len(seen) before
    either writes and BOTH return True: a duplicate library entry and a doubled `promoted` count -- a measurement
    corrupted by scheduling, which is worse than a low measurement."""
    c = Consolidator(echo_threshold=2)
    promotions, lock = [], threading.Lock()
    start = threading.Event()

    def worker(i: int) -> None:
        start.wait()
        got = c.observe_mint(task_id("g%02d" % i, 0, 0), Mint(predicate=PHI, saved_bits=9.0, support=8))
        with lock:
            promotions.append(got)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
    for t in threads:
        t.start()
    start.set()
    for t in threads:
        t.join()
    assert sum(1 for p in promotions if p) == 1, "exactly one call may report the promotion"
    assert len(c.library) == 1, "and Γ holds exactly one copy of φ"
    assert len(c.echo_games(PHI)) == 16


def test_explains_tolerates_gamma_growing_underneath_it():
    """A transfer verdict must not depend on thread scheduling. `explains_scored` snapshots the library; without
    that, another game appending mid-iteration is undefined behaviour on the list it is scoring."""
    c = Consolidator(echo_threshold=2)
    for g in ("re86-aaa", "wa30-bbb"):
        c.observe_mint(task_id(g, 0, 0), Mint(predicate=PHI, saved_bits=9.0, support=8))
    stop = threading.Event()

    def churn() -> None:
        i = 0
        while not stop.is_set():
            c.observe_mint(task_id("noise%03d" % i, 0, 0), Mint(predicate=PSI, saved_bits=9.0, support=8))
            i += 1

    t = threading.Thread(target=churn, daemon=True)
    t.start()
    try:
        for _ in range(200):
            c.explains_scored(_mixed(12))                      # must never raise
    finally:
        stop.set()
        t.join(timeout=5)


# ---- the id format lives in ONE place ------------------------------------------------------------------------

def test_game_of_is_the_only_thing_that_knows_the_task_id_shape():
    """`echo_games`, the swarm's carrier-reach pool and `echo_kind` all need the game out of a task id. Three
    copies of the format is how a later change to `task_id` silently turns a cross-game count into a within-game
    one while every test still passes."""
    assert game_of(task_id("re86-aaa", 3, 7)) == "re86-aaa"
    assert game_of(task_id("re86-aaa", 3, 7, stream="rho")) == "re86-aaa", "the stream must not ride in the game"
    # `answer_lint` is excluded BY NAME and for a stated reason: it splits on "#" to strip a PYTHON COMMENT from a
    # source line, which has nothing to do with the task-id format. An exclusion without its reason written down is
    # how a real violation gets hidden behind a plausible one.
    out = subprocess.run(["grep", "-rn", "--exclude=answer_lint.py", 'split("#"', "src"],
                         capture_output=True, text=True, cwd=_repo_root())
    assert out.stdout.strip() == "", "a second parser of the task-id format reappeared:\n%s" % out.stdout

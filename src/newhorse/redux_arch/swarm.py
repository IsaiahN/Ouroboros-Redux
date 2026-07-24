"""
swarm.py -- redux-triality: run ONE ReduxPolicy per game across MANY games at once, the way the eval harness does
(agents/swarm.py: one agent per game, one shared scorecard, per-thread). Two things the official swarm does NOT
give us and we add here:
  * a SHARED global rate limiter -- the 600 RPM/key cap is shared across all games, so N per-session throttles would
    blow it; RateLimiter serialises the wire so the aggregate stays under the cap (swarm keeps the fixed pipe FULL,
    it does not raise it), and
  * a SHARED Blackboard -- cross-game transfer (a family/mechanism recognised on one game seeds the next), which
    the official swarm has no mechanism for.

Wall-clock is NOT multiplied by threads (RPM is the ceiling); the swarm's win is keeping the pipe saturated and
overlapping the FREE deliberation of hard games with the cheap acting of easy ones. RHAE: thinking is free.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Callable
import os
import time
import threading
import random
from .policy import ReduxPolicy, Blackboard


class RateLimiter:
    """Thread-safe global spacer: every acquire() reserves the next 1/rpm slot, so calls across ALL threads stay
    under `rpm` requests/min in aggregate (the ARC-AGI-3 per-key cap is 600 RPM -- default 540 leaves headroom)."""

    def __init__(self, rpm: int = 540):
        self.interval = 60.0 / max(1, int(rpm))
        self._lock = threading.Lock()
        self._next = 0.0

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            t = now if now >= self._next else self._next
            self._next = t + self.interval
            wait = t - now
        if wait > 0:
            time.sleep(wait)


def _play_policy(session, blackboard: Blackboard, game_id: str, max_actions: int, wall_cap_s: float,
                 open_retries: int = 6, open_backoff: float = 1.5) -> Dict[str, Any]:
    """Drive one ReduxPolicy through one (already-constructed) session to completion. Session is duck-typed on the
    Arc3Session interface: open()/step(val, data=)/close() returning snapshot dicts. Shared blackboard for transfer.
    open() is retried with EXPONENTIAL, JITTERED backoff: under swarm concurrency the reset can transiently
    500/return-None, and un-jittered retries re-collide in lockstep -- the swarm-L run lost m0r0 to exactly this.
    Jitter de-correlates concurrent retries so a game is not silently dropped from the scorecard."""
    log: List[str] = []
    try:
        snap = None; last = None
        for attempt in range(max(1, open_retries)):
            try:
                snap = session.open(); break
            except Exception as e:                          # transient server 500 / None reset under concurrency
                last = e
                if open_backoff:                            # exp backoff (cap 12s) + jitter to break lockstep
                    time.sleep(min(12.0, open_backoff * (2 ** attempt)) * (0.5 + random.random()))
        if snap is None:
            return dict(game=game_id, family="error", levels=0, steps=0,
                        outcome="open_error:%s" % (type(last).__name__ if last else "none"), log=log)
        pol = ReduxPolicy(game_id=game_id, blackboard=blackboard, warmup_cap=8)
        can_retry = hasattr(session, "reset_after_death")   # live sessions retry after death; simple fakes may not
        retry_cap = 6
        best = snap["levels_completed"]; t0 = time.time(); steps = 0; outcome = "action_cap"; retries = 0
        while steps < max_actions and (time.time() - t0) < wall_cap_s:
            pol.observe(snap["grid"], snap["available"], snap["levels_completed"], state=snap.get("state"))
            if snap["done"]:
                if snap["state"] == "WIN":
                    outcome = "WIN"; break
                # §XIX: retry ONLY if the reset is EARNED (death taught a NEW avoidable cause)
                earned, why = pol.reset_earned()
                if not can_retry or not earned or retries >= retry_cap:
                    outcome = "GAME_OVER"; log.append("no RESET (earned=%s): %s" % (earned, why)); break
                retries += 1; steps += 1
                log.append("EARNED RESET #%d @%d: %s" % (retries, steps, why))
                snap = session.reset_after_death(reasoning={"why": why, "reset_earned": True})
                pol.note_reset()
                continue
            lbl, data = pol.choose()
            prev = snap["levels_completed"]
            snap = session.step(int(lbl[1:]), data=data)
            if snap["levels_completed"] > prev:
                log.append("LEVEL UP %d->%d @%d" % (prev, snap["levels_completed"], steps))
            best = max(best, snap["levels_completed"]); steps += 1
        return dict(game=game_id, family=pol.family, levels=best, steps=steps, outcome=outcome,
                    view_url=getattr(session, "view_url", None), log=log,
                    deaths=pol.n_deaths, retries=retries, vetoes=pol.n_vetoes)
    except Exception as e:                                   # one game's failure must not sink the swarm
        return dict(game=game_id, family="error", levels=0, steps=0, outcome="error:%s" % type(e).__name__, log=log)
    finally:
        try:
            session.close()
        except Exception:
            pass


def run_swarm(game_ids: List[str], max_actions: int = 60, wall_cap_s: float = 150.0, rpm: int = 540,
              max_workers: int = 8, blackboard: Optional[Blackboard] = None, tags: Optional[List[str]] = None,
              session_factory: Optional[Callable[..., Any]] = None, start_stagger_s: float = 0.6,
              open_backoff: float = 1.5) -> Dict[str, Any]:
    """Run ReduxPolicy across many games concurrently under ONE shared scorecard + rate limiter + blackboard.
    `session_factory(game_id, scorecard_id=, limiter=)` is injectable for offline tests; default = live Arc3Session.
    Returns {view_url, scorecard_id, results{game->dict}, families, blackboard_prefixes}."""
    bb = blackboard if blackboard is not None else Blackboard()
    limiter = RateLimiter(rpm)
    card_id: Optional[str] = None
    view_url: Optional[str] = None
    arc = None

    if session_factory is None:
        from .sdk_guard import assert_online_sdk
        assert_online_sdk()                                  # fail loud on wrong interpreter/SDK before live swarm
        import arc_agi
        try:
            from arc_agi.base import OperationMode
        except Exception:                                    # pragma: no cover - SDK layout drift
            from arc_agi import OperationMode
        key = os.environ.get("ARC_API_KEY", "")
        if not key:
            raise RuntimeError("ARC_API_KEY not set -- env-only")
        arc = arc_agi.Arcade(operation_mode=OperationMode.ONLINE, arc_api_key=key)
        card_id = arc.open_scorecard(tags=tags or ["redux-triality", "swarm"])
        view_url = "https://arcprize.org/scorecards/%s" % card_id
        from ..arc3_env import Arc3Session

        def session_factory(gid, scorecard_id=None, limiter=None):   # noqa: overrides the None default
            return Arc3Session(gid, scorecard_id=scorecard_id, limiter=limiter,
                               tags=(tags or ["redux-triality", "swarm"]) + [gid])

    results: Dict[str, Any] = {}
    rlock = threading.Lock()
    sem = threading.Semaphore(max(1, int(max_workers)))

    def play(gid: str) -> None:
        with sem:
            try:
                session = session_factory(gid, scorecard_id=card_id, limiter=limiter)
            except Exception as e:
                with rlock:
                    results[gid] = dict(game=gid, family="error", levels=0, steps=0,
                                        outcome="open_error:%s" % type(e).__name__)
                return
            r = _play_policy(session, bb, gid, max_actions, wall_cap_s, open_backoff=open_backoff)
            with rlock:
                results[gid] = r

    threads = [threading.Thread(target=play, args=(g,), daemon=True) for g in game_ids]
    for i, t in enumerate(threads):
        t.start()
        if start_stagger_s and i + 1 < len(threads):        # stagger opens: session make()/reset bypasses the
            time.sleep(start_stagger_s)                     # limiter, so a simultaneous burst trips server 500s
    for t in threads:
        t.join(timeout=wall_cap_s + 60)

    if arc is not None and card_id is not None:
        try:
            arc.close_scorecard(card_id)
        except Exception:
            pass

    families = {g: r.get("family") for g, r in results.items()}
    return dict(view_url=view_url, scorecard_id=card_id, results=results, families=families,
                blackboard_prefixes=sorted({g.split("-")[0] for g in results}),
                total_levels=sum(int(r.get("levels", 0)) for r in results.values()))

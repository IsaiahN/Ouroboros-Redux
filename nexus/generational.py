"""nexus.generational -- the fusion: one agent, many lifetimes, over a run-local ledger.

Economy of THOUGHT (within a lifetime): ReduxPolicy's hypotheses compete, priced by prediction error.
Economy of AGENTS (across lifetimes): on GAME_OVER the run RESETS into a new generation, but the SAME
policy instance persists (its falsified ledger + hypotheses carry over) and the JSON RunLedger records
what was refuted -- so generation N+1 never re-spends what N proved dead. Compounding, not thrash.

This is the offline reconstruction of v4's generations without an external database (Isaiah, 2026-08-02):
the ledger is the mutable shared reference; reset is the generation boundary. One game per agent, so a
swarm gives each game its own independent 9-hour run (parallelism, NOT cross-game transfer).

Pure over the session interface (open/step/reset_after_death/close), so it runs offline against a
FakeSession with no key or network. `run_online(game_id, ...)` is the thin live entry.
"""
from __future__ import annotations
import time
from typing import Any, Dict, Optional
from .ledger import RunLedger
from .reasoning import decision_reasoning, compact_why
from .reset_policy import ResetPolicy
from .verdict import VerdictCircuit, classify


def _board_hash(grid) -> int:
    try:
        return hash(grid.tobytes())
    except Exception:
        return hash(str(grid))


def apply_fatal_veto(cur_board, lbl, data, available, fatal_moves):
    """The learned-fatal veto ACROSS resets (the 'return-to-start apply the veto' primitive ls20 asked
    for). If the policy is about to repeat a (board, action) a past lifetime recorded as fatal, and a
    non-fatal directional alternative exists, override to it. Returns (lbl, data, avoided_or_None).

    Scoped to no-data (directional) actions: a click's fatal unit is (board, coord), and picking an
    alternative coordinate is the policy's job, so click fatals are recorded but not overridden here."""
    if data:
        return lbl, data, None
    if (cur_board, lbl) not in fatal_moves:
        return lbl, data, None
    alts = ["A%d" % v for v in available if int(v) != 6]
    fresh = [a for a in alts if a != lbl and (cur_board, a) not in fatal_moves]
    if fresh:
        return fresh[0], None, lbl        # vetoed lbl -> a non-fatal alternative
    return lbl, data, None                # every alternative is also fatal / none available -> forced


class GenerationalRunner:
    def __init__(self, run_dir: str = "/tmp/nexus_runs"):
        self.run_dir = run_dir

    def run(self, session, game_id: str, *, max_generations: int = 20, hard_cap: int = 500,
            stall_patience: int = 60, unearned_patience: int = 3, wall_cap_s: float = 3600.0,
            blackboard=None, run_tag: str = "", now=time.time) -> Dict[str, Any]:
        import sys, os
        src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from newhorse.redux_arch.policy import ReduxPolicy

        led = RunLedger(game_id, self.run_dir, run_tag=run_tag)
        pol = ReduxPolicy(game_id=game_id, blackboard=blackboard, warmup_cap=8)  # ONE agent across generations
        rp = ResetPolicy(base_patience=stall_patience, hard_cap=hard_cap)         # reset boundary is game-natural
        snap = session.open()
        best = snap.get("levels_completed", 0)
        t0 = now(); total_steps = 0; outcome = "budget"; gen = 0; payload = None
        circuit = VerdictCircuit()          # the closed price->generation loop, carried ACROSS lifetimes
        consecutive_unearned = 0            # deaths that taught nothing new (kernel §XIX)
        try:
            for gen in range(max_generations):
                led.start_generation(gen)
                seen = set(); life_steps = 0; since_progress = 0; prev_best = best; reason = None
                while (now() - t0) < wall_cap_s:
                    pol.observe(snap["grid"], snap["available"], snap.get("levels_completed", 0),
                                state=snap.get("state"))
                    reason = rp.lifetime_over(done=bool(snap.get("done")), state=snap.get("state"),
                                              steps_in_life=life_steps, steps_since_progress=since_progress)
                    if reason == "win":
                        outcome = "WIN"; led.flush()
                        return self._result(game_id, best, gen, total_steps, outcome, led, session)
                    if reason:                                    # death / stall / cap -> end this lifetime
                        if reason == "death":
                            earned, why = pol.reset_earned()      # GAME_OVER: what killed us (a receipt)
                            led.record_death(gen, total_steps, why)
                            if why:
                                led.record_refuted(why)
                            # FIX 1 (§XIX): an unearned death taught nothing new; do not reset-and-repeat
                            # into the same trap. Stop the game once the agent is provably stuck.
                            consecutive_unearned = 0 if earned else consecutive_unearned + 1
                            if consecutive_unearned >= unearned_patience:
                                outcome = "stuck"
                                led.record_generation_end(gen, "stuck", life_steps,
                                                          {"consecutive_unearned": consecutive_unearned})
                                led.flush()
                                return self._result(game_id, best, gen, total_steps, outcome, led, session)
                        break
                    lbl, data = pol.choose()
                    cur_board = _board_hash(snap["grid"])
                    # CLOSED LOOP: shape this proposal from ALL prior ground verdicts -- refute vetoes,
                    # mute routes to empowerment, confirm is preferred. Sync pol._pending on override so
                    # the policy attributes the next frame to what was actually emitted.
                    lbl, data, shaped = circuit.shape(cur_board, lbl, data, snap.get("available", []))
                    if shaped is not None:
                        try:
                            pol._pending = lbl; pol._pending_rc = None
                        except Exception:
                            pass
                    payload = decision_reasoning(pol, lbl, data, total_steps, gen)
                    if shaped is not None:
                        payload["shaped"] = shaped                # e.g. "veto:refuted->A1" / "empower:mute->A2"
                    prev = snap.get("levels_completed", 0)
                    snap = session.step(int(lbl[1:]), data=data,
                                        reasoning={"why": compact_why(payload), **payload})  # rich reasoning to the API
                    lv = snap.get("levels_completed", 0)
                    after_board = _board_hash(snap["grid"])
                    verdict = classify(cur_board, after_board, lv - prev,
                                       bool(snap.get("done")), snap.get("state"))
                    circuit.record(cur_board, lbl, data, verdict)  # <- the price feeds back into generation
                    payload["verdict"] = verdict
                    led.record_action(gen, total_steps, lbl, data, payload, lv)
                    led.record_verdict(verdict)
                    novel = after_board not in seen; seen.add(after_board)
                    if lv > prev:
                        led.record_level_up(gen, total_steps, prev, lv); best = max(best, lv); since_progress = 0
                    elif novel:
                        since_progress = 0                        # reaching a NEW board state = still revealing
                    else:
                        since_progress += 1                       # cycling/static = stalling
                    life_steps += 1; total_steps += 1
                    if total_steps % 20 == 0:
                        led.flush()
                # generation ended: let the society tune the reset threshold, record the receipt
                gained = best > prev_best
                adj = rp.adapt(reason or "budget", gained)
                led.record_generation_end(gen, reason or "budget", life_steps, adj)
                led.snapshot_hypotheses(gen, payload_hyps(payload), abduced_list(payload))
                if (now() - t0) >= wall_cap_s:
                    outcome = "wall_cap"; break
                snap = session.reset_after_death(
                    reasoning={"why": "generational reset (%s)" % reason, "generation": gen})
                pol.note_reset()
        finally:
            led.flush()
            try:
                session.close()
            except Exception:
                pass
        return self._result(game_id, best, gen, total_steps, outcome, led, session)

    def run_online(self, game_id: str, **kw) -> Dict[str, Any]:
        """Live entry: own scorecard per game (independent -- no shared swarm scorecard, so RESET is clean)."""
        import os, sys
        src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from newhorse.arc3_env import Arc3Session
        session = Arc3Session(game_id, tags=["nexus", "generational", game_id])
        return self.run(session, game_id, **kw)

    @staticmethod
    def _result(game_id, best, gen, steps, outcome, led, session):
        return {"game": game_id, "best_level": best, "generations": gen + 1, "steps": steps,
                "outcome": outcome, "ledger": led.flush(), "summary": led.summary(),
                "view_url": getattr(session, "view_url", None)}


def payload_hyps(payload):
    return (payload or {}).get("proposer", {}).get("candidates", []) if payload else []

def abduced_list(payload):
    return (payload or {}).get("proposer", {}).get("abduced_objectives", []) if payload else []

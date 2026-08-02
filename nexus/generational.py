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


class GenerationalRunner:
    def __init__(self, run_dir: str = "/tmp/nexus_runs"):
        self.run_dir = run_dir

    def run(self, session, game_id: str, *, max_generations: int = 20, max_actions_per_life: int = 120,
            wall_cap_s: float = 3600.0, blackboard=None, run_tag: str = "", now=time.time) -> Dict[str, Any]:
        import sys, os
        src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from newhorse.redux_arch.policy import ReduxPolicy

        led = RunLedger(game_id, self.run_dir, run_tag=run_tag)
        pol = ReduxPolicy(game_id=game_id, blackboard=blackboard, warmup_cap=8)  # ONE agent across generations
        snap = session.open()
        best = snap.get("levels_completed", 0)
        t0 = now(); total_steps = 0; outcome = "budget"; gen = 0
        try:
            for gen in range(max_generations):
                led.start_generation(gen)
                life_steps = 0
                while life_steps < max_actions_per_life and (now() - t0) < wall_cap_s:
                    pol.observe(snap["grid"], snap["available"], snap.get("levels_completed", 0),
                                state=snap.get("state"))
                    if snap.get("done"):
                        if snap.get("state") == "WIN":
                            outcome = "WIN"
                            led.flush()
                            return self._result(game_id, best, gen, total_steps, outcome, led, session)
                        earned, why = pol.reset_earned()          # GAME_OVER: what killed us (a receipt)
                        led.record_death(gen, total_steps, why)
                        if why:
                            led.record_refuted(why)               # never re-spend this across generations
                        break                                      # end lifetime -> reset into next generation
                    lbl, data = pol.choose()
                    payload = decision_reasoning(pol, lbl, data, total_steps, gen)
                    prev = snap.get("levels_completed", 0)
                    snap = session.step(int(lbl[1:]), data=data,
                                        reasoning={"why": compact_why(payload), **payload})  # rich reasoning to the API
                    lv = snap.get("levels_completed", 0)
                    led.record_action(gen, total_steps, lbl, data, payload, lv)
                    if lv > prev:
                        led.record_level_up(gen, total_steps, prev, lv); best = max(best, lv)
                    life_steps += 1; total_steps += 1
                    if total_steps % 20 == 0:
                        led.flush()
                # snapshot this generation's live hypotheses, then reset into the next
                led.snapshot_hypotheses(gen, payload_hyps(payload), abduced_list(payload))
                if (now() - t0) >= wall_cap_s:
                    outcome = "wall_cap"; break
                snap = session.reset_after_death(reasoning={"why": "generational reset", "generation": gen})
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

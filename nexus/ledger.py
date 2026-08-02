"""nexus.ledger -- the per-run shared reference: a mutable, queryable JSON that lives for ONE game's
run and persists across LIFETIMES (resets). This is the offline reconstruction of the database/
generations the Tether paper thought the offline constraint removed (§16.7): you don't need SQL, you
need a run-local store the agent can write, update, and self-reference across its own history.

It carries what makes generations COMPOUND instead of thrash: the refuted set (never re-spend a move
a past lifetime proved fatal/dead), the per-action reasoning trace (incl. the proposer's proposals),
deaths + their causes, level-ups, and per-generation hypothesis snapshots. Nothing here decides
anything -- it records receipts and answers queries. The ground still prices everything.
"""
from __future__ import annotations
import json, os, time
from typing import Any, Dict, List, Optional


class RunLedger:
    def __init__(self, game_id: str, run_dir: str = "/tmp/nexus_runs", run_tag: str = ""):
        os.makedirs(run_dir, exist_ok=True)
        stamp = run_tag or str(int(time.time()))
        self.path = os.path.join(run_dir, f"{game_id}_{stamp}.json")
        self.data: Dict[str, Any] = {
            "game": game_id, "started": time.time(),
            "best_level": 0, "generations": 0,
            "refuted": [],            # causes/moves a past lifetime proved dead -- do not re-spend
            "actions": [],            # per-action: {gen, step, action, data, levels, reasoning}
            "deaths": [],             # {gen, step, cause}
            "level_ups": [],          # {gen, step, from, to}
            "hypothesis_snapshots": [],  # {gen, hypotheses:[...], abduced:[...]}
            "generation_ends": [],    # {gen, reason: death|stall|cap|budget, life_steps, adjustment}
        }

    # ---- writes (receipts) ------------------------------------------------------------------------
    def start_generation(self, gen: int) -> None:
        self.data["generations"] = max(self.data["generations"], gen + 1)

    def record_action(self, gen: int, step: int, action: str, data: Optional[dict],
                      reasoning: dict, levels: int) -> None:
        self.data["actions"].append({"gen": gen, "step": step, "action": action, "data": data,
                                     "levels": levels, "reasoning": reasoning})

    def record_refuted(self, cause: str) -> None:
        if cause and cause not in self.data["refuted"]:
            self.data["refuted"].append(cause)

    def record_death(self, gen: int, step: int, cause: str) -> None:
        self.data["deaths"].append({"gen": gen, "step": step, "cause": cause})

    def record_level_up(self, gen: int, step: int, frm: int, to: int) -> None:
        self.data["level_ups"].append({"gen": gen, "step": step, "from": frm, "to": to})
        self.data["best_level"] = max(self.data["best_level"], to)

    def snapshot_hypotheses(self, gen: int, hypotheses: List[str], abduced: List[str]) -> None:
        self.data["hypothesis_snapshots"].append({"gen": gen, "hypotheses": hypotheses, "abduced": abduced})

    def record_generation_end(self, gen: int, reason: str, life_steps: int, adjustment: dict) -> None:
        """Why a generation ended (death/stall/cap/win/budget) + how the society retuned the reset."""
        self.data["generation_ends"].append({"gen": gen, "reason": reason, "life_steps": life_steps,
                                              "adjustment": adjustment})

    # ---- self-reference (queries the agent uses across lifetimes) ---------------------------------
    def is_refuted(self, cause: str) -> bool:
        return cause in self.data["refuted"]

    def summary(self) -> Dict[str, Any]:
        """The compact view a new lifetime reads first: how far we've gotten, what's dead, how we've died."""
        return {"best_level": self.data["best_level"], "generations": self.data["generations"],
                "refuted": list(self.data["refuted"]),
                "n_deaths": len(self.data["deaths"]),
                "death_causes": sorted({d["cause"] for d in self.data["deaths"] if d["cause"]})}

    def flush(self) -> str:
        self.data["updated"] = time.time()
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2, default=str)
        return self.path

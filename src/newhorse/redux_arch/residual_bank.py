"""
residual_bank.py -- PERSISTENT RESIDUAL ACCUMULATION (Tether §3.5 QUARANTINE/ACCUMULATE: "deferred residual
accumulates across boundaries").

WHAT PROBLEM THIS IS AIMED AT, IN ONE LINE. The measured stall distribution is DIED_PRE_DIFF 22 / RESIDUAL_EMPTY 4
/ MINT_UNFIRED 16 / REUSE_UNWIRED 2. The 16 are segments where the diff RAN and found MIXED structure and the
two-part MDL code still declined -- because a segment's residual is ~5 exceptions and the selection cost alone is
~6 bits, so no split of five items can ever pay for naming itself. Today `_residual_pass` computes that residual,
scores it, and DROPS IT ON THE FLOOR at segment close. Each episode therefore re-meets the same wall with the same
five items. This module is the floor: the residual survives the segment, the level, and the process.

WHAT IT BANKS AND WHAT IT REFUSES TO BANK. It banks EVIDENCE -- (before-state Context, outcome) pairs, exactly the
type the minter consumes -- and never CONCLUSIONS. No predicate, no verdict, no per-game answer is written here.
That distinction is the whole safety argument: a bank of evidence can only ever let the SAME acceptance rule see
more data; a bank of conclusions would let a past episode's verdict skip the rule. (Charter: "bank evidence, never
conclusions"; Blackboard's rule, "learned MECHANISMS, never per-game answers", is the same rule one layer up.)

SCOPE: KEYED PER GAME FAMILY, NEVER CROSS-GAME. `ls20-016295f7` and `ls20-9c1e...` are two instances of one game
and share colour semantics; `ls20` and `tn36` do not. Pooling colour-indexed exceptions across families would mint
a rule about the integer 4 meaning two different things -- a §7 perception failure ("if the object basis is wrong,
the residual is consistent but lying") dressed up as a mint. So the key is the family prefix and nothing wider.
Widening this key is a separate, separately-measured decision.

DECAY BOUND (§3.5 PARK, "freeze under a decay bound"). Deposits carry a monotonic SERIAL, not a wall clock, so the
bound is reproducible in tests and across processes. Two bounds apply together: entries older than `max_age`
serials are forgotten, and the pool is capped at `capacity` exceptions (oldest evicted first). Without a bound an
accumulating pool eventually mints from a mixture of regimes that never co-existed -- the ACCUMULATE failure mode
the spec parks against.

WHAT THIS DOES NOT FIX. Nothing here touches DIED_PRE_DIFF (22): if the diff never ran there is no evidence to
bank. Nothing here touches RESIDUAL_EMPTY (4): a pure residual contributes nothing to a pool. It is aimed at the
16 and only the 16, and the receipt says which pool a mint came from so the claim stays checkable.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .dsl import Context

Exception_ = Tuple[Context, bool]

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
DEFAULT_BANK_DIR = os.environ.get("NEWHORSE_BANK_DIR", os.path.join(_REPO, ".residual_bank"))

DEFAULT_MAX_AGE = 32          # serials: a deposit is forgotten 32 deposits later on the same key
DEFAULT_CAPACITY = 400        # exceptions: hard cap on the pooled evidence for one key


def family_key(game_id: str) -> str:
    """The pooling key: the game FAMILY prefix, never the instance. `ls20-016295f7` -> `ls20`."""
    g = str(game_id or "").strip()
    return g.split("-", 1)[0] if g else "unknown"


# ---- serialisation: evidence only ---------------------------------------------------------------------------
def _ctx_to_json(c: Context) -> dict:
    return dict(focus_rc=list(c.focus_rc), focus_colour=int(c.focus_colour),
                target_rc=list(c.target_rc), action_vec=list(c.action_vec),
                intended_free=bool(c.intended_free),
                intended_colour=(None if c.intended_colour is None else int(c.intended_colour)))


def _ctx_from_json(d: dict) -> Context:
    return Context(focus_rc=tuple(d["focus_rc"]), focus_colour=int(d["focus_colour"]),
                   target_rc=tuple(d["target_rc"]), action_vec=tuple(d["action_vec"]),
                   intended_free=bool(d.get("intended_free", True)),
                   intended_colour=(None if d.get("intended_colour") is None else int(d["intended_colour"])))


@dataclass
class Deposit:
    """One segment's residual, kept whole so a pool can always be decomposed back into the segments that made it."""
    task_id: str
    serial: int
    exceptions: List[Exception_] = field(default_factory=list)

    def to_json(self) -> dict:
        return dict(task_id=self.task_id, serial=int(self.serial),
                    exceptions=[[_ctx_to_json(c), bool(o)] for c, o in self.exceptions])

    @staticmethod
    def from_json(d: dict) -> "Deposit":
        return Deposit(task_id=str(d.get("task_id", "?")), serial=int(d.get("serial", 0)),
                       exceptions=[(_ctx_from_json(e[0]), bool(e[1])) for e in d.get("exceptions", [])])


@dataclass
class ResidualBank:
    """Durable, per-family accumulation of residual EVIDENCE under a decay bound.

    Thread-safe (the swarm runs 8 workers and two of them can be on the same family). Disk writes are
    temp-file-and-rename so a killed run leaves a whole file or the previous whole file, never half of one."""
    root: str = DEFAULT_BANK_DIR
    max_age: int = DEFAULT_MAX_AGE
    capacity: int = DEFAULT_CAPACITY
    persist: bool = True
    _mem: Dict[str, List[Deposit]] = field(default_factory=dict, repr=False)
    _serial: Dict[str, int] = field(default_factory=dict, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    # ---- disk ------------------------------------------------------------------------------------------------
    def _path(self, key: str) -> str:
        safe = "".join(ch for ch in key if ch.isalnum() or ch in "._-") or "unknown"
        return os.path.join(self.root, safe + ".json")

    def _load(self, key: str) -> None:
        """Read the key's bank from disk ONCE per process. A corrupt or absent file starts an empty bank -- a bank
        that raises would sink a run, and the honest fallback for lost evidence is no evidence."""
        if key in self._mem:
            return
        self._mem[key] = []
        self._serial[key] = 0
        if not self.persist:
            return
        p = self._path(key)
        try:
            with open(p, "r", encoding="utf-8") as f:
                blob = json.load(f)
            self._mem[key] = [Deposit.from_json(d) for d in blob.get("deposits", [])]
            self._serial[key] = int(blob.get("serial", 0))
        except Exception:
            self._mem[key] = []
            self._serial[key] = 0

    def _flush(self, key: str) -> None:
        if not self.persist:
            return
        p = self._path(key)
        try:
            os.makedirs(self.root, exist_ok=True)
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(dict(key=key, serial=int(self._serial.get(key, 0)),
                               deposits=[d.to_json() for d in self._mem.get(key, [])]), f)
            os.replace(tmp, p)
        except Exception:
            pass                      # a bank that cannot write must not sink a run

    # ---- decay -----------------------------------------------------------------------------------------------
    def _decay(self, key: str) -> None:
        """Apply both bounds, newest-first. AGE first (a stale regime is dropped even if there is room), then
        CAPACITY (oldest evicted until the pooled exception count fits)."""
        cur = self._serial.get(key, 0)
        deps = [d for d in self._mem.get(key, []) if cur - d.serial <= self.max_age]
        deps.sort(key=lambda d: d.serial)
        total = sum(len(d.exceptions) for d in deps)
        while deps and total > self.capacity:
            total -= len(deps[0].exceptions)
            deps.pop(0)
        self._mem[key] = deps

    # ---- API -------------------------------------------------------------------------------------------------
    def deposit(self, game_id: str, task_id: str, exceptions: Sequence[Exception_]) -> int:
        """Bank one segment's residual. Returns the serial assigned. An empty residual is not banked -- there is
        nothing in it, and banking it would only age the pool for free."""
        if not exceptions:
            return -1
        key = family_key(game_id)
        with self._lock:
            self._load(key)
            self._serial[key] = self._serial.get(key, 0) + 1
            s = self._serial[key]
            self._mem[key].append(Deposit(task_id=str(task_id), serial=s, exceptions=list(exceptions)))
            self._decay(key)
            self._flush(key)
            return s

    def pool(self, game_id: str, exclude_task: Optional[str] = None) -> Tuple[List[Exception_], List[str]]:
        """The accumulated evidence for this family, oldest first, with the task ids that contributed it.

        `exclude_task` drops one task's own deposits so a caller can ask "what did the PAST say?" separately from
        "what did this segment say?" -- the two are different questions and conflating them would let a fresh
        residual be scored twice and read as corroboration."""
        key = family_key(game_id)
        with self._lock:
            self._load(key)
            self._decay(key)
            out: List[Exception_] = []
            tasks: List[str] = []
            for d in self._mem.get(key, []):
                if exclude_task is not None and d.task_id == exclude_task:
                    continue
                out.extend(d.exceptions)
                if d.task_id not in tasks:
                    tasks.append(d.task_id)
            return out, tasks

    def stats(self, game_id: str) -> Dict[str, int]:
        key = family_key(game_id)
        with self._lock:
            self._load(key)
            self._decay(key)
            deps = self._mem.get(key, [])
            return dict(deposits=len(deps), exceptions=sum(len(d.exceptions) for d in deps),
                        tasks=len({d.task_id for d in deps}), serial=int(self._serial.get(key, 0)))

    def clear(self, game_id: Optional[str] = None) -> None:
        """Forget a family's bank (or all of them). Test hygiene and the manual undo path."""
        with self._lock:
            keys = [family_key(game_id)] if game_id is not None else list(self._mem.keys())
            for k in keys:
                self._mem[k] = []
                self._serial[k] = 0
                if self.persist:
                    try:
                        os.remove(self._path(k))
                    except OSError:
                        pass

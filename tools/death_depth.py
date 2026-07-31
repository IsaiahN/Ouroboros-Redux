"""Offline attribution over a sweep capture: HOW DEEP DID THE AGENT GET BEFORE EACH DEATH, AND DID A RESTART BUY IT
ANYTHING? (`tools/replay_mint.py` is the pattern -- attribute offline, from a file, before claiming anything.)

Reads the `=== WHAT THE DEATHS TAUGHT` and `=== THE ACTION BUDGET` sections of a sweep capture and prints, per game,
the step index of every death and the interval between consecutive deaths. Nothing is re-derived from the agent:
every number here was printed by `tools/sweep_chain.py` from a string the policy itself wrote.

THE COLUMN THAT MATTERS IS `actions/life`, NOT THE RAW MARKS.
  * The `@N` on an `EARNED RESET` line is `steps` AFTER the reset's own increment, so the death happened at `N-1`
    and the raw gap between two marks is one MORE than the number of actions the agent actually took between them.
    That is the budget identity of CLASSIFIER 11 showing up in the log; it is not noise. Printing the raw gap and
    asking the reader to subtract is how an off-by-one becomes a finding, so this tool subtracts it here, once,
    and prints ACTIONS PER LIFE: `marks[0]-1` for the first life, `marks[i]-1-marks[i-1]` for each granted
    restart, and `final_steps - marks[-1]` for a terminal life (no reset follows it, so nothing is added back).
  * The TERMINAL death carries no `@N` at all (the branch logs and breaks). Its depth is DERIVED as the game's
    final `steps` and is marked `[derived]` in the table. Deriving it is sound -- the run ends at that death -- but
    it is not a printed receipt, and it is the first thing to fix if these lives are ever load-bearing.
  * A life count is only comparable WITHIN a game. Two games that both die after 50 actions have nothing in
    common; one game that dies after 50 actions three times in a row is the observation.
"""
from __future__ import annotations
import re
import sys


def parse(path: str) -> dict:
    txt = open(path, encoding="utf-8").read()
    if "=== WHAT THE DEATHS TAUGHT" not in txt:
        raise SystemExit("%s carries no deaths section -- it predates the §XIX rationale printer" % path)
    sec = txt.split("=== WHAT THE DEATHS TAUGHT")[1].split("\n=== ")[0]
    budget = txt.split("=== THE ACTION BUDGET")[1].split("\n=== ")[0]
    steps = {}
    for m in re.finditer(r"^\s{2}(\S+-\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(\S+)", budget, re.M):
        g, st, _dec, ret, dth, _res, out = m.groups()
        steps[g] = dict(steps=int(st), retries=int(ret), deaths=int(dth), outcome=out)
    per: dict = {}
    cur = None
    for line in sec.splitlines():
        m = re.match(r"^\s{2}(\S+-\S+)\s", line)
        if m:
            cur = m.group(1)
            per[cur] = dict(at=[], acts=[], terminal=None)
            continue
        if cur and "EARNED  :" in line:
            per[cur]["at"].append(int(re.search(r"@(\d+):", line).group(1)))
            per[cur]["acts"].append(re.search(r"action (\w+) from this board", line).group(1))
        if cur and "TERMINAL:" in line and "MISSING" not in line:
            per[cur]["terminal"] = re.search(r"action (\w+) from a board", line).group(1)
    return {"steps": steps, "per": per}


def lives(marks: list, final_steps, terminal: bool) -> list:
    """Actions the agent took in each life, from the marks the policy printed. See the module docstring for why
    the `-1` is here: the mark is post-increment, so the raw gap overstates the actions by exactly one. Returns
    [] when there is nothing to say -- a game with no marks has no lives to compare."""
    out = []
    for i, m in enumerate(marks):
        out.append(m - 1 if i == 0 else m - 1 - marks[i - 1])
    if terminal and final_steps is not None:
        out.append(int(final_steps) - (marks[-1] if marks else 0))
    return out


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/armL_deaths.txt"
    d = parse(path)
    steps, per = d["steps"], d["per"]
    print("DEATH DEPTH per game (capture: %s)" % path)
    print("  %-18s %-20s %-26s %-16s %s" % ("game", "outcome", "death @steps", "actions/life", "fatal actions"))
    flat, varied = [], []
    for g in sorted(per):
        s = steps.get(g, {})
        term = per[g]["terminal"] is not None
        acts = list(per[g]["acts"]) + ([per[g]["terminal"] + "*"] if term else [])
        lv = lives(per[g]["at"], s.get("steps"), term)
        if len(lv) > 1:
            (flat if max(lv) == min(lv) else varied).append(g)
        shown = ", ".join(str(x) for x in per[g]["at"])
        if term:
            shown += ", [%s derived]" % s.get("steps")
        print("  %-18s %-20s %-26s %-16s %s"
              % (g, s.get("outcome"), shown, ", ".join(str(x) for x in lv) or "--", " ".join(acts)))
    multi = sorted(flat + varied)
    print("  %d game(s) lived more than once. * marks the terminal death (depth derived, not printed)." % len(multi))
    if multi:
        print("  %d of %d reproduce their per-life action count EXACTLY across every life: %s"
              % (len(flat), len(multi), ", ".join(sorted(flat)) or "none"))
        if varied:
            print("  ★ %s did NOT -- report these by name. A game where a later life runs materially LONGER is the"
                  " only shape in this table that shows a restart buying anything." % ", ".join(sorted(varied)))
    print("  ⇒ A CONSTANT per-life count means the restart bought the agent no additional depth. It does NOT say"
          " why: a replayed route and a per-game death clock both produce it, and this capture cannot tell them"
          " apart. What separates them is the death BOARD, which no receipt currently carries.")


if __name__ == "__main__":
    main()

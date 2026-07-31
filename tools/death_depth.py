"""Offline attribution over a sweep capture: HOW DEEP DID THE AGENT GET BEFORE EACH DEATH, AND DID A RESTART BUY IT
ANYTHING? (`tools/replay_mint.py` is the pattern -- attribute offline, from a file, before claiming anything.)

Reads the `=== WHAT THE DEATHS TAUGHT` and `=== THE ACTION BUDGET` sections of a sweep capture and prints, per game,
the step index of every death, the interval between consecutive deaths, and the BOARD each death happened on.
Nothing is re-derived from the agent: every number here was printed by `tools/sweep_chain.py` from a string the
policy itself wrote.

THE COLUMN THAT MATTERS IS `actions/life`, NOT THE RAW MARKS.
  * The `@N` on an `EARNED RESET` line is `steps` AFTER the reset's own increment, so the death happened at `N-1`
    and the raw gap between two marks is one MORE than the number of actions the agent actually took between them.
    That is the budget identity of CLASSIFIER 11 showing up in the log; it is not noise. Printing the raw gap and
    asking the reader to subtract is how an off-by-one becomes a finding, so this tool subtracts it here, once,
    and prints ACTIONS PER LIFE: `marks[0]-1` for the first life, `marks[i]-1-marks[i-1]` for each granted
    restart, and `final_steps - marks[-1]` for a terminal life (no reset follows it, so nothing is added back).
  * THE TERMINAL DEATH NOW STAMPS ITS OWN `@N`. Until this beat that branch logged and broke without a mark, so its
    depth had to be DERIVED as the game's final `steps` and the whole life table rested on a derivation. The mark is
    read at the same site and off the same counter as the EARNED ones, one branch apart, and it is NOT
    post-incremented (that branch grants no reset). This tool computes BOTH and cross-checks them rather than
    silently switching: a disagreement is printed by name and loudly, because it would mean the derived table that
    has already been published was wrong. Captures that predate the stamp still parse -- their terminal mark reads
    `[derived]` and the cross-check is skipped, not faked.
  * A life count is only comparable WITHIN a game. Two games that both die after 50 actions have nothing in
    common; one game that dies after 50 actions three times in a row is the observation.

THE BOARD COLUMN IS WHAT SEPARATES THE TWO READINGS OF A FLAT LIFE COUNT, AND ONE HALF OF IT IS TAUTOLOGICAL.
A constant per-life count says a restart bought no depth; it does not say WHY. Two mechanisms produce it and the
step marks cannot tell them apart: H2, the agent REPLAYS the same route and dies on the same screen; H1, a per-game
DEATH CLOCK kills it at a fixed depth wherever it happens to be. The `‖ DEATH-BOARD board=…` clause the §XIX branch
now writes carries the identity the gate itself judged, so the two shapes are finally distinguishable -- but only
if the tautology is held apart from the evidence:
  * A `death_no_new_cause` TERMINAL death repeating an earlier board is `[by defn]`, NOT evidence. That literal is
    chosen precisely BECAUSE the memory already held this (board, action); finding the board again in the list is
    restating the branch condition. Citing it as a route would be citing the classifier's own premise back as its
    conclusion.
  * An EARNED death repeating an earlier board IS evidence for H2. The gate ruled that death a NEW cause, so it was
    a new ACTION from a board the agent had already stood on and died at -- the agent walked the same route back to
    the same screen and tried a different way to die there.
  * All-distinct boards plus a flat life count is the H1 shape: dying at the same DEPTH on DIFFERENT screens is what
    a clock looks like and is not what a replay looks like.
  * `distinct` here means only "not pixel-identical". Two boards that differ by one moved pixel of a timer or an
    animated tile are distinct to this column and to the gate, which is the same equivalence -- that is the point,
    and it is also the limit. A game whose screen ticks every frame CANNOT show a repeat, so `distinct` from such a
    game is weak evidence for H1 and must be reported as such rather than counted.
"""
from __future__ import annotations
import re
import sys


_BOARD = re.compile(r"‖ DEATH-BOARD board=(\w+) act=(\S+) pstep=(\d+)")


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
            per[cur] = dict(at=[], acts=[], boards=[], terminal=None, terminal_at=None, terminal_board=None)
            continue
        if cur and "EARNED  :" in line:
            per[cur]["at"].append(int(re.search(r"@(\d+):", line).group(1)))
            per[cur]["acts"].append(re.search(r"action (\w+) from this board", line).group(1))
            b = _BOARD.search(line)
            per[cur]["boards"].append(b.group(1) if b else None)
        if cur and "TERMINAL:" in line and "MISSING" not in line:
            per[cur]["terminal"] = re.search(r"action (\w+) from a board", line).group(1)
            mk = re.search(r"no RESET @(\d+) ", line)                   # absent on captures predating the stamp
            per[cur]["terminal_at"] = int(mk.group(1)) if mk else None
            b = _BOARD.search(line)
            per[cur]["terminal_board"] = b.group(1) if b else None
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


def board_story(boards: list, terminal_board, terminal_is_no_new_cause: bool):
    """Label each death by whether its board was seen at an EARLIER death of the same game, and return
    (labels, verdict) with verdict in {distinct, replay, by-defn, unknown}.

    The ORDER of the tests is the whole content of this function. A terminal repeat under the
    `death_no_new_cause` literal is TAUTOLOGICAL -- that branch was taken because the memory already held the
    (board, action) -- so it is labelled `[by defn]` and can NEVER raise the verdict to `replay`. Only a repeat on
    a death the gate itself ruled a NEW cause is evidence of a replayed route. A game with no boards at all (a
    capture predating the clause) is `unknown`, which is an absence and not a `distinct`."""
    seq = list(boards) + ([terminal_board] if terminal_board is not None else [])
    if not seq or any(b is None for b in seq):
        return ([], "unknown")
    labels, seen, verdict = [], {}, "distinct"
    n_earned = len(boards)
    for i, b in enumerate(seq):
        short = b[:6]
        if b in seen:
            tautological = (i >= n_earned) and terminal_is_no_new_cause
            labels.append("%s=life%d%s" % (short, seen[b] + 1, "[by defn]" if tautological else "★REPEAT"))
            if not tautological:
                verdict = "replay"
            elif verdict == "distinct":
                verdict = "by-defn"
        else:
            seen[b] = i
            labels.append(short)
    return (labels, verdict)


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/armL_deaths.txt"
    d = parse(path)
    steps, per = d["steps"], d["per"]
    print("DEATH DEPTH per game (capture: %s)" % path)
    print("  %-18s %-20s %-26s %-16s %-18s %s"
          % ("game", "outcome", "death @steps", "actions/life", "fatal actions", "death boards"))
    flat, varied, disagree = [], [], []
    verdicts: dict = {}
    for g in sorted(per):
        s = steps.get(g, {})
        term = per[g]["terminal"] is not None
        acts = list(per[g]["acts"]) + ([per[g]["terminal"] + "*"] if term else [])
        lv = lives(per[g]["at"], s.get("steps"), term)
        if len(lv) > 1:
            (flat if max(lv) == min(lv) else varied).append(g)
        shown = ", ".join(str(x) for x in per[g]["at"])
        if term:
            printed, derived = per[g]["terminal_at"], s.get("steps")
            if printed is None:
                shown += ", [%s derived]" % derived
            else:
                shown += ", %d" % printed
                if derived is not None and int(printed) != int(derived):
                    disagree.append("%s(printed %s, derived %s)" % (g, printed, derived))
        labels, verdict = board_story(per[g]["boards"], per[g]["terminal_board"],
                                      str(s.get("outcome")) == "death_no_new_cause")
        verdicts.setdefault(verdict, []).append(g)
        print("  %-18s %-20s %-26s %-16s %-18s %s"
              % (g, s.get("outcome"), shown, ", ".join(str(x) for x in lv) or "--",
                 " ".join(acts), " ".join(labels) or "--"))
    multi = sorted(flat + varied)
    print("  %d game(s) lived more than once. * marks the terminal death." % len(multi))
    if disagree:
        print("  ★★ THE PRINTED TERMINAL STEP DISAGREES WITH THE DERIVED ONE on %s. The derived number is what every"
              " published life table so far was built from, so this is not a formatting note: re-measure before"
              " citing any of them." % ", ".join(disagree))
    if multi:
        print("  %d of %d reproduce their per-life action count EXACTLY across every life: %s"
              % (len(flat), len(multi), ", ".join(sorted(flat)) or "none"))
        if varied:
            print("  ★ %s did NOT -- report these by name. A game where a later life runs materially LONGER is the"
                  " only shape in this table that shows a restart buying anything." % ", ".join(sorted(varied)))
    for v in ("replay", "by-defn", "distinct", "unknown"):
        if verdicts.get(v):
            print("  DEATH BOARDS -- %-8s: %s" % (v, ", ".join(sorted(verdicts[v]))))
    print("  ⇒ READ IT THIS WAY. A flat per-life count says a restart bought no depth and does NOT say why."
          " `replay` (an EARNED death on a board an earlier death already used) is evidence the agent walked the"
          " SAME route back to the SAME screen -- H2. `by-defn` is NOT evidence: a `death_no_new_cause` terminal"
          " repeats its board because that is the branch condition, so counting it would be citing the premise as"
          " the conclusion. `distinct` boards under a FLAT life count is the H1 shape (a per-game death clock),"
          " weakly -- a screen that ticks every frame cannot show a repeat, so check the game before counting it."
          " `unknown` means the capture predates the DEATH-BOARD clause and separates nothing.")


if __name__ == "__main__":
    main()

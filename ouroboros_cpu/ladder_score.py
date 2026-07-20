"""THE LADDER, as a live gauge. Reads a run's DSL stream (the _emit tee) + outcome and scores
(log_rung, corroborated_rung). A rung is CREDITED on the log only if its reasoning MOVES appear; it is
CORROBORATED only if an EXTERNAL fact (a gate opening, the diff shrinking, a level clearing, a minted
primitive being reused) proves the talk cashed out. The gap is the headline: where the agent reasons
above what it can do. Proctor tool -- reads what the agent emits, changes nothing.

Usage: python3 ladder_score.py <stream.log> [<stream2.log> ...]
Stream line format: '[#N act=A lvl=L] KEYWORD  rest...'  (the _emit tee)
"""
import sys, re, glob

# Each rung: signature patterns (its reasoning MOVES) and corroboration patterns (EXTERNAL proof).
# Patterns are regex, matched case-insensitively against the emit text (keyword + body).
RUNGS = [
    ("L0 reflex", {
        "sig": [r"."],                       # floor: any activity at all
        "corr": [r"."],                      # trivially met -- L0 is the basement
    }),
    ("L1 sensorimotor", {
        "sig": [r"\bPROPRIOCEPT\b", r"\bLAYERS\b", r"\bMODEL\b", r"\bRECOGNISE\b", r"\bPASSABLE\b"],
        # corroborated when it BUILT a real model (confirmed object-laws) or REUSED a learned effect
        "corr": [r"confirmed object-laws", r"\bRECOGNISE\b.*reuse", r"reuse the learned effect"],
    }),
    ("L2 representational", {
        "sig": [r"\bHYPOTHESIS\b", r"\bFALSIFY\b", r"GRAMMAR\b.*reads as", r"\bSEGMENT\b", r"\bCARVE\b",
                r"readout identity"],
        # corroborated when role-naming produced a testable structure: a key/lock pair it could COMPARE
        "corr": [r"\bCOMPARE\b", r"target :=", r"readout := .* target :="],
    }),
    ("L3 concrete-operational", {
        "sig": [r"\bCOMPARE\b", r"\bENUMERATE\b", r"\bPLAN\b", r"\bINDUCE\b", r"BUDGET-MATH", r"\bSUBGOAL\b"],
        # corroborated when the PLAN CONVERGED: the compared attributes aligned / a gate opened
        "corr": [r"key MATCHES lock", r"GATE .*SATISFIED", r"MATCH .*-> STOP cycling"],
    }),
    ("L4 formal-operational", {
        "sig": [r"COMPOSED a new molecule", r"MODEL-BREAK", r"is ESTABLISHED from a prior level",
                r"need .*reset", r"return to start", r"I need the ability"],
        # corroborated ONLY when the self-authored move genuinely WORKED. A raw compose does NOT count --
        # the agent minting TEMP_1 from {BECAUSE,BECOME} ("a caused change") is a vacuous mint, the exact
        # dead-reckoning the ladder guards against. Real corroboration = a NAMED grammar molecule reused
        # across a level (established memory that carried), or an earned capability that paid off.
        "corr": [r"is ESTABLISHED from a prior level", r"earned .*-> cleared",
                 r"reads as (?!TEMP_)[A-Z_]+.*already hold.*\n(?:.*\n)*?.*is ESTABLISHED"],
    }),
    ("L5 meta/self-directed", {
        "sig": [r"revise .*own operator", r"my own curriculum", r"transfers to .*held-out",
                r"basin-type .*from game"],
        "corr": [r"generaliz.* across .*games"],
    }),
]


def _levels_progressed(lines):
    lvls = [int(m.group(1)) for ln in lines for m in [re.search(r"lvl=(\d+)", ln)] if m]
    return (max(lvls) - min(lvls)) if lvls else 0


def score_stream(text):
    lines = text.splitlines()
    body = "\n".join(lines)
    cleared = _levels_progressed(lines) > 0
    log_present, corr_met, evid = {}, {}, {}
    for name, pat in RUNGS:
        sig = any(re.search(p, body, re.I) for p in pat["sig"])
        corr = any(re.search(p, body, re.I) for p in pat["corr"])
        # a cleared level is external corroboration that L3's plan converged for real
        if name.startswith("L3") and cleared:
            corr = True
        log_present[name] = sig
        corr_met[name] = sig and corr
        if sig:
            evid[name] = [p for p in pat["sig"] if re.search(p, body, re.I)][:3]
    order = [n for n, _ in RUNGS]
    log_rung = max([n for n in order if log_present[n]], key=order.index, default=order[0])
    corr_rung = max([n for n in order if corr_met[n]], key=order.index, default=order[0])
    return dict(log_rung=log_rung, corr_rung=corr_rung, cleared=cleared, evidence=evid,
                n_emits=len([l for l in lines if l.strip()]))


def main():
    files = []
    for a in sys.argv[1:]:
        files += glob.glob(a)
    if not files:
        print("usage: ladder_score.py <stream.log> [...]"); return
    print("%-28s %-26s %-26s %s" % ("run", "LOG rung", "CORROBORATED rung", "gap"))
    print("-" * 100)
    order = [n for n, _ in RUNGS]
    gaps = []
    for f in sorted(files):
        try:
            s = score_stream(open(f, errors="ignore").read())
        except Exception as e:
            print("%-28s ERROR %s" % (f.split('/')[-1], e)); continue
        gap = order.index(s["log_rung"]) - order.index(s["corr_rung"])
        gaps.append(gap)
        print("%-28s %-26s %-26s %s" % (f.split('/')[-1][:28], s["log_rung"], s["corr_rung"],
              ("+%d rungs (reasons above execution)" % gap) if gap else "aligned"))
    if gaps:
        print("-" * 100)
        print("mean log>corroboration gap: %.1f rungs across %d runs" % (sum(gaps) / len(gaps), len(gaps)))


if __name__ == "__main__":
    main()

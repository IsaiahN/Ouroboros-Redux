"""test_marketplace_fidelity.py -- does the extracted invariant actually reproduce v4?

The whole port rests on one claim: that v4's marketplace and a single agent's internal marketplace are the SAME
mechanism at different shells. That claim is worth nothing unless the extracted protocol, bound to v4's semantics,
reproduces v4's real numbers. So these tests hard-code the arithmetic transcribed from v4's source and check the
generic protocol against it. If this file fails, the invariant is my paraphrase of v4 and not v4, and the micro
binding inherits a story instead of a mechanism.

    python3 test_marketplace_fidelity.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True

from marketplace import (CONSENSUS_THRESHOLD, EpisodeScoreCurrency, Ledger, Marketplace, Proposal,
                         WEIGHT_CEIL, WEIGHT_FLOOR, vote_weight)

FAIL = []


def check(name, got, want, eps=1e-9):
    ok = (abs(got - want) < eps) if isinstance(want, float) else (got == want)
    print("  %-58s %s   got=%r want=%r" % (name, "OK " if ok else "FAIL", got, want))
    if not ok:
        FAIL.append(name)


print("== 1. proposal pricing: v4 `min(1.0, 0.3 + score_change*2.0)` ==")
cur, led = EpisodeScoreCurrency(), Ledger()
for delta, want in ((0.0, 0.3), (0.1, 0.5), (0.35, 1.0), (2.0, 1.0)):
    p = Proposal("a", 1, 0.0, payload={"score_change": delta})
    check("delta=%.2f -> confidence" % delta, cur.price(p, led), want)

print("\n== 2. vote weight: cap each term at 1.5, average, clamp to [0.5, 2.0] ==")
led = Ledger()
# v4: score_weight=min(1.5, avg/10), win_weight=min(1.5, wins/5), eff=min(1.5, efficiency*2)
led.record("strong", score=100.0, wins=10.0, efficiency=1.0)     # avg=100 -> 10 capped 1.5; wins 10/5=2 -> 1.5; eff 2 -> 1.5
# v4's EFFECTIVE ceiling is TERM_CEIL (1.5), not WEIGHT_CEIL: the average of three <=1.5 terms cannot exceed 1.5,
# so the outer min(2.0, ...) is dead code in v4 itself. Assert the real behaviour, not the advertised constant.
check("saturated actor clamps at the EFFECTIVE ceiling 1.5", vote_weight(cur, "strong", led), 1.5)
led2 = Ledger()
led2.record("weak", score=0.0, wins=0.0, efficiency=0.0)          # all terms 0 -> avg 0 -> clamped up to floor
check("worthless actor still keeps a voice (floor)", vote_weight(cur, "weak", led2), WEIGHT_FLOOR)
check("unknown actor gets a fair hearing (v4 default 1.0)", vote_weight(cur, "never_seen", Ledger()), 1.0)
led3 = Ledger()
led3.record("mid", score=50.0, wins=2.5, efficiency=0.25)         # (1.5 + 0.5 + 0.5)/3 = 0.8333
check("mid actor averages its capped terms", vote_weight(cur, "mid", led3), (1.5 + 0.5 + 0.5) / 3.0, eps=1e-6)

print("\n== 3. THE CLAMP: the best actor cannot outvote a crowd of weak ones ==")
led4 = Ledger()
led4.record("titan", score=1000.0, wins=100.0, efficiency=10.0)
for i in range(4):
    led4.record("weak%d" % i, score=0.0, wins=0.0, efficiency=0.0)
titan_w = vote_weight(cur, "titan", led4)
crowd_w = sum(vote_weight(cur, "weak%d" % i, led4) for i in range(4))
check("titan weight is capped at 1.5", titan_w, 1.5)
print("     titan=%.2f vs crowd-of-4=%.2f -> crowd prevails: %s" % (titan_w, crowd_w, crowd_w > titan_w))
if crowd_w <= titan_w:
    FAIL.append("clamp fails to protect the ensemble")

print("\n== 4. consensus ratio + 0.6 threshold ==")
class FixedCur(EpisodeScoreCurrency):
    """standings fixed so the vote pattern is deterministic and hand-checkable"""
    def __init__(self, standings): self.s = standings
    def standing(self, actor_id, ledger): return self.s.get(actor_id, 0.0)
    def weight_terms(self, actor_id, ledger): return (1.0, 1.0, 1.0)      # every weight = 1.0 -> ratio is pure counting

# 3 actors: A measured +0.5, B +0.1, C 0.0. Each votes on the others.
mk = Marketplace(FixedCur({"A": 0.5, "B": 0.1, "C": 0.0}), Ledger())
ps = [Proposal("A", 1, 0, payload={"score_change": 0.5}, rationale="A"),
      Proposal("B", 2, 0, payload={"score_change": 0.1}, rationale="B"),
      Proposal("C", 3, 0, payload={"score_change": 0.0}, rationale="C")]
ps = mk.propose(ps)
vs = mk.vote(ps)
# A: voters B(0.1) and C(0.0); A's 0.5 >= both -> 2 for, 0 against -> ratio 1.0
a_for = sum(1 for v in vs if v.proposal.actor_id == "A" and v.choice == "for")
check("best-measured proposal draws unanimous support", a_for, 2)
# C: standing 0.0; voters A(0.5) and B(0.1) both outrank it, and 0.0 is not > 0 -> 0 for, 2 against -> ratio 0.0
c_against = sum(1 for v in vs if v.proposal.actor_id == "C" and v.choice == "against")
check("unevidenced proposal is rejected by everyone", c_against, 2)
res = mk.resolve(ps, vs)
check("winner is the measured-best actor", res["proposal"].actor_id, "A")
check("winner's consensus ratio", res["consensus_ratio"], 1.0)

print("\n== 5. no forced consensus when standings genuinely differ ==")
# X measured nothing, Y measured a loss. Y's -0.2 < X's 0.0 and is not > 0 -> X votes AGAINST Y.
mk2 = Marketplace(FixedCur({"X": 0.0, "Y": -0.2}), Ledger())
ps2 = mk2.propose([Proposal("X", 1, 0, payload={"score_change": 0.0}),
                   Proposal("Y", 2, 0, payload={"score_change": -0.2})])
v2 = mk2.vote(ps2)
y_against = sum(1 for v in v2 if v.proposal.actor_id == "Y" and v.choice == "against")
check("a measured LOSS is voted down", y_against, 1)

print("\n== 5b. COLD START (v4's real, degenerate behaviour -- transcribed, not wished away) ==")
# Two actors BOTH at zero evidence. v4 rule: `proposer >= voter` -> 'for'. 0.0 >= 0.0 is True, so they endorse each
# other unanimously and the market rubber-stamps a bid backed by NOTHING. In v4 this was masked: deliberation only
# ran on stuck games among agents that already had records. At the micro shell every level STARTS here, which is
# exactly when the market is most needed -- so the micro binding must break this tie on something real.
mkc = Marketplace(FixedCur({"X": 0.0, "Y": 0.0}), Ledger())
psc = mkc.propose([Proposal("X", 1, 0, payload={"score_change": 0.0}),
                   Proposal("Y", 2, 0, payload={"score_change": 0.0})])
resc = mkc.resolve(psc, mkc.vote(psc))
check("cold start rubber-stamps (documented v4 defect, ratio=1.0)", (resc or {}).get("consensus_ratio"), 1.0)

print("\n== 6. below quorum there is no market, only an opinion ==")
mk3 = Marketplace(FixedCur({"solo": 1.0}), Ledger())
check("single bidder -> None", mk3.run([Proposal("solo", 1, 0, payload={"score_change": 1.0})]), None)

print("\n== 7. the protocol is shell-agnostic: a DIFFERENT currency binds with no protocol change ==")
class PredictionErrorCurrency(EpisodeScoreCurrency):
    """micro sketch: actor = chain, arena = frame, currency = 1 - normalised prediction error"""
    def price(self, proposal, ledger):
        acc = float(proposal.payload.get("accuracy", 0.0))
        return min(1.0, 0.3 + acc * 2.0)
    def standing(self, actor_id, ledger):
        r = ledger.get(actor_id); n = max(1.0, r.get("n", 0.0))
        return r.get("hits", 0.0) / n
    def weight_terms(self, actor_id, ledger):
        r = ledger.get(actor_id); n = max(1.0, r.get("n", 0.0))
        return (r.get("hits", 0.0) / n * 1.5, r.get("confirmed", 0.0) / 5.0, r.get("hits", 0.0) / n * 2.0)

led5 = Ledger()
led5.record("chain_sharp", hits=1.0, confirmed=1.0)
led5.record("chain_blunt", hits=0.0, confirmed=0.0)
mk4 = Marketplace(PredictionErrorCurrency(), led5)
r4 = mk4.run([Proposal("chain_sharp", "UP", 0, payload={"accuracy": 0.9}, rationale="sharp"),
              Proposal("chain_blunt", "DOWN", 0, payload={"accuracy": 0.0}, rationale="blunt")])
check("same protocol, new shell: accurate chain wins", (r4 or {}).get("proposal").actor_id if r4 else None,
      "chain_sharp")

print("\n" + ("ALL FIDELITY TESTS PASSED" if not FAIL else "FAILURES: %s" % FAIL))
sys.exit(1 if FAIL else 0)

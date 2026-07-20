"""marketplace.py -- the Ouroboros invariant, extracted once and bound at any shell.

WHAT THIS IS
------------
Ouroboros v1-v4 solved games with a network of agents that traded ideas: propose -> vote -> resolve -> promote. It
worked even when the individual agents were poor, and the reason is visible in the arithmetic rather than in any
agent's cleverness:

    confidence  = min(1.0, 0.3 + measured_delta * 2.0)        # a proposal is priced by what it MEASURABLY did
    vote        = 'for' if proposer_delta >= my_delta else 'against'
    weight      = clamp(mean(track-record terms), 0.5, 2.0)   # <-- the load-bearing line
    ratio       = weighted_for / (weighted_for + weighted_against)
    accepted    = ratio >= 0.6

Nothing is priced by how good it sounds. Every number descends from an outcome someone actually observed. And the
CLAMP is what makes an ensemble of weak actors strong: the best actor caps at 2.0 so it can never dictate, the worst
floors at 0.5 so it never loses its voice. Diversity is protected from competence by construction. A marketplace
without that clamp collapses into the winner's monologue -- which is exactly what a single-hypothesis solver already
is, and exactly what this exists to fix.

THE SHELLS (why this file is parameterised rather than copied)
-------------------------------------------------------------
The same invariant runs at more than one scale; each shell is not a copy but the invariant transformed by its own
actors, currency and arena:

    shell       actor                     arena            currency
    macro       an agent                  a game episode   score_change over the episode
    micro       a perceptual carving      one frame        prediction error against the next frame

The protocol below knows about none of that. It asks a Currency for two things -- how to price a proposal, and how to
score a track record -- and is otherwise identical at every shell. If a shell cannot be expressed by binding a
Currency to this protocol, then it is not the same invariant and the claim of a shared mechanism is false. That is a
falsifiable claim and it is meant to be: the macro binding exists to be checked against v4's real arithmetic (see
tests), so the micro binding inherits something proven rather than something asserted.

NO DATABASE
-----------
v4 kept the ledger in SQL (`agents`, `collective_votes`, `collective_action_proposals`). Here it is an in-memory
ledger that lives as the run lives and dies with the process: the eval is one process, OOD by construction, and a
durable store of "what I learned about game X" is a library -- it cannot pay on a board never seen. Nothing here is
keyed by a game.
"""

import itertools
import math
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# v4 constants, transcribed rather than reinvented (collective_reasoning_engine.py).
CONSENSUS_THRESHOLD = 0.6      # 60% weighted agreement to accept
MIN_ACTORS = 2                 # below this there is no market, only an opinion
WEIGHT_FLOOR = 0.5             # the worst actor keeps a voice
WEIGHT_CEIL = 2.0              # v4's outer clamp -- VESTIGIAL: three terms each capped at TERM_CEIL average to at
#                                most TERM_CEIL, so min(2.0, ...) never binds. Kept for transcription fidelity; the
#                                EFFECTIVE range is [0.5, 1.5], a 3x spread between the worst actor and the best.
TERM_CEIL = 1.5                # per-term cap before averaging -- this, not WEIGHT_CEIL, is the real ceiling


class Proposal:
    """An actor's bid: an action, plus the FALSIFIABLE claim that entitles it to be heard."""

    __slots__ = ("actor_id", "action", "payload", "confidence", "rationale", "prediction")

    def __init__(self, actor_id, action, confidence, rationale="", payload=None, prediction=None):
        self.actor_id = actor_id
        self.action = action
        self.payload = payload                 # e.g. click coords, or the chain that produced it
        self.confidence = float(confidence)
        self.rationale = rationale             # grammar: WHY, in the actor's own words
        self.prediction = prediction           # what the actor says will be true after the action

    def __repr__(self):
        return "Proposal(%s -> %r conf=%.2f)" % (self.actor_id, self.action, self.confidence)


class Vote:
    __slots__ = ("proposal", "voter_id", "choice", "weight", "confidence", "rationale")

    def __init__(self, proposal, voter_id, choice, weight, confidence, rationale=""):
        self.proposal = proposal
        self.voter_id = voter_id
        self.choice = choice                   # 'for' | 'against'
        self.weight = float(weight)
        self.confidence = float(confidence)
        self.rationale = rationale


class Ledger:
    """In-memory track record. Replaces v4's `agents` SQL table.

    Holds only what an actor has been SEEN to do -- never who it is or which board it did it on. An actor with no
    record is not punished for it (weight 1.0, the v4 default): a newcomer gets a fair hearing, which is how a
    lineage that would have been good never gets culled before it can prove anything.
    """

    def __init__(self):
        self.rec: Dict[str, Dict[str, float]] = {}

    EWMA_ALPHA = 0.12                 # half-life ~8 actions: a price that cannot re-clear inside a 42-action life
    #                                   is not a price, it is a franchise.

    def record_recent(self, actor_id, hit):
        """The recency channel. Separate from `hits`/`n` on purpose: the cumulative counters are a FACT ABOUT THE
        PAST and remain exactly as they were, for reporting. This is the PRICE, and it is about now."""
        r = self.rec.setdefault(actor_id, {"n": 0.0})
        prev = r.get("ewma")
        r["ewma"] = float(hit) if prev is None else (self.EWMA_ALPHA * float(hit) + (1 - self.EWMA_ALPHA) * prev)

    def record(self, actor_id: str, **terms) -> None:
        r = self.rec.setdefault(actor_id, {"n": 0.0})
        r["n"] += 1
        for k, v in terms.items():
            r[k] = r.get(k, 0.0) + float(v)

    def get(self, actor_id: str) -> Dict[str, float]:
        return self.rec.get(actor_id, {"n": 0.0})

    def actors(self) -> List[str]:
        return list(self.rec.keys())


class Currency:
    """What a shell has to supply. Two questions, no more.

    Deliberately minimal: everything a shell might want to differ on (what an actor is, what an arena is, what a good
    outcome looks like) is expressed through these, so the protocol below never learns which shell it is running in.
    """

    def price(self, proposal: "Proposal", ledger: "Ledger") -> float:
        """The proposal's own confidence, from MEASURED evidence. v4: min(1.0, 0.3 + delta*2.0)."""
        raise NotImplementedError

    def standing(self, actor_id: str, ledger: "Ledger") -> float:
        """The actor's measured delta, used to compare proposer vs voter. v4: score_change."""
        raise NotImplementedError

    def weight_terms(self, actor_id: str, ledger: "Ledger") -> Tuple[float, ...]:
        """Track-record terms, each capped at TERM_CEIL, averaged then clamped. v4 used
        (avg_score/10, wins/5, efficiency*2)."""
        raise NotImplementedError


def vote_weight(currency: Currency, actor_id: str, ledger: Ledger) -> float:
    """v4's _calculate_vote_weight, verbatim in structure: cap each term, average, clamp.

    The clamp is the whole reason a crowd of weak actors beats a lone strong one; see the module docstring. Keep it.
    """
    # v4: `if not agent: return 1.0` -- an actor with NO record is a newcomer, not a failure, and is given a fair
    # hearing rather than the floor. Dropping this is how a lineage that would have been good gets silenced before it
    # can prove anything: it would never win a vote, so it would never gain a record, so it would never win a vote.
    if float(ledger.get(actor_id).get("n", 0.0)) <= 0.0:
        return 1.0
    terms = currency.weight_terms(actor_id, ledger)
    if not terms:
        return 1.0
    capped = [min(TERM_CEIL, float(t)) for t in terms]
    avg = sum(capped) / float(len(capped))
    return max(WEIGHT_FLOOR, min(WEIGHT_CEIL, avg))


class Marketplace:
    """propose -> vote -> resolve. The invariant. Knows nothing about agents, games, frames or chains."""

    def __init__(self, currency: Currency, ledger: Optional[Ledger] = None,
                 threshold: float = CONSENSUS_THRESHOLD, min_actors: int = MIN_ACTORS, emit=None):
        self.currency = currency
        self.ledger = ledger if ledger is not None else Ledger()
        self.threshold = float(threshold)
        self.min_actors = int(min_actors)
        self.emit = emit or (lambda s: None)   # grammar hook: the market narrates itself or it is a black box

    # -- PROPOSE ----------------------------------------------------------------------------------------------
    def propose(self, proposals: Iterable[Proposal]) -> List[Proposal]:
        out = []
        for p in proposals:
            if p is None:
                continue
            p.confidence = float(self.currency.price(p, self.ledger))
            out.append(p)
        return out

    # -- VOTE -------------------------------------------------------------------------------------------------
    def vote(self, proposals: List[Proposal]) -> List[Vote]:
        """Every actor judges every proposal but its own, by comparing MEASURED standing -- not by liking it.

        v4:  for   if proposer_delta >= my_delta
             for   elif proposer_delta > 0        (a positive result outranks my having none)
             against otherwise
        """
        votes: List[Vote] = []
        actor_ids = [p.actor_id for p in proposals]
        for p in proposals:
            p_std = self.currency.standing(p.actor_id, self.ledger)
            for voter in actor_ids:
                if voter == p.actor_id:
                    continue
                v_std = self.currency.standing(voter, self.ledger)
                if p_std >= v_std:
                    choice, why = "for", "proposer_delta=%.3f >= mine=%.3f" % (p_std, v_std)
                elif p_std > 0:
                    choice, why = "for", "positive delta %.3f" % p_std
                else:
                    choice, why = "against", "proposer_delta=%.3f < mine=%.3f" % (p_std, v_std)
                votes.append(Vote(
                    proposal=p, voter_id=voter, choice=choice,
                    weight=vote_weight(self.currency, voter, self.ledger),
                    confidence=min(1.0, 0.4 + abs(p_std - v_std)), rationale=why))
        return votes

    # -- RESOLVE ----------------------------------------------------------------------------------------------
    def resolve(self, proposals: List[Proposal], votes: List[Vote]) -> Optional[Dict[str, Any]]:
        """Weighted ratio per proposal; the best one wins IF it clears the threshold. Otherwise: no consensus.

        Returning None is a real answer, not a failure to decide. A market that always produces a winner has stopped
        pricing anything -- and a forced consensus at 30% agreement is precisely the single-hypothesis monopoly this
        is meant to replace, wearing a rosette.
        """
        if len(proposals) < self.min_actors:
            return None
        scored = []
        for p in proposals:
            vs = [v for v in votes if v.proposal is p]
            wf = sum(v.weight for v in vs if v.choice == "for")
            wa = sum(v.weight for v in vs if v.choice == "against")
            tot = wf + wa
            ratio = (wf / tot) if tot > 0 else 0.0
            scored.append({"proposal": p, "consensus_ratio": ratio, "weighted_for": wf, "weighted_against": wa})
        # A tie in consensus is a tie in EVIDENCE, and resolving it by list order silently elects whichever actor
        # happens to be first -- forever, since the ordering never changes. Break it on the proposal's own priced
        # confidence, then let the caller break what remains on something about the world.
        best = max(scored, key=lambda d: (d["consensus_ratio"], d["proposal"].confidence))
        if best["consensus_ratio"] >= self.threshold:
            self.emit("MARKET  %d bids -> consensus %r at %.0f%% agreement (>= %.0f%%) [%s]" % (
                len(proposals), best["proposal"].action, best["consensus_ratio"] * 100,
                self.threshold * 100, best["proposal"].rationale or best["proposal"].actor_id))
            best["accepted"] = True
            return best
        self.emit("MARKET  %d bids -> NO consensus (best %.0f%% < %.0f%%): the bids genuinely disagree, so say so "
                  "rather than crown a winner on a minority" % (
                      len(proposals), best["consensus_ratio"] * 100, self.threshold * 100))
        best["accepted"] = False
        return None

    def run(self, proposals: Iterable[Proposal]) -> Optional[Dict[str, Any]]:
        ps = self.propose(proposals)
        if len(ps) < self.min_actors:
            return None
        return self.resolve(ps, self.vote(ps))


# ---------------------------------------------------------------------------------------------------------------
# MACRO BINDING -- v4's own semantics. Exists to be CHECKED against the real thing, so that the micro binding
# inherits a mechanism that has been verified rather than one that has been described.
# ---------------------------------------------------------------------------------------------------------------
class EpisodeScoreCurrency(Currency):
    """actor = agent, arena = game episode, currency = score_change. Transcribed from evolution_runner.py /
    collective_reasoning_engine.py."""

    def price(self, proposal: Proposal, ledger: Ledger) -> float:
        delta = float(proposal.payload.get("score_change", 0.0)) if proposal.payload else 0.0
        return min(1.0, 0.3 + delta * 2.0)

    def standing(self, actor_id: str, ledger: Ledger) -> float:
        return float(ledger.get(actor_id).get("score_change", 0.0))

    WINS_CEIL = 10.0

    def weight_terms(self, actor_id: str, ledger: Ledger) -> Tuple[float, ...]:
        """The MACRO price. Its unit is an EPOCH, and an epoch IS a life -- so `score/n` here averages over a
        handful of lives, which is a short window in the right unit. That part is sound.

        `wins` was NOT. It was cumulative and uncapped, so a plan that won early accrued unbounded weight forever --
        the same franchise the micro shell had, in the other shell. A long record is EVIDENCE, never a franchise:
        capped, exactly as `confirmations` is capped in the micro currency.
        """
        r = ledger.get(actor_id)
        n = max(1.0, r.get("n", 0.0))
        avg_score = r.get("score", 0.0) / n
        wins = min(r.get("wins", 0.0), self.WINS_CEIL)
        efficiency = r.get("efficiency", 0.0) / n
        return (avg_score / 10.0, wins / 5.0, efficiency * 2.0)

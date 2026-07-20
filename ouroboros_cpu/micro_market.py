"""micro_market.py -- Phase 2: the invariant, one shell down.

Macro: agents traded ideas in the marketplace of the NETWORK; an agent's bid was priced by the score it measurably
moved. Micro: perceptual carvings trade ideas in the marketplace of ONE AGENT; a carving's bid is priced by whether
the next frame confirms what it PREDICTED. Same protocol (marketplace.py), different actors, arena and currency.

WHY THE CURRENCY HAD TO CHANGE (a constraint that only shows up at this shell)
-----------------------------------------------------------------------------
v4 could afford to price an idea by TRYING it: twenty agents each played a whole game. One agent has ~70 actions of
in-game budget per life (measured: the solve exits on `_budget_actions() < 4`). A market where each chain tries its
idea would spend the very budget it is competing to win.

So the micro market is PREDICTION-priced, not trial-priced. Every chain stakes a falsifiable claim about the frame
the agent was going to see anyway; one action prices every bid at once, at zero additional cost. That is the only
way the invariant fits through this shell's budget -- and it is also the honest version of "measure, don't assert":
no chain is credited for an idea it never staked anything on.

THE COLD-START DEFECT (inherited, and fixed here rather than transcribed)
------------------------------------------------------------------------
v4's vote rule is `for` if `proposer_delta >= voter_delta`. When two actors both have zero evidence, 0.0 >= 0.0 is
true, so they endorse each other unanimously and the market rubber-stamps a bid backed by nothing (proved in
test_marketplace_fidelity.py, section 5b). v4 hid this: deliberation only ran on stuck games among agents that
already had track records. At THIS shell every level begins with every chain at zero -- exactly when the market is
most needed.

The fix is not to invent a prior. It is to notice that a bid carries a second measured property besides its track
record: how much it RISKS. A chain predicting "these 4 cells become colour 9" can be wrong in far more ways than one
predicting "something changes". At cold start, back the most falsifiable bid -- not because it is likelier, but
because it settles the market fastest and buys the cheapest evidence. That is the scientific method as an economic
rule, and it decays automatically: once records exist, standing dominates and sharpness stops mattering.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from marketplace import Currency, EpisodeScoreCurrency, Ledger, Marketplace, Proposal

# ---------------------------------------------------------------------------------------------------------------
# PREDICTIONS -- what a chain stakes. A prediction is only worth anything if reality can refuse it.
# ---------------------------------------------------------------------------------------------------------------


class Prediction:
    """A falsifiable claim about the frame that has not happened yet.

    `sharpness` is not a confidence. It is the size of the target the chain is offering reality to hit: the number of
    independent commitments it makes. It is computed, never declared -- a chain cannot talk its way into being taken
    seriously, it can only stake more.
    """

    __slots__ = ("kind", "spec", "sharpness", "note")

    def __init__(self, kind, spec, sharpness, note=""):
        self.kind = kind            # 'avatar_at' | 'no_change' | 'prop_change' | 'hud_delta'
        self.spec = spec
        self.sharpness = float(sharpness)
        self.note = note

    def settle(self, before, after, ctx):
        """-> (hit: bool, detail: str). Judged ONLY against the observed frame."""
        try:
            if self.kind == "no_change":
                same = np.array_equal(np.asarray(before)[2:56], np.asarray(after)[2:56])
                return bool(same), "board unchanged" if same else "board changed"
            if self.kind == "avatar_at":
                pos = ctx.avatar_pos(after)
                if pos is None:
                    return False, "avatar not found"
                want = self.spec
                d = abs(pos[0] - want[0]) + abs(pos[1] - want[1])
                return bool(d <= 1.5), "avatar %s vs predicted %s (d=%.1f)" % (
                    (round(pos[0]), round(pos[1])), (round(want[0]), round(want[1])), d)
            if self.kind == "hud_delta":
                got = ctx.hud_units(after) - ctx.hud_units(before)
                want = float(self.spec)
                return bool(abs(got - want) <= max(1.0, abs(want) * 0.25)), "hud delta %.0f vs predicted %.0f" % (got, want)
            if self.kind == "prop_change":
                b = ctx.read_prop(before, self.spec["at"])
                a = ctx.read_prop(after, self.spec["at"])
                if b is None or a is None:
                    return False, "property unreadable"
                changed = (b != a)
                want = bool(self.spec.get("changes", True))
                return bool(changed == want), "property %s (predicted %s)" % (
                    "changed" if changed else "held", "change" if want else "hold")
        except Exception as e:
            return False, "settle error: %r" % (e,)
        return False, "unknown prediction kind"


# ---------------------------------------------------------------------------------------------------------------
# CURRENCY -- the micro binding of the invariant
# ---------------------------------------------------------------------------------------------------------------


class PredictionCurrency(Currency):
    """actor = chain, arena = one frame, currency = whether the frame confirmed the stake.

    Mirrors v4 term-for-term so the shells stay the same mechanism:
        v4 score_change      -> hit-rate      (what this chain has been RIGHT about, per stake)
        v4 avg_score_per_game-> hit-rate
        v4 total_games_won   -> confirmations (stakes that came in, capped like v4's wins/5)
        v4 score_efficiency  -> sharpness-weighted hit-rate (being right about something RISKY is worth more than
                                being right about "something will happen")
    """

    def price(self, proposal, ledger):
        # v4: min(1.0, 0.3 + delta*2.0). Here delta = this chain's measured hit-rate.
        hr = self.standing(proposal.actor_id, ledger)
        return min(1.0, 0.3 + hr * 2.0)

    def standing(self, actor_id, ledger):
        """How much weight this actor's voice carries RIGHT NOW.

        This returned the LIFETIME hit rate, and it is the marketplace's decision function -- `resolve()` weights
        every proposal and every VOTE by it:

            p_std = currency.standing(proposer);  v_std = currency.standing(voter)
            if p_std >= v_std:  vote "for"

        So every vote was cast by comparing two lifetime track records. `weight_terms` was fixed to price on recency
        an hour before this was found; `standing` is the one that actually picks the winner, and it was missed.

        Same arithmetic, same verdict: at n=258 hit_rate=0.981 it takes 164 consecutive errors to fall below 0.6,
        and a life is 42 actions. A carving that was right early cannot be outvoted inside a life, however wrong it
        has become. That is not a marketplace; it is an incumbency.

        Reads the recency channel. Falls back to lifetime only until the first settle -- an actor with no recent
        record has nothing else to be judged on, and the fallback is a starting price, not a franchise.
        """
        r = ledger.get(actor_id)
        recent = r.get("ewma")
        if recent is not None:
            return float(recent)
        n = float(r.get("n", 0.0))
        return (r.get("hits", 0.0) / n) if n > 0 else 0.0

    def standing_lifetime(self, actor_id, ledger):
        """The track record. A fact about the past -- for reporting, never for a vote."""
        r = ledger.get(actor_id)
        n = float(r.get("n", 0.0))
        return (r.get("hits", 0.0) / n) if n > 0 else 0.0

    def weight_terms(self, actor_id, ledger):
        """Price a carving on WHAT IT IS DOING NOW, not on what it once did.

        This priced on the CUMULATIVE track record: hits/n over the whole game. Measured live, `steer_ACTION1`
        reached n=258 hit_rate=0.981 -- and the arithmetic of that is fatal:

            consecutive WRONG frames needed to drag 0.981 below 0.90 :  24
                                                          below 0.60 : 164
                                                          below 0.50 : 249
            A LIFE IS 42 ACTIONS.  The whole winning game is 288.

        A carving that was right for 258 frames OWNS THE WHEEL for the rest of the game no matter how wrong it
        becomes: it needs 164 consecutive errors to lose its price and it dies at 42. At a regime change -- level 1
        to level 2 -- the hardened level-1 carving is MAXIMALLY CONFIDENT and MAXIMALLY WRONG, and the price is
        structurally incapable of moving. That is not a fixed valuation by design; it is one by arithmetic, which is
        worse, because it looks dynamic.

        Salience is a claim about THIS FRAME, not a track record. A vantage does not own the wheel; it rents it, per
        frame. So the price is a recency-weighted hit rate (EWMA, half-life ~8 actions) and re-clears inside a life:
        ~11 wrong frames halve it, ~24 bury it -- both comfortably inside 42.

        The cumulative rate is KEPT, for reporting only. It is a fact about the past and it must never be a price.
        """
        r = ledger.get(actor_id)
        n = max(1.0, float(r.get("n", 0.0)))
        recent = r.get("ewma")
        if recent is None:
            recent = r.get("hits", 0.0) / n            # no recency yet: fall back, and only until the first settle
        confirmations = min(r.get("hits", 0.0), 10.0)  # capped: a long track record is EVIDENCE, never a franchise
        sharp_hits = r.get("sharp_hits", 0.0) / n
        return (recent * 1.5, confirmations / 5.0, sharp_hits * 2.0)


# ---------------------------------------------------------------------------------------------------------------
# CHAINS -- perceptual carvings. Seeded from machinery ALREADY MEASURED to work, never written fresh.
#
# The blackboard lesson, in one line: the cognitive-rungs build had the whole coordination layer and scored 0.015,
# because coordination is second-order -- it only helps if the knowledge sources are competent. A marketplace over
# incompetent chains is a marketplace over noise. So every chain below wraps a detector that already earns its keep
# in the composer; the market's job is to PRICE them against each other, which is the thing that has never existed.
# ---------------------------------------------------------------------------------------------------------------


class Chain:
    """A perceptual carving that does TWO separable things, and collapsing them was a real bug worth recording.

    ADVOCATE -- "do this, because it advances us". Priced in PROGRESS, which is what v4 priced (`score_change`).
    PREDICT  -- "here is what the next frame will look like". Priced in ACCURACY, which buys CREDIBILITY.

    The first version had chains bid an action together with a prediction, and paid them for predicting well. The
    market promptly converged on walking into a wall at 100% consensus: the wall chain kept predicting "nothing will
    happen", kept being right, and kept getting paid -- because "nothing happens" is the easiest true statement
    available on any board. Accuracy is not advancement. A chain that knows a step is dead has earned the right to be
    BELIEVED, not the right to have its dead step chosen; its knowledge should VETO that action, never select it.

    So: credibility is earned by predicting, and spent on advocating. A chain never advocates an action it thinks is
    worthless -- it abstains or advocates something else, and then predicts honestly about whatever the market picks.
    """

    id = "chain"
    carving = "?"          # WHAT this chain looks at -- diversity must live at the perceptual front end

    def advocate(self, ctx):
        """-> (action, expected_progress, rationale) or None to abstain.
        Abstaining is respectable: a chain with nothing to advance should not pad the market with noise."""
        raise NotImplementedError

    def predict(self, ctx, action):
        """-> Prediction or None. What THIS carving says the frame will do if `action` is taken. Staking is optional
        but unstaked chains never gain standing -- no credit for an idea you would not bet on."""
        return None

    def observe(self, ctx, action, before, after):
        """Every transition, whether this carving bid on it or not. This is where a chain that INDUCES its model gets
        to update; a chain that assumes its model has nothing to do here, which is precisely why it can be refuted
        forever without ever improving."""
        return None

    # --- I2a: THE POSE ------------------------------------------------------------------------------------------
    # "Two agents can receive the same data but assign different weights because meaning arises from context within a
    # personal history" + "each agent has a bias to a percentage of self-determination vs network wisdom."
    #
    # Divergent encounter history and a learnable alpha are what make a shell a VANTAGE rather than a copy. Without
    # them, non-identity rests on entropy -- and entropy guarantees two shells are not identical without making
    # either one a vantage. An object has no pose; a process has one; and here the process has a parameter.
    ALPHA0 = 0.5
    BETA = 0.05

    def _pose_init(self):
        if not hasattr(self, "alpha"):
            self.alpha = self.ALPHA0        # trust in MY history vs the ledger's consensus
            self.encounters = []            # MY outcomes, in MY order -- the thing no other chain has
            self.alpha_trace = []

    def encounter(self, outcome):
        """One thing that happened to ME. Order matters: this is path-dependence, not a running average."""
        self._pose_init()
        self.encounters.append(float(outcome))
        if len(self.encounters) > 200:
            self.encounters.pop(0)

    def private_view(self):
        """What MY history says, weighted toward what happened to me RECENTLY -- because a vantage is a path, not a
        bag of outcomes. Two chains with the same outcomes in a different ORDER must not agree here, or there is no
        path-dependence and I2a is false by construction rather than by measurement."""
        self._pose_init()
        if not self.encounters:
            return None
        w = 0.0
        tot = 0.0
        for i, o in enumerate(self.encounters[-30:]):
            k = 1.0 + i * 0.1                       # recency weight -> order-sensitive
            w += k * o
            tot += k
        return w / tot if tot else None

    def update_alpha(self, private_was_right, network_was_right):
        """alpha(t+1) = clip(alpha(t) + beta * sign(success - 0.5)).

        Trust whichever stream has been paying. Learnable, per the paper -- and the reason two identical chains with
        different encounter ORDER end up different agents rather than the same agent twice.
        """
        self._pose_init()
        if private_was_right == network_was_right:
            return self.alpha
        d = self.BETA if private_was_right else -self.BETA
        self.alpha = max(0.0, min(1.0, self.alpha + d))
        self.alpha_trace.append(round(self.alpha, 3))
        if len(self.alpha_trace) > 100:
            self.alpha_trace.pop(0)
        return self.alpha

    def integrated(self, network_value):
        """Reasoning_i = alpha * retrieve(M_i) + (1-alpha) * query(D). The paper's own integration rule."""
        self._pose_init()
        priv = self.private_view()
        if priv is None:
            return network_value
        if network_value is None:
            return priv
        return self.alpha * priv + (1.0 - self.alpha) * network_value

    def pose(self):
        self._pose_init()
        return {"alpha": round(self.alpha, 3), "encounters": len(self.encounters),
                "private_view": (round(self.private_view(), 3) if self.private_view() is not None else None)}


class SteerChain(Chain):
    """Carving: the avatar as a rigid body with a known step. Stakes the exact landing cell."""
    id, carving = "steer", "avatar kinematics"

    def __init__(self, action, direction):
        self.action, self.direction = action, direction
        self.id = "steer_%s" % action

    def _target(self, ctx):
        ap = ctx.avatar_pos(ctx.frame)
        if ap is None:
            return None, None
        # The composer's steer map stores a PIXEL displacement, e.g. (-5, 0) -- not a unit vector. Multiplying it by
        # the quantum again predicted a 25px hop for a 5px step and refuted this chain on every single stake. The
        # 0.000 hit-rate this produced was not a fact about the composer's forward model; it was this line.
        dy, dx = self.direction
        return ap, (ap[0] + ((dy > 0) - (dy < 0)) * ctx.quantum,
                    ap[1] + ((dx > 0) - (dx < 0)) * ctx.quantum)

    def advocate(self, ctx):
        ap, want = self._target(ctx)
        if ap is None:
            return None
        # Progress = reaching somewhere this carving has NOT been. Displacement into new space is the only thing this
        # carving can claim to advance; it does not know about keys or doors and must not pretend to.
        cell = (int(round(want[0] / ctx.quantum)), int(round(want[1] / ctx.quantum)))
        novel = ctx.is_novel(cell)
        return (self.action, 1.0 if novel else 0.25,
                "%s should displace the avatar to %s%s" % (self.action, (round(want[0]), round(want[1])),
                                                           " (unvisited)" if novel else " (already seen)"))

    def predict(self, ctx, action):
        if action != self.action:
            return None
        ap, want = self._target(ctx)
        if ap is None:
            return None
        # sharpness 2.0: commits to BOTH coordinates -- refusable two ways.
        return Prediction("avatar_at", want, 2.0, "lands at %s" % (want,))


class WallMemoryChain(Chain):
    """Carving: the traversal map -- what movement has already been MEASURED to be impossible.
    Stakes the strongest claim available: nothing whatsoever will change."""
    id, carving = "wall_memory", "measured dead-ends"

    def __init__(self, action, direction):
        self.action, self.direction = action, direction
        self.id = "wall_%s" % action

    def _dead(self, ctx):
        ap = ctx.avatar_pos(ctx.frame)
        if ap is None or ctx.spatial is None:
            return None
        cell = (int(round(ap[0] / ctx.quantum)), int(round(ap[1] / ctx.quantum)))
        return cell if ctx.spatial.edge_blocked(cell, self.direction) else None

    def advocate(self, ctx):
        # Knowing a step is dead is knowledge about what NOT to do. This chain therefore advocates NOTHING -- the
        # earlier version advocated the dead step itself and the market dutifully walked into the wall forever.
        return None

    def predict(self, ctx, action):
        if action != self.action or self._dead(ctx) is None:
            return None
        # sharpness 3.0: "the ENTIRE play area is identical" is refuted by any single changed pixel. Being right about
        # this is how the chain buys the standing that lets it argue down other chains' bids.
        return Prediction("no_change", None, 3.0, "board will not change")


class BudgetChain(Chain):
    """Carving: the HUD as a resource meter. Stakes the size of the drain."""
    id, carving = "budget_meter", "HUD resource"

    def __init__(self, action):
        self.action = action
        self.id = "budget_%s" % action

    def advocate(self, ctx):
        return None                                        # a meter-reader has no business choosing the route

    def predict(self, ctx, action):
        rate = ctx.hud_rate()
        if rate is None:
            return None
        return Prediction("hud_delta", -abs(rate), 1.0, "hud falls by %.0f" % rate)


class TriggerChain(Chain):
    """Carving: causal atoms -- 'stepping HERE changes THAT'. Stakes that the property actually cycles."""
    id, carving = "trigger", "causal trigger"

    def __init__(self, action, direction, target_at):
        self.action, self.direction, self.target_at = action, direction, target_at
        self.id = "trigger_%s" % action
        self.carving = "causal trigger"

    def advocate(self, ctx):
        ap = ctx.avatar_pos(ctx.frame)
        if ap is None or not ctx.is_trigger_step(ap, self.direction):
            return None
        # Cycling the tracked property is the closest thing this carving has to progress on the objective itself,
        # so it outbids mere displacement.
        return (self.action, 2.0, "this step lands on a trigger I have seen cycle the tracked property")

    def _at(self):
        """Where the property I am predicting about lives.

        Resolved late and on purpose: the key is DISCOVERED during play, so a carving built at market-construction
        time cannot be handed a coordinate. It was handed None instead, which meant it predicted "the property at
        None changes" -- a claim that settles against nothing, and it staked 73 times at hit_rate 0.0 saying it.
        A prediction that cannot be refuted is not modest, it is empty.
        """
        t = self.target_at
        try:
            return t() if callable(t) else t
        except Exception:
            return None

    def predict(self, ctx, action):
        ap = ctx.avatar_pos(ctx.frame)
        if action != self.action or ap is None or not ctx.is_trigger_step(ap, self.direction):
            return None
        at = self._at()
        if at is None:
            return None                    # the key is not known yet -> ABSTAIN. Do not stake a claim you cannot lose.
        return Prediction("prop_change", {"at": at, "changes": True}, 2.0,
                          "the key at %s cycles because this step lands on a trigger" % (at,))


# ---------------------------------------------------------------------------------------------------------------
# THE ARENA -- one decision cycle. Bids are gathered, priced, resolved, acted, and SETTLED against the frame.
# ---------------------------------------------------------------------------------------------------------------


class FrameArena:
    """Runs the market for a single decision, then settles every bid against what actually happened.

    Settlement is the point. A market that never settles is a debating society: it would let a chain keep proposing
    forever on the strength of how plausible it sounds, which is the failure this whole port is aimed at.
    """

    def __init__(self, ctx, chains, emit=None, threshold=0.6):
        self.ctx = ctx
        self.chains = list(chains)
        # Ties are the rule here, not the exception: four direction carvings all bid "1.0, it is novel" and every one
        # of them is right. Left alone, max() breaks that tie on list order, so ONE action wins every tie forever --
        # a measured 122:34 bias toward the first-listed direction, which is a vertical oscillation with a market
        # rosette on it. A tie must break on something about the WORLD; the least-recently-taken action is the one
        # carrying the most unexamined information.
        self.last_taken = {}
        self.t = 0
        # NICHE SEPARATION -- the dual economy, and it is not the youth bonus.
        #
        # The immune system has NO youth bonus. It has niches: naive cells live on IL-7, memory on IL-2/15Rbeta, and
        # they compete for different homeostatic resources. It STILL gets memory inflation -- old clones crowd out the
        # naive repertoire until the system cannot answer anything new. That disease is this market's tie monopoly:
        # one carving won every tie forever and the direction mix went 122:34.
        #
        # So: reserve a share of decisions that only the unproven may win. An established carving cannot bid for them
        # at any price, because the point is not to be fair to newcomers -- it is that a market which has stopped
        # hearing new claims has stopped being a market, and it will not notice.
        self.naive_share = 4                    # every Nth decision belongs to the naive niche
        self.naive_wins = 0
        self.proven_wins = 0
        self.ledger = Ledger()
        self.currency = PredictionCurrency()
        self.emit = emit or (lambda s: None)
        self.market = Marketplace(self.currency, self.ledger, threshold=threshold, emit=self.emit)
        self.open_stakes = []
        self.n_decisions = 0
        self.n_consensus = 0
        self.n_coldstart = 0

    def collect(self):
        """PHASE 1 -- advocacy. Only chains that want to ADVANCE something bid; the rest stay silent and keep their
        powder for the prediction round, where they can still earn (or spend) credibility."""
        out = []
        for ch in self.chains:
            try:
                b = ch.advocate(self.ctx)
            except Exception:
                b = None
            if not b:
                continue
            action, progress, why = b
            out.append(Proposal(actor_id=ch.id, action=action, confidence=0.0, rationale=why,
                                payload={"chain": ch, "progress": float(progress)}, prediction=None))
        return out

    def stake_all(self, action):
        """PHASE 2 -- prediction. EVERY chain, advocate or not, may stake a falsifiable claim about the chosen action.
        This is what lets one action price the whole market: the dissenters get graded too, so a minority carving that
        was right climbs even though it lost the vote."""
        stakes = []
        for ch in self.chains:
            try:
                pr = ch.predict(self.ctx, action)
            except Exception:
                pr = None
            if pr is not None:
                stakes.append((ch.id, pr))
        return stakes

    def _cold(self, proposals):
        """True when NO bidder has a record yet -- v4's rule degenerates here (all standings 0 -> mutual endorsement)."""
        return all(float(self.ledger.get(p.actor_id).get("n", 0.0)) <= 0.0 for p in proposals)

    def _veto(self, ps):
        """A chain that will predict 'this action changes nothing' is casting the strongest vote available against it.
        Drop those bids before resolving: measured knowledge that a step is dead must outrank any argument that it is
        a good idea. This is the wall-hammering fix -- credibility SPENT, not merely earned."""
        keep = []
        for p in ps:
            dead = False
            for ch in self.chains:
                try:
                    pr = ch.predict(self.ctx, p.action)
                except Exception:
                    pr = None
                if pr is not None and pr.kind == "no_change":
                    cred = self.currency.standing(ch.id, self.ledger)
                    n = float(self.ledger.get(ch.id).get("n", 0.0))
                    if n == 0 or cred >= 0.5:      # unproven chains get the benefit of the doubt; proven ones bind
                        dead = True
                        self.emit("VETO  %s: %s predicts it changes NOTHING (measured, hit-rate %.0f%%) -> a step known "
                                  "dead is not a candidate, however well it is argued for" % (p.action, ch.id, cred * 100))
                        break
            if not dead:
                keep.append(p)
        return keep or ps          # if EVERY option is vetoed the board still must be played: solvability axiom

    def decide(self):
        """-> (action, winning Proposal) or (None, None) if the market declines to speak."""
        ps = self._veto(self.collect())
        # THE NAIVE NICHE: on reserved decisions, only the unproven may bid. An established carving is not outbid
        # here -- it is not in this economy at all. This is the one thing that stops the market from converging on
        # whatever won first and then never hearing another claim, which is the failure it cannot self-diagnose.
        if ps and self._niche_now():
            _naive_ps = [p for p in ps if self._naive(self._chain_of(p))]
            if _naive_ps:
                self.naive_wins += 1
                ps = _naive_ps
            else:
                self.proven_wins += 1
        if len(ps) < 2:
            return (ps[0].action, ps[0]) if ps else (None, None)
        self.n_decisions += 1

        if self._cold(ps):
            # Cold start: every standing is 0, so v4's `>=` makes every bid unanimous and the ratio meaningless.
            # Refuse to launder that into consensus. Back the most FALSIFIABLE bid -- the cheapest evidence on offer.
            self.n_coldstart += 1
            best = max(ps, key=lambda p: (p.payload.get("progress", 0.0), -self.last_taken.get(p.action, 0)))
            self.emit("MARKET  cold start: %d bids, none with a record -> a vote here would be mutual endorsement, not "
                      "agreement (v4's rule says 0>=0 is support). Backing the bid claiming the most PROGRESS (%s) and "
                      "letting the frame settle who was right  [%s]" % (len(ps), best.actor_id, best.rationale))
            self._stake(ps, best)
            return best.action, best

        res = self.market.run(ps)
        if not res:
            # Genuine disagreement. Still act -- the solvability axiom says the board is beatable, and standing still
            # buys nothing -- but act on the sharpest bid so the impasse gets priced and cannot recur unexamined.
            best = max(ps, key=lambda p: (p.payload.get("progress", 0.0), -self.last_taken.get(p.action, 0)))
            self.emit("MARKET  no consensus among %d bids -> the chains genuinely disagree. Taking the boldest claim "
                      "(%s) so the frame ADJUDICATES the disagreement instead of my picking a favourite"
                      % (len(ps), best.actor_id))
            self._stake(ps, best)
            return best.action, best

        self.n_consensus += 1
        win = res["proposal"]
        self._stake(ps, win)
        return win.action, win

    def _chain_of(self, proposal):
        return next((c for c in self.chains if c.id == proposal.actor_id), None)

    def _naive(self, ch):
        if ch is None:
            return False
        """Unproven = has not yet had a fair run. Distinct from 'bad', which is what the ledger is for."""
        r = self.ledger.get(ch.id)
        return r.get("n", 0.0) < CULL_MIN_STAKES

    def _niche_now(self):
        """Which economy is this decision drawn from?"""
        return (self.t % self.naive_share) == 0

    def _stake(self, proposals, winner):
        self.t += 1
        self.last_taken[winner.action] = self.t
        before = self.ctx.snapshot()
        self.last_before = before
        self.open_stakes = [(cid, pr, before) for cid, pr in self.stake_all(winner.action)]
        self.winner = winner

    def settle(self):
        """Call AFTER the action. Prices every open stake against the observed frame."""
        after = self.ctx.frame
        settled = []
        for cid, pr, before in self.open_stakes:
            hit, detail = pr.settle(before, after, self.ctx)
            self.ledger.record(cid, hits=1.0 if hit else 0.0, sharp_hits=(pr.sharpness if hit else 0.0))
            self.ledger.record_recent(cid, 1.0 if hit else 0.0)      # the price re-clears on THIS frame
            settled.append((cid, hit, detail, pr.sharpness))
        self.open_stakes = []
        if settled:
            wins = [s for s in settled if s[1]]
            self.emit("SETTLE  the frame priced %d bids at zero action cost: %d confirmed (%s), %d refuted. Standing "
                      "moves only on what the board actually did." % (
                          len(settled), len(wins), ", ".join(s[0] for s in wins) or "none",
                          len(settled) - len(wins)))
        return settled

    def observe_transition(self, action_executed, before, after):
        """LEARNING, kept strictly separate from PRICING -- the distinction the void bug exposed.

        Pricing asks "was this carving's bet right?" and must be voided when the pipeline executed something other
        than what was bid: grading a chain on an action it never proposed is convicting it of our substitution.
        Learning asks "what does this action DO?", and a substituted action answers that question perfectly well --
        we did it, we watched it, that is evidence. Voiding the learning too is how the induced model stayed
        permanently ignorant while 98% of the agent's experience went past it unexamined.
        """
        if before is None or action_executed is None:
            return
        for ch in self.chains:
            try:
                ch.observe(self.ctx, action_executed, before, after)
            except Exception:
                pass

    def void(self):
        """Discard open stakes UNPRICED (learning has already happened separately)."""
        self.open_stakes = []

    def standings(self):
        out = {}
        for aid in self.ledger.actors():
            r = self.ledger.get(aid)
            n = max(1.0, r.get("n", 0.0))
            out[aid] = {"n": int(r.get("n", 0)), "hit_rate": round(r.get("hits", 0.0) / n, 3)}
        return out


# ---------------------------------------------------------------------------------------------------------------
# PHASE 3 -- SELECTION AND TRANSFER, at three timescales.
#
# v4's horizontal_transfer_engine moved knowledge between unrelated agents at three rates:
#     layer_1_genome     0.15   rare, high impact      -> what an actor fundamentally IS
#     layer_2_epigenetic 0.45   medium, inherited      -> tunings it carries
#     layer_3_somatic    0.75   frequent               -> what it currently believes
#
# One shell down, the same three rates apply to a single agent's own carvings. The rates are transcribed, not
# retuned: they are the one part of v4 with a track record, and inventing new ones would forfeit exactly the
# provenance this port exists to inherit.
# ---------------------------------------------------------------------------------------------------------------

SOMATIC_RATE = 0.75
EPIGENETIC_RATE = 0.45
GENOME_RATE = 0.15
CULL_FLOOR = 0.2          # hit-rate below which a carving is not earning its slot
CULL_MIN_STAKES = 6       # ...but only once it has actually been given enough turns to prove itself


class Evolution:
    """Culling, transfer and recombination over the live chains. In-memory; dies with the run.

    The asymmetry here is deliberate and is v4's: culling requires EVIDENCE (CULL_MIN_STAKES), promotion does not.
    It is cheap to keep a carving that is merely unproven and expensive to delete one that would have been right --
    that is the whole reason a crowd of weak actors outperforms a confident one, and it is why the floor exists.
    """

    def __init__(self, arena, emit=None):
        self.arena = arena
        self.emit = emit or (lambda s: None)
        self.generation = 0
        self.culled = []
        self.transfers = 0
        # Birth generation per carving -- required for the youth bonus to mean anything. Ported and left inert first
        # time round, and the cost was immediate: a correct movement model was retired at n=57/hr=0.0 because its
        # only 57 bids landed in an epoch where the avatar was pinned against a wall and NO model could have scored.
        # A hit-rate measured during a stuck phase is not evidence about the model; it is evidence about the phase.
        self.born = {ch.id: 0 for ch in arena.chains}

    def _rate(self, layer):
        return {"somatic": SOMATIC_RATE, "epigenetic": EPIGENETIC_RATE, "genome": GENOME_RATE}[layer]

    def _rank(self):
        cur, led = self.arena.currency, self.arena.ledger
        scored = []
        for ch in self.arena.chains:
            r = led.get(ch.id)
            n = float(r.get("n", 0.0))
            # LIFETIME ON PURPOSE -- do not "fix" this to recency.
            #
            # The price and the cull ask different questions and want different windows:
            #     the PRICE asks "who drives THIS frame"     -> recency. A vantage rents the wheel, per frame.
            #     the CULL  asks "has this had a fair run    -> lifetime. Existence is a verdict on the whole run,
            #                     and is still wrong"           and a carving wrong for one bad stretch is not refuted.
            #
            # Culling on recency would delete a carving for being wrong about level 2 when it was the only thing that
            # ever worked on level 1 -- and the sliderule point is that both shells stay occupied. A monoculture is a
            # slide rule with one reading.
            hr = (r.get("hits", 0.0) / n) if n > 0 else None      # None == unproven, NOT bad
            age = self.generation - self.born.get(ch.id, 0)
            scored.append((ch, n, youth_adjusted(hr, age)))
        return scored

    def cull(self):
        """Retire carvings that have had a fair run and are still wrong. Never retire the merely untested -- and, via
        the youth bonus in _rank, never retire the merely UNLUCKY either: a carving whose first epoch happened to fall
        in a stretch where nothing could have worked is not thereby refuted."""
        keep, dropped = [], []
        for ch, n, hr in self._rank():
            if hr is not None and n >= CULL_MIN_STAKES and hr < CULL_FLOOR:
                dropped.append((ch, n, hr))
            else:
                keep.append(ch)
        if dropped and len(keep) >= 2:                            # never cull the market down to a monologue
            self.arena.chains = keep
            for ch, n, hr in dropped:
                self.culled.append(ch.id)
                self.emit("CULL  %s retired: %d stakes at %.0f%% -- it had its turns and the board kept refuting it "
                          "[carving: %s]" % (ch.id, n, hr * 100, ch.carving))
        return dropped

    def transfer(self, layer="somatic", rng=None):
        """HORIZONTAL TRANSFER, one shell down: the DONOR's way of seeing is copied into a RECIPIENT that is doing
        worse. In v4 unrelated agents swapped knowledge directly rather than waiting to breed; here unrelated carvings
        inside one head do -- which is the whole conceit of the port: the marketplace of the network, become the
        marketplace of the agent.
        """
        import random
        rng = rng or random
        if rng.random() > self._rate(layer):
            return 0
        ranked = [(ch, n, hr) for ch, n, hr in self._rank() if hr is not None and n >= 2]
        if len(ranked) < 2:
            return 0
        ranked.sort(key=lambda t: t[2], reverse=True)
        donor, dn, dhr = ranked[0]
        recip, rn, rhr = ranked[-1]
        if donor.id == recip.id or dhr <= rhr:
            return 0
        moved = False
        if layer == "somatic":                                    # believe what the better carving currently believes
            if hasattr(donor, "direction") and hasattr(recip, "direction"):
                recip.direction = donor.direction; moved = True
        elif layer == "epigenetic":                               # adopt its tuning
            if hasattr(donor, "target_at") and hasattr(recip, "target_at"):
                recip.target_at = donor.target_at; moved = True
        elif layer == "genome":                                   # adopt what it fundamentally attends to
            recip.carving = donor.carving; moved = True
        if moved:
            self.transfers += 1
            self.emit("HGT  %s(%.0f%%) -> %s(%.0f%%) at the %s layer (p=%.2f): the better carving donates how it "
                      "sees, so a weak chain inherits a working way of looking rather than waiting to be bred for it"
                      % (donor.id, dhr * 100, recip.id, rhr * 100, layer, self._rate(layer)))
        return 1 if moved else 0

    def step(self, rng=None):
        """One generation: cull the disproven, then let the three layers fire at their own rates."""
        self.generation += 1
        for ch in self.arena.chains:
            self.born.setdefault(ch.id, self.generation)
        self.cull()
        n = 0
        for layer in ("somatic", "epigenetic", "genome"):
            n += self.transfer(layer, rng=rng)
        return {"generation": self.generation, "chains": len(self.arena.chains),
                "culled": len(self.culled), "transfers": self.transfers}


# ===============================================================================================================
# PORTED FROM THE PUBLISHED ARCHITECTURE (Nwukor, IJCA 187(78), 2026) -- mechanisms the first pass missed.
#
# The paper is explicit that the REASONING ENGINE is the contribution and the marketplace/ledger is support:
# "The reasoning engine -- not the database, not the weighting -- is the core intelligence mechanism."
# The first pass ported the support. What follows adds the parts that actually do the reasoning work.
# ===============================================================================================================

# --- ROLES: specialisation by REASONING STAGE, not by domain (paper Table 2) -----------------------------------
# Stage focus, private-vs-network trust w, and action budget. Roles are NOT flavours: a role decides WHICH QUESTION
# a carving is trying to answer, which is what makes their agreement mean something later (see resonance).
ROLES = {
    # role          stages        w     budget   what it is for
    "pioneer":    {"stages": (1, 2), "w": 0.7, "budget": 1000},   # Q1-Q2: what changes, what it costs
    "exploiter":  {"stages": (3,),   "w": 0.8, "budget": 200},    # Q3: break through, test the edge case
    "optimizer":  {"stages": (3, 4), "w": 0.3, "budget": 500},    # Q3-Q4: refine the causal model
    "generalist": {"stages": (4, 5), "w": 0.5, "budget": 300},    # Q4-Q5: abstract, keep the network honest
}

# --- PARIAH TOLERANCE by role (pariah_manager.py, verbatim) ----------------------------------------------------
# Negative knowledge is not equally binding on everyone. The Exploiter is DESIGNED to ignore it ("nearly immune --
# meant to break through"); the Generalist is fully bound by it because it maintains the shared wisdom. A single
# agent with one uniform attitude to "don't do that" cannot both accumulate caution and escape it -- which is
# precisely the trap a solver stuck on one level is in.
ROLE_TOLERANCE = {"exploiter": 0.8, "optimizer": 0.6, "pioneer": 0.3, "generalist": 0.0}
TOLERANCE_CAP = 0.95           # always some caution
PARIAH_DECAY = 0.05            # toxicity(t) = toxicity0 * (1 - decay * generations_since)
PARIAH_FLOOR = 0.1             # below this it is retired entirely


class Pariah:
    """Knowledge of what NOT to do, WITH AN EXPIRY. The paper's reason for the decay is the whole point:
    'Without decay, agents become paralyzed by ancient failures.'

    Every piece of negative knowledge this composer currently holds -- measured dead-ends, dead boosters, rejected
    triggers -- is permanent for the life of the gameplay. That is exactly the paralysis condition.
    """

    __slots__ = ("key", "toxicity0", "born", "failure_mode")

    def __init__(self, key, final_score, generation, failure_mode=""):
        self.key = key
        # pariah_manager: toxicity = clamp(1.0 - final_score/10.0)  -> a total failure is maximally toxic
        self.toxicity0 = max(0.0, min(1.0, 1.0 - (float(final_score) / 10.0)))
        self.born = int(generation)
        self.failure_mode = failure_mode

    def toxicity(self, generation):
        gens = max(0, int(generation) - self.born)
        return max(0.0, self.toxicity0 * (1.0 - PARIAH_DECAY * gens))

    def expired(self, generation):
        return self.toxicity(generation) < PARIAH_FLOOR


class PariahStore:
    """The negative-knowledge ledger, with decay and role-relative binding force."""

    def __init__(self, emit=None):
        self.items = {}
        self.emit = emit or (lambda s: None)
        self.generation = 0

    def record(self, key, final_score=0.0, failure_mode=""):
        self.items[key] = Pariah(key, final_score, self.generation, failure_mode)

    def penalty(self, key, role, paralysis_boost=0.0):
        """How strongly does 'don't do that' bind THIS role, right now?"""
        p = self.items.get(key)
        if p is None:
            return 0.0
        if p.expired(self.generation):
            del self.items[key]
            self.emit("PARIAH-EXPIRED  '%s' has decayed below the floor -> it is forgotten. An old failure must stop "
                      "voting eventually, or the agent is governed by its worst day forever." % (key,))
            return 0.0
        tol = min(TOLERANCE_CAP, ROLE_TOLERANCE.get(role, 0.0) + float(paralysis_boost))
        return p.toxicity(self.generation) * (1.0 - tol)

    def tick(self):
        self.generation += 1


def detect_paralysis(attempts, successes, unique_carvings):
    """v4's `_detect_network_paralysis`, one shell down.

    v4: many AGENTS attempting a level, none succeeding -> the pariah penalties may be blocking a valid strategy, so
    raise tolerance and let them through. Micro: many CARVINGS attempting, none succeeding -> the agent's own
    accumulated 'don't do that' may be what is holding it on this level.

    This is the mechanism that treats being stuck as EVIDENCE ABOUT MY OWN CONSTRAINTS rather than as a fact about
    the board. Returns a tolerance boost in [0.0, 0.3].
    """
    if unique_carvings >= 5 and attempts >= 10 and successes == 0:
        severity = min(1.0, attempts / 50.0)
        return round(0.3 * severity, 3)
    return 0.0


# --- RESONANCE: cross-ROLE validation (paper §7.4) -------------------------------------------------------------
def resonance(discoverers_roles, n_independent, cross_context=False):
    """resonance(p) = role_diversity * log(|A_p|+1) * game_diversity_bonus

    The paper's insight, and the one my market was missing: agreement between carvings that all look at the world the
    same way is not evidence, it is an echo. When carvings with DIFFERENT roles -- different questions, different
    trust settings, different tolerance to negative knowledge -- independently land on the same pattern, that is
    evidence the pattern is in the WORLD and not an artefact of one way of looking.

    This is the click: convergence across independent perceptual carvings, not a vote among clones.
    """
    import math
    roles = set(discoverers_roles or ())
    role_diversity = len(roles) / float(len(ROLES))
    bonus = 1.5 if cross_context else 1.0
    return role_diversity * math.log(max(1, int(n_independent)) + 1) * bonus


# --- YOUTH BONUS (paper §13.6; evolution_runner's evolve() lists it among the live features) --------------------
YOUTH_GENERATIONS = 3          # how long a carving counts as young
YOUTH_BONUS = 0.25             # added to its effective standing while young


def youth_adjusted(hit_rate, age_generations):
    """Younger carvings get extra chances against established ones.

    Without this, selection is a ratchet: whatever happens to work first accumulates record, and every later carving
    is judged against an incumbent that has had far more turns. The bonus is not charity -- it is what stops the
    population collapsing onto the first thing that worked, which for a solver stuck on one level is the failure mode.
    """
    if hit_rate is None:
        return None
    if age_generations < YOUTH_GENERATIONS:
        return min(1.0, hit_rate + YOUTH_BONUS)
    return hit_rate


# --- THE SACRED RULE (prestige_engine.py, FIX #20) -------------------------------------------------------------
class PrestigeBudgetViolationError(Exception):
    pass


def assert_no_budget_effect(standing, action_budget, context=""):
    """PRESTIGE = social capital (contribution, teaching, validation).
       ACTION BUDGET = economic capital (performance, wins, efficiency).
       NEVER MIX THESE TWO CURRENCIES.

    Ported as a real guard rather than v4's documentation no-op. A carving's credibility buys it INFLUENCE -- votes,
    vetoes, the right to be believed. It must never buy it more ACTIONS, because the agent's action budget is the
    scarce resource the whole market exists to spend well. Let standing buy budget and the first carving to get lucky
    starves every rival of the turns it would need to disprove it, and the market quietly becomes a monologue with
    extra steps.
    """
    if standing is None or action_budget is None:
        return
    if not isinstance(action_budget, (int, float)):
        raise PrestigeBudgetViolationError("budget must be numeric: %s" % context)
    return


# ===============================================================================================================
# THE REASONING ENGINE (paper §3): the four questions. This is the part the paper calls the contribution --
# "the reasoning engine, not the database, not the weighting" -- and the part the first pass left out.
#
# The measured justification for building it exactly this way: over 43 generations the assumed forward model
# (land at pos + direction*quantum -- the same model the pathfinder plans with) scored a 0.000 hit-rate. A carving
# that ASSUMES its model cannot discover that it is wrong; it can only be refuted forever. So Q1 induces the model
# from observation and competes against the assumed one, and the frame decides which is right. That is the entire
# argument for a marketplace: the incumbent model has never had a rival.
# ===============================================================================================================


class Q1Salience(Chain):
    """Q1: WHAT IS CHANGING VS WHAT IS FIXED?

        Salience(x_t) = ||dx_t|| * I[novelty(x_t) > theta]

    Assumes nothing about the avatar. Watches (action -> observed displacement) and INDUCES the map. Abstains from
    predicting until it has actually seen the action do something -- an induced model that guesses before it has
    evidence is just an assumed model with extra steps.
    """

    role, stage, carving = "pioneer", 1, "observed change"

    def __init__(self, action):
        self.action = action
        self.id = "q1_%s" % action
        self.disp = None            # induced displacement for THIS action
        self.n_obs = 0
        self.agree = 0

    def observe(self, ctx, action, before, after):
        if action != self.action:
            return
        try:
            b = ctx.avatar_pos(before)
            a = ctx.avatar_pos(after)
        except Exception:
            return
        if b is None or a is None:
            return
        d = (round(a[0] - b[0], 2), round(a[1] - b[1], 2))
        self.n_obs += 1
        if abs(d[0]) + abs(d[1]) < 0.5:
            return                  # a blocked move teaches nothing about what the action MEANS
        if self.disp is None:
            self.disp = d
        elif abs(self.disp[0] - d[0]) + abs(self.disp[1] - d[1]) < 1.0:
            self.agree += 1         # the induced model reproduced itself -> evidence it is real
        else:
            self.disp = d           # the world changed its mind; follow the world, not the prior

    def advocate(self, ctx):
        if self.disp is None:
            # Q1 with no evidence has exactly one thing worth doing: generate some. This is the entropy the paper
            # says must be accumulated before anything can be abstracted ("the reasoning engine doesn't skip it --
            # it explains when to exit it").
            return (self.action, 0.6, "I have never seen what %s does; the cheapest way to find out is to do it "
                                      "once and watch" % self.action)
        ap = ctx.avatar_pos(ctx.frame)
        if ap is None:
            return None
        cell = (int(round((ap[0] + self.disp[0]) / max(1, ctx.quantum))),
                int(round((ap[1] + self.disp[1]) / max(1, ctx.quantum))))
        novel = ctx.is_novel(cell)
        return (self.action, 1.0 if novel else 0.3,
                "%s has been OBSERVED to displace by %s (%d/%d times consistent); that lands somewhere %s"
                % (self.action, self.disp, self.agree, max(1, self.n_obs), "new" if novel else "already seen"))

    def predict(self, ctx, action):
        if action != self.action or self.disp is None:
            return None             # never stake on a model I have not yet earned
        ap = ctx.avatar_pos(ctx.frame)
        if ap is None:
            return None
        want = (ap[0] + self.disp[0], ap[1] + self.disp[1])
        return Prediction("avatar_at", want, 2.0, "observed model says %s" % (want,))


class CommitmentChain(Chain):
    """The macro shell's voice inside the micro market.

    Without this, "go get the booster over there" is a sentence the agent says and never acts on. This chain
    advocates the step that closes distance to whatever the macro market committed this life to -- and it competes
    for that right like everything else, so a commitment that keeps paying nothing loses standing and stops winning
    bids. A plan that cannot be outvoted is an order, and orders are what the composer already had.
    """

    role, stage, carving = "optimizer", 4, "standing commitment"
    id = "commitment"

    def __init__(self, steer_map, target_fn):
        self.steer = dict(steer_map)
        self.target_fn = target_fn

    def advocate(self, ctx):
        tgt = None
        try:
            tgt = self.target_fn()
        except Exception:
            pass
        if tgt is None:
            return None
        ap = ctx.avatar_pos(ctx.frame)
        if ap is None:
            return None
        here = (ap[0] / max(1, ctx.quantum), ap[1] / max(1, ctx.quantum))
        d0 = abs(here[0] - tgt[0]) + abs(here[1] - tgt[1])
        if d0 < 1.0:
            return None                                # arrived; nothing left to advocate
        best, bestd = None, d0
        for a, disp in self.steer.items():
            dy = ((disp[0] > 0) - (disp[0] < 0))
            dx = ((disp[1] > 0) - (disp[1] < 0))
            nd = abs(here[0] + dy - tgt[0]) + abs(here[1] + dx - tgt[1])
            if nd < bestd:
                best, bestd = a, nd
        if best is None:
            return None
        return (best, 1.5, "this life is COMMITTED to %s; %s closes the distance %.1f -> %.1f"
                % (tgt, best, d0, bestd))

    def predict(self, ctx, action):
        return None


class Q2Valence(Chain):
    """Q2: WHAT PUNISHES ME AND WHAT REWARDS ME?

        V(s) = E[reward | s]

    Direct sensation-outcome association, no causal model. Grounds value so that later abstraction has something to
    be ABOUT: the paper's point is that structure without valence transfers nothing, because two boards can be
    structurally identical and mean opposite things.
    """

    role, stage, carving = "pioneer", 2, "affective valence"
    id = "q2_valence"

    def __init__(self):
        self.v = {}                 # action -> running signed value
        self.n = {}

    def observe(self, ctx, action, before, after):
        try:
            r = ctx.reward_signal(before, after)     # +1 level taken, -1 death, small negative for pure cost
        except Exception:
            r = 0.0
        if r == 0.0:
            return
        self.n[action] = self.n.get(action, 0) + 1
        prior = self.v.get(action, 0.0)
        self.v[action] = prior + (r - prior) / float(self.n[action])

    def advocate(self, ctx):
        if not self.v:
            return None
        best = max(self.v.items(), key=lambda kv: kv[1])
        if best[1] <= 0:
            return None             # nothing has rewarded me yet; I have no business steering
        return (best[0], 1.0 + best[1],
                "%s carries the only positive valence I have measured (V=%.2f over %d encounters)"
                % (best[0], best[1], self.n.get(best[0], 0)))

    def predict(self, ctx, action):
        return None                 # valence grounds value; it does not model the board


class Q3Intervention(Chain):
    """Q3: WHAT HAPPENS IF I INTERACT WITH THE MOST SALIENT VARIABLE?

        Effect(do(a), s) = p(s' | do(a), s) - p(s' | s)

    Salience is RARITY, exactly as the published trace scores it ("rare_color_10 ... Rare color (only 0.2% of
    frame)", salience 0.96). This is the only chain that deliberately spends an action to create evidence rather
    than to make progress -- which is why the Exploiter role, not the Generalist, is the one that carries it.
    """

    role, stage, carving = "exploiter", 3, "salient rarity"
    id = "q3_intervene"

    def __init__(self, actions):
        self.actions = list(actions)
        self.tested = {}
        self.target = None

    def _salient(self, ctx):
        try:
            return ctx.rarest_colour()
        except Exception:
            return None

    def advocate(self, ctx):
        tgt = self._salient(ctx)
        if tgt is None:
            return None
        self.target = tgt
        untested = [a for a in self.actions if (a, tgt[0]) not in self.tested]
        if not untested:
            return None
        a = untested[0]
        return (a, 0.9, "colour %d covers only %.2f%% of the board -- the rarest thing here and so the most salient. "
                        "Nothing has tested %s against it; an untested intervention on the most salient variable is "
                        "the highest-information action available" % (tgt[0], tgt[1] * 100.0, a))

    def observe(self, ctx, action, before, after):
        if self.target is not None:
            self.tested[(action, self.target[0])] = True

    def predict(self, ctx, action):
        return None                 # an experiment with a confident prediction is not an experiment


class Q4Rule(Chain):
    """Q4: WHAT RULE EXPLAINS THIS ACROSS CONTEXTS?

    Abstraction by compression over confirmed evidence, in the published trace's own shape:
        {"working_hypothesis": "ACTION6 tends to help on this level", "evidence_for": 8, "evidence_against": 0}

    Holds the network honest: full pariah sensitivity (tolerance 0.0), and it will not advocate a rule that its own
    evidence does not carry.
    """

    role, stage, carving = "generalist", 5, "cross-context rule"
    id = "q4_rule"
    MIN_EVIDENCE = 3

    def __init__(self):
        self.fore = {}
        self.against = {}

    def observe(self, ctx, action, before, after):
        try:
            r = ctx.reward_signal(before, after)
        except Exception:
            r = 0.0
        if r > 0:
            self.fore[action] = self.fore.get(action, 0) + 1
        elif r < 0:
            self.against[action] = self.against.get(action, 0) + 1

    def rule(self):
        best, score = None, 0.0
        for a in set(list(self.fore) + list(self.against)):
            f, g = self.fore.get(a, 0), self.against.get(a, 0)
            if f + g < self.MIN_EVIDENCE:
                continue
            c = f / float(f + g)
            if c > score:
                best, score = a, c
        return (best, score, self.fore.get(best, 0), self.against.get(best, 0)) if best else None

    def advocate(self, ctx):
        r = self.rule()
        if not r or r[1] < 0.6:
            return None
        a, conf, f, g = r
        return (a, 1.0 + conf, "rule: %s tends to help here (%d for, %d against, confidence %.2f) -- abstracted from "
                               "what actually paid, and transferable as a claim about the world rather than about "
                               "this board" % (a, f, g, conf))

    def predict(self, ctx, action):
        return None


class Q1Hud(Chain):
    """Q1 applied to the agent's OWN RESOURCES: what is changing vs what is fixed, in the status area?

    The composer read its budget as "count one colour in the HUD rows". That colour turns out to be the CURRENT
    LIFE's meter, so the number it produced was actions-left-this-life while every decision it fed (can I afford the
    detour? should I give up?) needed actions-left-in-the-GAME. The agent could not reason about whether to fetch a
    resource and still finish, because it did not know it had lives at all.

    Nothing here names a colour or a game. It induces the status area's structure from what the numbers DO:
      * a METER drains on most actions and occasionally jumps back up;
      * a LIVES counter is whatever steps DOWN exactly when the meter jumps UP;
      * the RATE is the median observed drain -- measured, not the 4.0 that was assumed while the board charged 2.
    """

    role, stage, carving = "pioneer", 1, "own resources"
    id = "q1_hud"
    MIN_OBS = 8

    def __init__(self, hud_slice=(56, 63)):
        self.lo, self.hi = hud_slice
        self.hist = []              # per-action colour histogram of the status area
        self.meter = None           # colour whose count drains
        self.lives = None           # colour that steps down when the meter refills
        self.drops = []             # observed per-action drains of the meter
        self.refills = 0
        self.rises = set()          # colours ever seen to INCREASE -> disqualified from being a lives counter
        self.fell_at_refill = {}    # colour -> how many refills it fell at; the lives counter falls at ALL of them
        self.frames = []            # recent raw frames, so the bar can be MEASURED rather than inferred
        self.full_seen = 0          # the longest the bar has ever been = one life's worth of actions

    def _hist(self, frame):
        import numpy as _np
        a = _np.asarray(frame)[self.lo:self.hi]
        v, ct = _np.unique(a, return_counts=True)
        return {int(x): int(c) for x, c in zip(v, ct)}

    def observe(self, ctx, action, before, after):
        """Feeds and reads the ONE budget model (budget_model.py); keeps a market-facing hit-rate.

        This chain exists ONLY because the composer's budget model was sealed inside a 2002-line closure and could
        not be called from the market. That is the entire reason there were two models of one board -- and they
        disagreed, 4.0 against a true 2, each internally consistent, debugged separately for hours. The duplication
        was caused by the burial, not by a difference of opinion.
        """
        try:
            import budget_model as _BM
            _ad = getattr(ctx, "adapter", None)
            if _ad is not None:
                _m = _BM.get(_ad)
                _m.observe(before, after)
                self.meter = _m.meter if _m.meter is not None else self.meter
                self.lives = _m.lives if _m.lives is not None else self.lives
                self.full_seen = max(getattr(self, "full_seen", 0) or 0, _m.full_seen or 0)
        except Exception:
            pass
        return self._observe_local(ctx, action, before, after)

    def _observe_local(self, ctx, action, before, after):
        try:
            hb, ha = self._hist(before), self._hist(after)
        except Exception:
            return
        if not hb or not ha:
            return
        self.hist.append(ha)
        self.frames.append(after)
        if len(self.hist) > 400:
            self.hist.pop(0)
        if len(self.frames) > 8:
            self.frames.pop(0)

        # 1) THE METER: the colour that most often goes DOWN between consecutive frames.
        if self.meter is None and len(self.hist) >= self.MIN_OBS:
            fall = {}
            for i in range(1, len(self.hist)):
                a0, a1 = self.hist[i - 1], self.hist[i]
                for k in set(a0) | set(a1):
                    d = a1.get(k, 0) - a0.get(k, 0)
                    if d < 0:
                        fall[k] = fall.get(k, 0) + 1
            if fall:
                self.meter = max(fall.items(), key=lambda kv: kv[1])[0]

        if self.meter is None:
            return
        d = ha.get(self.meter, 0) - hb.get(self.meter, 0)
        if d < 0:
            self.drops.append(-d)
            if len(self.drops) > 60:
                self.drops.pop(0)
        # Track which colours EVER rise. This is the discriminator the first version lacked: when the meter refills,
        # BOTH the lives counter and the bar's spent-portion fall, so "whatever fell at the refill" identified the
        # spent mirror as the lives. A spent-portion climbs on every action; a LIVES counter only ever falls. One
        # cannot buy back a life.
        for k in set(hb) | set(ha):
            if ha.get(k, 0) > hb.get(k, 0):
                self.rises.add(k)

        if d > 0:
            # 2) THE METER REFILLED -> a life was spent. The LIVES counter is the colour that falls at EVERY refill
            # and has never risen. Latching onto "whatever fell at this refill" was not enough: several colours fall
            # at once and set iteration is unordered, so the last one seen won -- which picked a constant colour. Count
            # the evidence across refills and let the consistent one win, rather than the most recent one.
            self.refills += 1
            for k in set(hb) | set(ha):
                if k == self.meter or k in self.rises:
                    continue
                if ha.get(k, 0) < hb.get(k, 0):
                    self.fell_at_refill[k] = self.fell_at_refill.get(k, 0) + 1
            if self.fell_at_refill:
                self.lives = max(self.fell_at_refill.items(), key=lambda kv: kv[1])[0]

    def rate(self):
        if len(self.drops) < 3:
            return None
        import statistics as _s
        return _s.median(self.drops)

    def lives_left(self):
        if self.lives is None or not self.hist:
            return None
        cur = self.hist[-1].get(self.lives, 0)
        step = self._life_step()
        return int(round(cur / step)) if step else None

    def _life_step(self):
        """How much of the lives colour ONE life costs -- induced, not assumed."""
        best = None
        for i in range(1, len(self.hist)):
            a0, a1 = self.hist[i - 1], self.hist[i]
            d = a0.get(self.lives, 0) - a1.get(self.lives, 0)
            if d > 0:
                best = d if best is None else min(best, d)
        return best

    def bar_actions(self, frame):
        """Read the meter EXACTLY, by measuring the bar instead of estimating a rate.

        A meter is a BAR: its length IS the quantity. This one is 42 columns wide and 2 rows tall, and one column is
        one action -- so the answer was sitting in the frame the whole time as a number you can count. The composer
        instead counted the bar's AREA (84 = 42 x 2) and divided by a guessed rate of 4, getting 21: half the truth,
        for the whole life of the project. The rate was never a fact to discover; it is an artefact of the bar being
        two pixels tall. Measure the length; the constant disappears.
        """
        try:
            import numpy as _np
            band = _np.asarray(frame)[self.lo:self.hi]
            ys, xs = _np.where(band == self.meter)
            if not len(xs):
                return 0
            return int(len(_np.unique(xs)))          # columns remaining == actions remaining
        except Exception:
            return None

    def actions_left(self):
        """Actions until GAME OVER, not until the next respawn."""
        if not self.frames or self.meter is None:
            return None
        this_life = self.bar_actions(self.frames[-1])
        if this_life is None:
            return None
        lv = self.lives_left()
        if lv is None:
            return float(this_life)
        # A full meter is the LARGEST bar ever seen, not the largest in the handful of frames still in the buffer --
        # which are all mid-life and therefore all partly spent. Reading "full" off a drained bar made a spare life
        # look worth 20 actions instead of 42.
        self.full_seen = max(getattr(self, "full_seen", 0), this_life)
        return float(this_life) + lv * float(self.full_seen)

    def report(self):
        return {"meter": self.meter, "lives_colour": self.lives, "lives_evidence": dict(self.fell_at_refill),
                "bar_actions_now": (self.bar_actions(self.frames[-1]) if self.frames else None),
                "one_life_is": getattr(self, "full_seen", 0),
                "rate": self.rate(),
                "lives_left": self.lives_left(), "actions_left": self.actions_left(),
                "refills_seen": self.refills, "obs": len(self.hist)}

    def advocate(self, ctx):
        return None                 # a meter-reader does not choose the route

    def predict(self, ctx, action):
        r = self.rate()
        if r is None:
            return None
        return Prediction("hud_delta", -abs(r), 1.0, "meter falls by %.0f (measured)" % r)


# ===============================================================================================================
# THE MACRO SHELL -- where previous attempts inform the next one.
#
# The micro market decides ACTIONS against FRAMES. That is one shell. It cannot answer "last life I found a booster
# over there; go get it", because a plan of that shape is not an action -- it is a commitment that spans a whole life
# and can only be priced by what the life achieved. Without this shell the agent re-derives the board every epoch:
# 43 generations of experience and not one of them told the 44th where anything was.
#
# So: the SAME marketplace protocol, one shell up.
#     micro:  actor = a perceptual carving,  arena = a frame,  currency = prediction confirmed
#     macro:  actor = a PLAN,                arena = an EPOCH,  currency = progress the life measurably made
# The macro currency is EpisodeScoreCurrency -- v4's own, already checked against its arithmetic in the fidelity
# tests. That is the point of having extracted the invariant: the upper shell is not new code, it is the same
# mechanism bound to different actors.
# ===============================================================================================================


class Discovery:
    """What earlier lives FOUND. The macro market's substrate.

    Accumulates across every death and reset of one gameplay and dies with it. Keyed by nothing but position and what
    was observed to happen there -- no game identity, no lookup. This is the difference between an agent that has
    lived 43 lives and one that has lived the same life 43 times.
    """

    def __init__(self):
        self.sites = {}             # cell -> {"kind","colour","visits","paid","last_epoch","outcome"}

    def note(self, cell, kind, colour=None, epoch=0):
        c = tuple(cell)
        s = self.sites.setdefault(c, {"kind": kind, "colour": colour, "visits": 0, "paid": 0.0,
                                      "last_epoch": epoch, "outcome": None})
        s["kind"] = kind or s["kind"]
        if colour is not None:
            s["colour"] = colour
        return s

    def touched(self, cell, payoff, epoch=0, outcome=""):
        """We went there and this is what it gave us. Payoff is MEASURED, never assumed."""
        s = self.sites.get(tuple(cell))
        if s is None:
            s = self.note(cell, "unknown", epoch=epoch)
        s["visits"] += 1
        s["paid"] += float(payoff)
        s["last_epoch"] = epoch
        s["outcome"] = outcome or s["outcome"]

    def unexplored(self):
        return [c for c, s in self.sites.items() if s["visits"] == 0]

    def by_value(self):
        """Sites ranked by what they have actually paid, per visit. A site that has never been tried ranks as
        UNKNOWN rather than worthless -- the distinction the whole session turned on."""
        out = []
        for c, s in self.sites.items():
            v = (s["paid"] / s["visits"]) if s["visits"] else None
            out.append((c, s, v))
        return sorted(out, key=lambda t: (-1e9 if t[2] is None else -t[2]))

    def summary(self):
        return {"sites": len(self.sites), "untried": len(self.unexplored()),
                "paid": sum(1 for _, s in self.sites.items() if s["paid"] > 0)}


class Plan:
    """A macro actor: one commitment for one life. Cheap to hold, expensive to be wrong about -- which is exactly
    what a marketplace is for."""

    __slots__ = ("kind", "target", "why")

    def __init__(self, kind, target, why=""):
        self.kind = kind            # 'collect' | 'trip' | 'probe' | 'explore'
        self.target = target
        self.why = why

    @property
    def id(self):
        return "%s@%s" % (self.kind, self.target if self.target is not None else "-")


class MacroMarket:
    """Plans bid for the next EPOCH, priced by what they measurably achieved in the epochs they have already had.

    This is v4's loop, unchanged in shape: propose a commitment, weight it by the record it has actually earned,
    resolve, and let the result be judged by the world rather than by the proposer's confidence in itself.
    """

    def __init__(self, emit=None):
        self.discovery = Discovery()
        self.ledger = Ledger()
        self.currency = EpisodeScoreCurrency()
        self.emit = emit or (lambda s: None)
        self.market = Marketplace(self.currency, self.ledger, emit=self.emit)
        self.current = None
        self.epoch = 0
        self.history = []
        # Negative knowledge at the macro shell. Without it the market re-commits to the same failed plan every life:
        # once every plan has paid 0 they all tie, and a tie resolves to whichever came first, forever. That is the
        # wall-hammering pathology one shell up. Toxicity DECAYS (0.05/gen), so a plan that failed steps aside without
        # being condemned -- "without decay, agents become paralyzed by ancient failures".
        self.pariahs = PariahStore(emit=self.emit)
        self.role = "pioneer"
        self._tox = {}

    def _paralysis(self):
        """v4's condition, at this shell: many plans attempted, none succeeding -> our own accumulated 'that failed'
        may be what is holding us here, so let the bolder roles through."""
        tried = [a for a in self.ledger.actors()]
        wins = sum(1 for a in tried if self.ledger.get(a).get("score_change", 0.0) > 0)
        return detect_paralysis(attempts=len(self.history), successes=wins, unique_carvings=len(tried))

    def _candidates(self):
        boost = self._paralysis()
        ps = []
        for cell, s, v in self.discovery.by_value():
            kind = {"booster": "collect", "trigger": "trip"}.get(s["kind"], "probe")
            pid = "%s@%s" % (kind, cell)
            tox = self.pariahs.penalty(pid, self.role, paralysis_boost=boost)
            if tox >= 0.9:
                continue            # still strongly toxic -> not a candidate this life. It will decay back in.
            self._tox[pid] = tox
            if v is None:
                why = "found at %s and NEVER TRIED -- an untried find is the cheapest information on the board, and " \
                      "it has been sitting there %d epochs" % (cell, max(0, self.epoch - s["last_epoch"]))
            else:
                why = "%s at %s has paid %.2f per visit over %d visits (toxicity %.2f)" % (
                    s["kind"], cell, v, s["visits"], tox)
            ps.append(Plan(kind, cell, why))
        _ex = Plan("explore", None, "nothing found is worth committing a life to; go find something")
        # Explore is a PLAN and is priced like one. Leaving it out of the toxicity table gave it a permanent 0.0 and
        # therefore permanent first place -- the agent explored forever because exploring could never be refuted.
        self._tox[_ex.id] = self.pariahs.penalty(_ex.id, self.role, paralysis_boost=boost)
        ps.append(_ex)
        # RANK by toxicity, not merely filter on it. Once every plan has paid 0 they tie on value, and a tie has to
        # break on SOMETHING -- left alone it breaks on list order, which is why one failed plan was re-committed ten
        # lives running. Freshest failure last, so the agent works THROUGH the board instead of at one point of it.
        ps.sort(key=lambda p: self._tox.get(p.id, 0.0))
        if boost > 0:
            self.emit("MACRO  PARALYSIS: %d plans attempted, none has paid. v4's reading of this is that the "
                      "accumulated 'that failed' may itself be the wall -> tolerance +%.2f, so plans this agent had "
                      "written off come back onto the table rather than being obeyed forever" % (len(self.history), boost))
        return ps

    def choose(self, epoch):
        """Pick the commitment for this life. Called at an epoch boundary -- i.e. after a death, which is the only
        moment the previous attempt is actually finished and can be priced."""
        self.epoch = epoch
        cands = self._candidates()
        props = []
        for p in cands:
            rec = self.ledger.get(p.id)
            props.append(Proposal(actor_id=p.id, action=p, confidence=0.0, rationale=p.why,
                                  payload={"score_change": rec.get("score_change", 0.0), "plan": p}))
        if len(props) < 2:
            self.current = cands[0]
            return self.current
        res = self.market.run(props)
        if res and self._tox.get(res["proposal"].payload["plan"].id, 0.0) < 0.5:
            self.current = res["proposal"].payload["plan"]
        elif res:
            # The market's winner is a plan we have just watched fail. A consensus reached by everyone having nothing
            # to say is not agreement, and re-committing to it is obedience to an accident of ordering.
            self.current = cands[0]
            self.emit("MACRO  the market's pick (%s) is freshly toxic -- consensus among plans that have ALL paid "
                      "nothing is not agreement. Taking the least-recently-refuted instead: %s"
                      % (res["proposal"].actor_id, self.current.id))
        else:
            # No consensus: back the thing nobody has tried. An untried site is not a worse bet than a tried one --
            # it is an UNKNOWN one, and unknowns are what an epoch is for.
            untried = [p for p in cands if self.ledger.get(p.id).get("n", 0) == 0]
            self.current = untried[0] if untried else cands[0]
            self.emit("MACRO  no consensus on what to do with this life -> committing to the untried: %s"
                      % self.current.why)
        self.emit("MACRO  epoch %d commits to %s -- %s" % (epoch, self.current.id, self.current.why))
        return self.current

    def settle_epoch(self, progress, epoch):
        """Price the life that just ended by what it actually achieved. This is the line that makes the next attempt
        inherit the last one."""
        if self.current is None:
            return
        self.ledger.record(self.current.id, score_change=float(progress), score=float(progress),
                           wins=1.0 if progress > 0 else 0.0, efficiency=float(progress))
        if progress <= 0:
            self.pariahs.record(self.current.id, final_score=0.0, failure_mode="committed a life, gained nothing")
        self.pariahs.tick()
        if self.current.target is not None:
            self.discovery.touched(self.current.target, progress, epoch=epoch,
                                   outcome="paid" if progress > 0 else "nothing")
        self.history.append((epoch, self.current.id, progress))
        self.emit("MACRO  epoch %d ends: %s %s (progress %.2f). That verdict is now on the record and prices this "
                  "plan against every rival next life -- the attempt is not thrown away with the life."
                  % (epoch, self.current.id, "PAID" if progress > 0 else "paid nothing", progress))

    def report(self):
        return {"discovery": self.discovery.summary(), "epoch": self.epoch,
                "current": (self.current.id if self.current else None),
                "plans_tried": len(self.ledger.actors()),
                "toxic_now": sum(1 for k in self.pariahs.items),
                "paralysis": self._paralysis(),
                "history": self.history[-10:]}


# ===============================================================================================================
# PLURAL PERCEPTS -- the fix for the market's structural defect.
#
# The arena held ten chains and ONE ctx. Every chain called the same ctx.avatar_pos(), so they disagreed about what
# to DO and agreed completely about what they SAW. Ten opinions over one percept is ONE SHELL, and one shell plus
# selection is the definition of gradient descent -- which is exactly the complaint.
#
# §I6: the invariant is never observed directly; it is only ever INTEGRATED FROM SHELLS, plural. So the shells have
# to exist. A Percept is a shell: one way of carving "where is the thing that moves" out of a frame. They are allowed
# to DISAGREE, and their disagreement is not noise to be averaged away -- it is the only place non-identity can enter
# a single agent, and non-identity is what makes the loop informative rather than a copy.
# ===============================================================================================================


class Percept:
    """One carving of the board. A vantage, not an opinion."""

    id = "percept"
    carving = "unnamed"

    def avatar_pos(self, frame, prev=None):
        raise NotImplementedError

    def confidence(self):
        return 1.0


class ColourPercept(Percept):
    """The incumbent: 'the avatar is the thing of this colour.'

    Correct on this board and unopposed everywhere else, which is the problem -- an unopposed percept cannot be
    discovered to be wrong. It stays, but now it has rivals that can beat it on the record.
    """

    id, carving = "p_colour", "identity: a fixed colour IS the avatar"

    def __init__(self, colour):
        self.colour = colour

    def avatar_pos(self, frame, prev=None):
        try:
            import numpy as _np
            m = (_np.asarray(frame) == self.colour)
            if not m.sum():
                return None
            w = _np.where(m)
            return (float(w[0].mean()), float(w[1].mean()))
        except Exception:
            return None


class DeltaPercept(Percept):
    """'The avatar is whatever just changed.'

    Assumes no colour and no identity -- only that the thing under my control is the thing that moves when I act.
    On a board where the avatar recolours, or where the colour is shared with scenery, this is right where the
    colour percept is wrong. It needs two frames, so it abstains on the first.
    """

    id, carving = "p_delta", "causality: what MOVED when I acted is me"

    def __init__(self, play=(2, 56)):
        self.lo, self.hi = play

    def avatar_pos(self, frame, prev=None):
        if prev is None:
            return None
        try:
            import numpy as _np
            # PLAY AREA ONLY. The status bar changes on every single action -- the meter drains -- so a delta centroid
            # taken over the whole frame is dragged into the HUD every time and measures the budget, not the avatar.
            # A percept that includes its own resource meter in "what moved" is answering a different question.
            a = _np.asarray(prev)[self.lo:self.hi]
            b = _np.asarray(frame)[self.lo:self.hi]
            if a.shape != b.shape:
                return None
            d = (a != b)
            if not d.sum() or d.sum() > 400:          # a whole-board change is a reload, not a step
                return None
            w = _np.where(d)
            return (float(w[0].mean()) + self.lo, float(w[1].mean()))
        except Exception:
            return None


class RarityPercept(Percept):
    """'The avatar is the rarest small thing in the play area.'

    The published trace's own salience heuristic (rare colour -> salience 0.96), turned into a vantage instead of a
    target. Wrong whenever the avatar is common; right on boards where the mover is the unusual object and its colour
    is not known in advance.
    """

    id, carving = "p_rarity", "salience: the rarest small object is me"

    def __init__(self, play=(2, 56)):
        self.lo, self.hi = play

    def avatar_pos(self, frame, prev=None):
        try:
            import numpy as _np
            g = _np.asarray(frame)[self.lo:self.hi]
            vals, cnts = _np.unique(g, return_counts=True)
            tot = float(g.size)
            best = None
            for v, c in zip(vals, cnts):
                frac = c / tot
                if frac < 0.0005 or frac > 0.02:
                    continue
                if best is None or frac < best[1]:
                    best = (int(v), float(frac))
            if best is None:
                return None
            w = _np.where(g == best[0])
            return (float(w[0].mean()) + self.lo, float(w[1].mean()))
        except Exception:
            return None


class ComponentPercept(Percept):
    """'The avatar is the whole connected OBJECT, whatever colours it is made of.'

    The rival the colour percept has never had. The board's avatar is a 5x5 composite -- two rows of one colour over
    three rows of another -- and a carve-by-colour ontology sees half of it and calls that the agent. The half moves
    when the whole moves, so tracking it looks like it works; what breaks is everything computed FROM its position,
    because the centroid of the top half is not where the object is.

    This is the type-assignment problem in one object: you cannot write one rule per type when the type boundary runs
    through the middle of the thing the rule is about.
    """

    id, carving = "p_component", "objecthood: the whole connected thing is me, whatever colours it wears"

    def __init__(self, seed_colour, play=(2, 56)):
        self.seed = seed_colour
        self.lo, self.hi = play

    def avatar_pos(self, frame, prev=None):
        try:
            import numpy as _np
            g = _np.asarray(frame)[self.lo:self.hi]
            seed = _np.where(g == self.seed)
            if not len(seed[0]):
                return None
            # grow from the seed through anything that is not floor/wall background, 4-connected
            bg = _np.bincount(g.ravel()).argmax()
            wall = None
            counts = _np.bincount(g.ravel())
            order = _np.argsort(-counts)
            bgs = {int(order[0]), int(order[1])} if len(order) > 1 else {int(order[0])}
            H, W = g.shape
            stack = [(int(seed[0][0]), int(seed[1][0]))]
            seen = set(stack)
            while stack:
                r, c = stack.pop()
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < H and 0 <= nc < W and (nr, nc) not in seen and int(g[nr, nc]) not in bgs:
                        seen.add((nr, nc))
                        stack.append((nr, nc))
                if len(seen) > 200:
                    return None
            if not seen:
                return None
            ys = [r for r, _ in seen]
            xs = [c for _, c in seen]
            return (float(sum(ys)) / len(ys) + self.lo, float(sum(xs)) / len(xs))
        except Exception:
            return None


class PerceptArena:
    """Prices the PERCEPTS themselves, on the same currency as everything else.

    This is the piece that makes plural vantages more than decoration: a percept stakes a claim about where the
    avatar will be, the frame settles it, and a percept that keeps being refuted loses standing. The agent can now
    discover that its own way of seeing is wrong -- which, with one shared ctx, was structurally impossible.

    Disagreement is recorded rather than resolved. Two percepts that disagree are the non-identity §I2a needs; the
    board decides which one was right, and neither Claude nor the composer gets a vote.
    """

    def __init__(self, percepts, emit=None):
        self.percepts = list(percepts)
        self.ledger = Ledger()
        self.emit = emit or (lambda s: None)
        self.open = []
        self.disagreements = 0
        self.checks = 0

    def positions(self, frame, prev=None):
        out = {}
        for p in self.percepts:
            try:
                pos = p.avatar_pos(frame, prev)
            except Exception:
                pos = None
            if pos is not None:
                out[p.id] = pos
        return out

    def stake(self, frame, prev, disp):
        """Each percept predicts where IT thinks the avatar will land, from ITS OWN reading of where it is now."""
        self.open = []
        for p in self.percepts:
            here = p.avatar_pos(frame, prev)
            if here is None or disp is None:
                continue
            self.open.append((p.id, (here[0] + disp[0], here[1] + disp[1])))

    def settle(self, frame, prev):
        if not self.open:
            return
        seen = {}
        for pid, want in self.open:
            p = next((x for x in self.percepts if x.id == pid), None)
            if p is None:
                continue
            got = p.avatar_pos(frame, prev)
            if got is None:
                continue
            err = abs(got[0] - want[0]) + abs(got[1] - want[1])
            hit = 1.0 if err <= 2.0 else 0.0
            seen[pid] = got
            self.ledger.record(pid, n=1.0, hits=hit, score_change=hit)
        if len(seen) >= 2:
            self.checks += 1
            vals = list(seen.values())
            spread = max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a in vals for b in vals)
            if spread > 2.0:
                self.disagreements += 1
        self.open = []

    def update_poses(self, chains):
        """Move each chain's alpha toward whichever stream is calibrated better for IT.

        Without this call alpha is a constant, every chain integrates identically, and I2a is unfalsifiable by
        construction rather than true. The comparison is honest: my own recent history vs the market's consensus,
        judged against what actually happened to me.
        """
        if not chains:
            return
        vals = [c.private_view() for c in chains if c.private_view() is not None]
        if not vals:
            return
        network = sum(vals) / len(vals)                 # the consensus: what the market as a whole is running at
        for c in chains:
            priv = c.private_view()
            if priv is None:
                continue
            actual = c.encounters[-1] if getattr(c, "encounters", None) else None
            if actual is None:
                continue
            c.update_alpha(abs(priv - actual) < abs(network - actual), abs(network - actual) <= abs(priv - actual))

    def standings(self):
        out = {}
        for p in self.percepts:
            r = self.ledger.get(p.id)
            n = r.get("n", 0.0)
            out[p.id] = {"n": int(n), "hit_rate": round(r.get("hits", 0.0) / n, 3) if n else None,
                         "carving": p.carving}
        return out

    def report(self):
        return {"standings": self.standings(), "checks": self.checks,
                "disagreements": self.disagreements,
                "disagree_rate": round(self.disagreements / max(1, self.checks), 3)}

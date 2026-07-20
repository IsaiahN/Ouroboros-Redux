"""
hypothesis_market.py  --  the micro-level HGT idea-economy for OBJECTIVE-HYPOTHESES.

Fixes Gap 1 (the composer holds ONE hypothesis where a market needs MANY). Instead of collapsing to a single
win-condition formula, the composer holds a POOL of competing objective-hypotheses and lets prediction-error arbitrate.

THE ACCOUNTING IS FRISTON, NOT A NEW ENGINE. Every "fitness" number here is a free-energy / surprise quantity taken from
the existing `prediction_error_bus` -- the Friston/Rescorla-Wagner organ this project already runs:
  * A hypothesis's FITNESS = -(precision-weighted prediction error) it accrues against real frames. In Free-Energy-
    Principle terms, a hypothesis that lowers variational free energy (surprise) is fit; one that raises it is a burden.
    (Friston, "The free-energy principle: a rough guide to the brain", 2009; "Life as we know it", 2013 -- cells/agents
    minimise the long-run average of surprise, i.e. maximise the evidence for their own generative model.)
  * PRECISION-WEIGHTING (inverse variance / confidence) is read straight from the bus's per-layer hits/misses, so a
    low-reliability hypothesis cannot masquerade as sharp. Precision is the brake, exactly as in FEP.

THE RULES OF THE ECONOMY ARE MICRO-LEVEL HGT (how a SINGLE cell handles foreign genetic material), not the v1-v4 macro
population economy:
  1. EXPRESS-BEFORE-JUDGE  -- (transcription-dependent CRISPR interference; Goldberg et al. 2014) a candidate is tried in
     the loop and judged by outcome, never accepted/rejected a priori.
  2. FITNESS = -SURPRISE    -- (Friston FEP; "a foreign gene is retained if it does not impair fitness") the bus residual
     is the fitness function; unfit hypotheses die.
  3. COHERENCE GATE         -- (restriction-modification: foreign DNA cut unless it matches host methylation; similar-self
     integrates) a candidate incoherent with won-confirmed priors is resisted. (This project already has the COHERENCE
     check; the market defers to it.)
  4. FALSIFIED MEMORY       -- (CRISPR-Cas adaptive immunity: a weighted record of past invaders, auto-degraded on
     re-encounter) falsified hypotheses are remembered and not re-tried, so trials aren't wasted on known-dead ideas.
  5. FITNESS-CONDITIONAL GATE-DROP -- (CRISPR loss under antibiotic selection: the rejection gate is relaxed when the
     acquired element is decisive) a candidate that sharply reduces surprise may integrate even against a low-confidence
     coherence objection -- high fitness overrides the gate.

Thread-local (the framework runs games in threads). Observe-capable: env OURO_HYP_MARKET selects behaviour so the market
can be A/B'd against the single-formula baseline on held-out levels_completed -- the only judge.
"""
from __future__ import annotations
import os, math, threading

MODE = os.environ.get("OURO_HYP_MARKET", "active").strip().lower()   # off | observe | active
POOL_CAP = int(os.environ.get("OURO_HYP_POOL", "6"))                   # max competing hypotheses held at once
GATE_DROP_FITNESS = float(os.environ.get("OURO_HYP_GATEDROP", "0.8"))  # fitness above which the coherence gate is relaxed


class _Hyp:
    __slots__ = ("name", "fitness", "trials", "confirms", "falsified", "coherent")
    def __init__(self, name):
        self.name = name
        self.fitness = 0.0      # running -surprise (free-energy) score; higher = fitter
        self.trials = 0         # times EXPRESSED (rule 1)
        self.confirms = 0       # times it re-confirmed on a real win
        self.falsified = False  # CRISPR memory (rule 4)
        self.coherent = True    # restriction-modification verdict (rule 3)


class HypothesisMarket:
    """A per-game pool of competing objective-hypotheses, arbitrated by Friston free-energy from the bus."""
    def __init__(self):
        self._local = threading.local()

    def _pool(self):
        p = getattr(self._local, "pool", None)
        if p is None:
            p = self._local.pool = {}      # name -> _Hyp
        return p

    # -- rule 1: EXPRESS a candidate (register it as tried); never judged a priori ------------------------------
    def express(self, name):
        if MODE == "off":
            return
        p = self._pool()
        h = p.get(name)
        if h is None:
            if len(p) >= POOL_CAP:
                # evict the least-fit non-verified hypothesis to bound the pool (natural death of the weakest idea)
                worst = min(p.values(), key=lambda x: (x.confirms, x.fitness))
                if worst.confirms == 0:
                    p.pop(worst.name, None)
            h = p[name] = _Hyp(name)
        if h.falsified:            # rule 4: CRISPR memory -- do not resurrect a known-dead idea
            return
        h.trials += 1

    # -- rule 2: FITNESS = -surprise. Feed the bus residual in as free-energy; higher fitness = lower surprise --
    def score(self, name, residual, precision=1.0, confirmed=False):
        """residual: prediction error against a REAL frame (0 = perfect). precision: bus confidence (inverse variance).
        Fitness accrues -(precision * residual): a hypothesis that keeps predicting real frames well gets fit."""
        if MODE == "off":
            return
        h = self._pool().get(name)
        if h is None or h.falsified:
            return
        h.fitness += -(float(precision) * float(residual))
        if confirmed:
            h.confirms += 1
            h.fitness += float(precision)          # a real win is strong evidence (self-evidencing, FEP)

    # -- rule 3: COHERENCE GATE (restriction-modification). Defer to the existing coherence verdict. -------------
    def set_coherence(self, name, coherent):
        h = self._pool().get(name)
        if h is not None:
            h.coherent = bool(coherent)

    # -- rule 4: FALSIFIED MEMORY (CRISPR). Record a dead idea so it is auto-rejected on re-encounter. -----------
    def falsify(self, name):
        if MODE == "off":
            return
        h = self._pool().get(name)
        if h is None:
            h = self._pool()[name] = _Hyp(name)
        h.falsified = True

    # -- arbitration: the winner is the fittest hypothesis that passes the gate (rule 5 relaxes the gate) --------
    def winner(self):
        """Return the name of the current best objective-hypothesis, or None. In OBSERVE mode this is advisory only."""
        live = [h for h in self._pool().values() if not h.falsified and h.trials > 0]
        if not live:
            return None
        # rule 5: a hypothesis whose fitness is decisive may pass even if the coherence gate objected
        eligible = [h for h in live if h.coherent or h.fitness >= GATE_DROP_FITNESS]
        if not eligible:
            eligible = live
        best = max(eligible, key=lambda h: (h.confirms, h.fitness))
        return best.name

    def ranked(self):
        return sorted([(h.name, round(h.fitness, 3), h.confirms, h.falsified)
                       for h in self._pool().values() if h.trials > 0],
                      key=lambda t: (-t[2], -t[1]))

    def narrate(self):
        r = self.ranked()
        if not r:
            return "hyp-market[%s]: empty" % MODE
        return "hyp-market[%s]: %d live | winner=%s | %s" % (MODE, len(r), self.winner(), r[:4])

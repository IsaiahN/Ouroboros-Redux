"""
resonance_market.py  --  the four Ouroboros v1-v4 evolutionary ACCELERANTS, transformed from the macro (population)
shell to the micro (single-agent) shell per FMap. NOT a shrink of the macro loop: each mechanism is the same INVARIANT
expressed in the transformed environment (population -> one mind; agents -> reasoning-fragments). This is the inner
Matryoshka shell, built to MEET the macro form in the middle -- each accelerant carries its macro<->micro bracket so the
meeting point is auditable, not asserted.

The marketplace of the NETWOK (agents swap ideas) transformed into the marketplace of the AGENT (analogies / CoT swap).

Wraps HypothesisMarket (the micro-HGT economy: express-before-judge, fitness=-surprise/Friston, R-M coherence gate,
CRISPR falsified memory, fitness-conditional gate-drop). Adds the four accelerants that compressed evolutionary time.

All observe-capable (env OURO_RESONANCE = off|observe|active), thread-local, judged on levels_completed vs baseline.
"""
from __future__ import annotations
import os, threading, hashlib

MODE = os.environ.get("OURO_RESONANCE", "active").strip().lower()
RES_BONUS = float(os.environ.get("OURO_RES_BONUS", "0.5"))    # fitness multiplier per extra independent source
WARM_BIAS = float(os.environ.get("OURO_WARM_BIAS", "0.5"))    # epigenetic warm-start strength (bias, never foreclose)


def _hash(x):
    return hashlib.sha1(str(x).encode()).hexdigest()[:10]


class ResonanceMarket:
    def __init__(self, base_market):
        self.m = base_market          # the underlying HypothesisMarket (5 micro-HGT rules)
        self._local = threading.local()

    def _st(self):
        s = getattr(self._local, "st", None)
        if s is None:
            s = self._local.st = {
                "sources": {},     # name -> set(source_id)      : resonance (who independently implicated it)
                "bias": {},        # source_id -> bias_tag        : independence guard (opposed biases only)
                "contexts": {},    # name -> set(context_sig)     : context-tagging (where it held)
                "inherited": set() # names carried in from a prior shell (epigenetic warm-start)
            }
        return s

    # ============================================================ ACCELERANT 1: RESONANCE (cross-source convergence)
    # MACRO (v4 resonance_detector): Pioneers/Generalists/Exploiters -- roles with RADICALLY DIFFERENT biases -- hash
    #   their inferred beliefs; when >=2 roles independently converge on the same pattern-hash, role_diversity rises and
    #   resonance amplifies it: "truth amplifies through cross-domain resonance, not random search." Independence is
    #   ENGINEERED (opposed biases) so agreement means truth, not shared error.
    # MICRO (FMap transform: agents -> the agent's own evidence SOURCES): perception (blind/frontier ~ Pioneer),
    #   causal-map (history-consensus ~ Generalist), coherence/priors (established ~ Exploiter), induction. When these
    #   INDEPENDENT derivations converge on the same objective-hypothesis, amplify it. The invariant is identical
    #   (independent convergence = truth); only the traders changed. The independence guard transforms too: a source may
    #   only add role_diversity if its bias_tag differs from sources already counted -- else it's the same error echoing.
    def declare_source(self, source_id, bias_tag):
        """Register an evidence source with its bias tag (independence bookkeeping)."""
        self._st()["bias"][source_id] = bias_tag

    def vote(self, name, source_id):
        """An independent source implicates this hypothesis (its belief-hash matches). Convergence, not fit."""
        if MODE == "off":
            return
        self._st()["sources"].setdefault(name, set()).add(source_id)

    def resonance(self, name):
        """role_diversity, counted only over DISTINCT biases (independence guard) -- echoing sources don't amplify."""
        srcs = self._st()["sources"].get(name, set())
        bias = self._st()["bias"]
        distinct_biases = {bias.get(s, s) for s in srcs}
        return len(distinct_biases)

    # ============================================================ ACCELERANT 2: EPIGENETIC WARM-START (Lamarckian)
    # MACRO (v4 HGT engine layer_2_epigenetic=0.45 "inherited"): learned adaptations (sensation mappings, learning rates)
    #   are inherited DIRECTLY, not waiting for genetic selection -- the biggest time-compressor (nature can't do this).
    # MICRO (FMap: generation-inheritance -> level/game-inheritance): confirmed hypotheses from the prior shell warm-start
    #   the new shell's induction -- they enter the pool pre-weighted (bias) but are NOT accepted as answers (never
    #   foreclose fresh synthesis; the nine-lives caution -- carry invariants, not solutions). A warm-started hypothesis
    #   still has to re-confirm on the new shell's real frames or it decays like any other.
    def inherit(self, prior_confirmed_names):
        """Warm-start the pool with prior-shell confirmed hypotheses: a fitness BIAS, not a commitment."""
        if MODE == "off":
            return
        for name in (prior_confirmed_names or []):
            self.m.express(name)
            self.m.score(name, residual=0.0, precision=WARM_BIAS)   # bias only; must still earn confirmation here
            self._st()["inherited"].add(name)

    # ============================================================ ACCELERANT 3: CONTEXT-TAGGING (transfer conditions)
    # MACRO (v4 sensation-aware transfer, >70% vs <30%): transfer WHAT worked + WHEN/HOW it felt, so the recipient knows
    #   the applicability conditions and doesn't misapply the gift. This IS FMap operationalized -- a unit carries the
    #   conditions under which its structure survives transfer to a new shell.
    # MICRO (FMap: emotional/sensation context -> perceptual context): tag each confirmed hypothesis with a signature of
    #   the perceptual context it held in; only re-apply (or warm-start) it where the context matches -- i.e. where the
    #   transformation between shells preserves its structure. A hypothesis whose context does NOT match the new shell is
    #   held but not asserted (it may not survive this particular transform).
    def tag_context(self, name, context_sig):
        if MODE == "off":
            return
        self._st()["contexts"].setdefault(name, set()).add(_hash(context_sig))

    def applicable(self, name, context_sig):
        """True if this hypothesis was confirmed in a matching context (its structure plausibly survives the transform)."""
        ctx = self._st()["contexts"].get(name)
        if not ctx:
            return True   # untagged -> no evidence against; allow (fresh synthesis)
        return _hash(context_sig) in ctx

    # ============================================================ ACCELERANT 4: DIVERSITY-PRESERVATION (prestige-analogue)
    # MACRO (v4 prestige_engine, SACRED rule): social capital (contribution/teaching) is DECOUPLED from economic capital
    #   (wins). Prestige buys survival protection + breeding priority but NEVER action budget -- so knowledge-sharers
    #   survive even if they don't personally win, preventing the population collapsing to one winning lineage (which
    #   would kill the diversity evolution feeds on).
    # MICRO (FMap: breeding-population diversity -> hypothesis-pool diversity): a hypothesis with cross-context
    #   CONTRIBUTION (it held across MANY shells) is protected from eviction even if it lost the CURRENT shell -- its
    #   contribution is decoupled from its current-level performance. This stops the agent collapsing prematurely onto a
    #   single-level winner and losing the breadth needed to crack the next shell.
    def contribution(self, name):
        """Cross-shell contribution = how many distinct contexts it held in (breadth), decoupled from current fitness."""
        return len(self._st()["contexts"].get(name, set()))

    def protected(self, name):
        """A high-contribution hypothesis is survival-protected (prestige) regardless of current-level performance."""
        return self.contribution(name) >= 2

    # ============================================================ arbitration: fit x resonance, diversity-protected
    def winner(self, context_sig=None):
        """The best hypothesis = base fitness AMPLIFIED by resonance (independent convergence), among the applicable set.
        In OBSERVE mode this is advisory; the single-formula baseline is unchanged so the market can be A/B'd."""
        pool = self.m._pool()
        live = [h for h in pool.values() if not h.falsified and h.trials > 0]
        if context_sig is not None:
            live = [h for h in live if self.applicable(h.name, context_sig)] or live
        if not live:
            return None
        def amplified(h):
            r = self.resonance(h.name)
            boost = 1.0 + RES_BONUS * max(0, r - 1)          # convergence across independent sources amplifies
            prot = 0.5 if self.protected(h.name) else 0.0    # diversity protection nudges breadth-carriers up
            return (h.confirms, h.fitness * boost + prot)
        return max(live, key=amplified).name

    def narrate(self):
        pool = self.m._pool()
        rows = []
        for h in pool.values():
            if h.trials > 0:
                rows.append((h.name, round(h.fitness, 2), self.resonance(h.name), self.contribution(h.name),
                             h.name in self._st()["inherited"]))
        rows.sort(key=lambda t: (-t[2], -t[1]))
        return "resonance-market[%s]: winner=%s | (name,fit,resonance,contrib,inherited)=%s" % (MODE, self.winner(), rows[:4])

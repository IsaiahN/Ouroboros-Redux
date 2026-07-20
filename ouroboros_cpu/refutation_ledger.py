"""refutation_ledger.py -- the detective's case file. Persists, ACROSS RESETS within a level-episode, which
molecules have been ruled out, so each reset eliminates rather than re-narrates, and the agent can EARN the
right to give up.

Why this is the build (from the §11.34x discussion, Q1+Q3+Q4):
  * Q1 (done): refutation is now CAUSAL at the molecule layer -- validation.validate(molecule, history, phase)
    returns 'falsified' when THAT molecule's prediction broke. The ledger consumes those verdicts; it never
    blames a molecule by mere co-occurrence with failure.
  * Q3: the candidate set is OBSERVATION-LICENSED -- it is exactly what the abductor proposes, which is
    already gated by observed dynamics/affordances/cues. The ledger persists and eliminates over that set;
    it never enumerates the productive composition space. "Exhausted" therefore means "exhausted the
    LICENSED vocabulary," which is small -- not "tried everything."
  * Q4 (the gap this closes): compose used to re-abduce COLD each reset; nothing carried the refuted set
    across resets. The ledger does, so the licensed space provably SHRINKS across resets.

Verdicts:
  composing            -- live candidates remain; keep testing (next_hypothesis picks what to test).
  confirmed_no_win     -- a molecule was CONFIRMED but the game is unwon: understanding without a win. This is
                          PURSUIT territory (the mechanic is right, the game isn't closed), NOT exhaustion.
  deduction_exhausted  -- every licensed candidate is REFUTED, none live, none confirmed, and re-abduction
                          adds nothing new. EARNED give-up. Scope is stated: exhausted the licensed grammar,
                          which is NOT a claim the game is unsolvable -- only unsolvable under this vocabulary.

DISCIPLINE: the ledger decides exhaustion from the SPACE being empty (composer offers nothing un-refuted),
never from "no reward lately" -- so a long flat pre-breakthrough stretch (the delayed-reward case) does not
trigger a tap-out as long as a live candidate or a fresh licensable molecule remains.
"""
import validation as _val


class RefutationLedger:
    def __init__(self):
        self.episode = 0
        self.established = {}                # molecules CONFIRMED in PRIOR episodes -- carried context (layering)
        self._new_episode_state()
        self.history_episodes = []          # archived (level, refuted, confirmed) for explain/record

    def _new_episode_state(self):
        self.candidates = {}                # identity -> molecule (live, not yet resolved)
        self.refuted = {}                   # identity -> evidence dict (closed branch)
        self.confirmed = {}                 # identity -> evidence dict (confirmed THIS episode)
        self.attempts = {}                  # identity -> int (how many resets this candidate has been tested)
        self.seen = set()                   # every identity ever licensed this episode
        self._last_added_new = 0            # how many genuinely-new candidates the last license() introduced
        self.resets = 0
        self._resets_at_last_move = 0       # self.resets when a verdict last formed (for the INERT detector)

    def new_episode(self, level=None):
        """Call on a genuine LEVEL ADVANCE: each level layers a new mechanic, so a molecule REFUTED under the
        old mechanic set may now be relevant -> live/refuted start fresh (re-testable). CONFIRMED molecules
        are established understanding and carry forward as context (persistent_model-style layering); they do
        NOT block this level's exhaustion (banking level 1 must not prevent tapping out of an unsolvable
        level 2). The old case file is archived."""
        if self.seen or self.confirmed:
            self.history_episodes.append(dict(episode=self.episode, level=level,
                                              refuted=list(self.refuted), confirmed=list(self.confirmed)))
        self.established.update(self.confirmed)     # carry confirmed forward as established context
        self.episode += 1
        self._new_episode_state()

    # ---- licensing: register the observation-licensed candidates the abductor proposed this round ----
    def license(self, molecules):
        """Add molecules (MoleculeHyp with .prediction) the environment justified. Already-resolved
        identities are NOT re-opened; that is how re-abducing the same molecule across resets does not
        re-test a closed branch. Returns the count of genuinely-new candidates."""
        added = 0
        for m in molecules:
            if getattr(m, "prediction", None) is None:
                continue                                  # uncommitted -> not a testable candidate
            ident = m.identity
            if ident in self.established:
                continue                                  # prior-level established -- not THIS episode's search
            self.seen.add(ident)
            if ident in self.refuted or ident in self.confirmed:
                continue                                  # already resolved this episode -- closed
            if ident not in self.candidates:
                self.candidates[ident] = m
                self.attempts.setdefault(ident, 0)
                added += 1
        self._last_added_new = added
        return added

    # ---- causal elimination: consume validate() verdicts over the accumulated causal history ----
    def update(self, history, phase="exploit"):
        """Validate each live candidate against the accumulated history. Falsified -> refuted (closed);
        confirmed -> confirmed. Persists across resets because the resolution is recorded here, not
        recomputed from scratch each compose."""
        for ident in list(self.candidates):
            m = self.candidates[ident]
            r = _val.validate(m, history, phase=phase)
            v = r.get("verdict")
            if v == "falsified":
                self.refuted[ident] = dict(reason="prediction-falsified", hold_rate=r.get("hold_rate"),
                                           n=r.get("n"))
                del self.candidates[ident]
                self._resets_at_last_move = self.resets      # a verdict formed -> the ledger MOVED
            elif v == "confirmed":
                self.confirmed[ident] = dict(hold_rate=r.get("hold_rate"), n=r.get("n"))
                del self.candidates[ident]
                self._resets_at_last_move = self.resets      # a verdict formed -> the ledger MOVED
            # untested / provisional -> stays live

    # ---- hypothesis-driven resets: what to test next (breadth-first elimination) ----
    def next_hypothesis(self):
        """Pick the live candidate to test on the next reset: fewest attempts first (so the space shrinks
        broadly rather than fixating), tie-broken by higher confidence. None if nothing live."""
        if not self.candidates:
            return None
        ident = min(self.candidates,
                    key=lambda i: (self.attempts.get(i, 0), -getattr(self.candidates[i], "confidence", 0.5)))
        self.attempts[ident] = self.attempts.get(ident, 0) + 1
        return self.candidates[ident]

    def mark_reset(self):
        self.resets += 1

    # ---- the COMMITTED-BUT-INERT terminal condition ----
    # An objective is committable (live candidates exist) and the agent has pursued through many resets, yet
    # the refutation engine has produced ZERO verdicts -- nothing refuted, nothing confirmed. That is
    # epistemic inertia: acting without learning. It is distinct from deduction_exhausted (the space was
    # ruled out -- the ledger DID move) and from the no-objective stall (here an objective IS committed each
    # cycle). It is EARNED, not a timer: it requires live candidates, that the ledger has never moved this
    # episode, and that enough resets have elapsed -- and it RESETS the instant any verdict forms, so a
    # delayed-reward game (which still produces confirmations before the reward arrives) never trips it.
    # Generous so the refutation engine gets minutes of genuine chances before inertia is concluded -- a
    # game that produces its first verdict late should survive, not be cut off in seconds. This is the
    # EARNED epistemic threshold (attempts); the dumb wall-clock ceiling in the reason-first loop is the
    # separate "never hours" guarantee. ~2-4 min of frozen pursuit on a typical game.
    INERT_MIN_RESETS = 64

    def inert(self, min_resets=None):
        k = self.INERT_MIN_RESETS if min_resets is None else min_resets
        moved = (len(self.refuted) + len(self.confirmed)) > 0
        return (len(self.candidates) > 0 and not moved
                and (self.resets - self._resets_at_last_move) >= k)

    def is_inert(self, won=False):
        return self.verdict(won=won)["status"] == "inert"

    # ---- the verdict ----
    def live(self):
        return list(self.candidates.values())

    def verdict(self, won=False):
        n_lic = len(self.seen); n_ref = len(self.refuted); n_con = len(self.confirmed); n_live = len(self.candidates)
        if won:
            return dict(status="won", **self._counts())
        if n_live > 0:
            if self.inert():
                return dict(status="inert", **self._counts(),
                            scope=(f"committed an objective across {self.resets} reset(s) but the refutation "
                                   f"engine produced ZERO verdicts -- {n_live} licensed molecule(s) remain "
                                   f"untestable under the current pursuit (inert, not refuted). No progress is "
                                   f"observable UNDER THIS PURSUIT -- not a claim of unsolvability (a molecule "
                                   f"is live but cannot be reached to test)"))
            return dict(status="composing", **self._counts())
        if n_con > 0:
            # tested the space; a mechanic is confirmed but the game is unwon -> pursuit, not exhaustion
            return dict(status="confirmed_no_win", **self._counts(),
                        note="a molecule is confirmed but the game is unwon (understanding without a win) "
                             "-> PURSUIT_FAILED, not exhaustion")
        if n_lic > 0 and n_ref == n_lic:
            est = (f" (carrying {len(self.established)} established molecule(s) from prior level(s))"
                   if self.established else "")
            return dict(status="deduction_exhausted", **self._counts(),
                        scope=(f"exhausted the observation-licensed vocabulary ({n_lic} molecule(s), all "
                               f"refuted across {self.resets} reset(s)){est}; unsolvable UNDER THIS GRAMMAR -- "
                               f"not a claim of unsolvability (a molecule outside the current vocabulary could "
                               f"win)"))
        # licensed nothing at all -> never got started; that is OBJECTIVE_INVALID's territory, not exhaustion
        return dict(status="objective_invalid", **self._counts(),
                    note="no licensed candidate was ever formed -> OBJECTIVE_INVALID (never started), distinct "
                         "from exhaustion (formed candidates and ruled them all out)")

    def exhausted(self, won=False):
        return self.verdict(won=won)["status"] == "deduction_exhausted"

    def _counts(self):
        return dict(licensed=len(self.seen), refuted=len(self.refuted), confirmed=len(self.confirmed),
                    live=len(self.candidates), established=len(self.established),
                    episode=self.episode, resets=self.resets, last_added_new=self._last_added_new)

    def explain(self):
        lines = [f"refutation ledger (episode {self.episode}, {self.resets} reset(s)):"]
        lines.append(f"  licensed={len(self.seen)} refuted={len(self.refuted)} "
                     f"confirmed={len(self.confirmed)} live={len(self.candidates)} "
                     f"established={len(self.established)}")
        for i in self.established:
            lines.append(f"  [=] {i}  established (confirmed in a prior level)")
        for i, e in self.refuted.items():
            lines.append(f"  [x] {i}  refuted (hold_rate={e.get('hold_rate')}, n={e.get('n')})")
        for i, e in self.confirmed.items():
            lines.append(f"  [v] {i}  confirmed (hold_rate={e.get('hold_rate')}, n={e.get('n')})")
        for i in self.candidates:
            lines.append(f"  [?] {i}  live (attempts={self.attempts.get(i, 0)})")
        return "\n".join(lines)

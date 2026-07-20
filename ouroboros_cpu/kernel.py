"""kernel.py -- the reason-first control loop (the moon-landing loop), Step 2 of the refactor.

INVERSION: composition is the DEFAULT entry. The reactive mover is demoted to two CALLED subroutines
(pursue, explore) injected as functions -- it is never a competing top-level policy. This makes the
old belief-plateau escalation band-aid obsolete: there is no "reactive default to escalate out of",
because reasoning is the default.

ATTRIBUTION SPLIT (the core of Step 2): a failed level must be diagnosed, not blamed on the composer by
reflex. Two distinct outcomes:
  * OBJECTIVE_INVALID -- the objective's predicate was SATISFIED but produced no reward (the binding/rule
    is wrong), OR no justifiable objective could be composed at all. -> RECOMPOSE (the composer was wrong).
  * PURSUIT_FAILED   -- the objective is fine but the executor could not REACH the predicate. -> EXPLORE to
    navigate the obstacle, then RETRY; only after exploration also fails is it an honest pursuit failure.
A movement bug must NEVER trigger a recompose -- that would falsely blame the composer and discard a
correct rule. The split is what prevents that.

UNEXPLAINABLE = UNCOMMITTED: an objective with no justification is not pursued; it is treated as
OBJECTIVE_INVALID immediately. The explanation IS the commitment the action flows from.

This module has NO platform / game dependencies. compose_fn / pursue_fn / explore_fn are injected, so it
is verified on SYNTHETIC scenarios (constructed from principles, not from any real game) and later wired
to the real composer + mover without changing this logic.
"""


class Outcome:
    SUCCESS = "success"
    OBJECTIVE_INVALID = "objective-invalid"   # wrong rule / unjustifiable -> recompose
    PURSUIT_FAILED = "pursuit-failed"         # right rule, executor stuck even after exploring
    MODEL_INCOMPLETE = "model-incomplete"     # objective justifiable + predicate reached + still no reward, and
                                              # recompose keeps failing -> the grammar lacks the needed dynamic;
                                              # emit a residual and hand to the evolvability engine (mint/co-opt).
    DEDUCTION_EXHAUSTED = "deduction-exhausted"  # EARNED give-up: licensed candidate space fully refuted
    INERT = "inert"                              # EARNED give-up: objective committed, but the refutation
    #                                              engine produced zero verdicts across many resets (acting
    #                                              without learning -- distinct from exhaustion and from stall)


# composer reason codes (already emitted by objective_validator) -> attribution
_REASON_OBJECTIVE_INVALID = {"predicate-satisfied-no-reward"}        # geometry met, no reward -> wrong binding
_REASON_PURSUIT_FAILED = {"reward-unreached", "predicate-unreached"} # couldn't reach the predicate


def attribute(pursue_result):
    """Map a pursue result to the attribution split. Defaults to PURSUIT_FAILED (never blame the composer
    by default -- a movement failure is the safer assumption than a wrong rule)."""
    if not isinstance(pursue_result, dict):
        return Outcome.PURSUIT_FAILED
    if pursue_result.get("validated") or pursue_result.get("success"):
        return Outcome.SUCCESS
    reason = pursue_result.get("reason") or (pursue_result.get("detail") or {}).get("reason")
    if reason in _REASON_OBJECTIVE_INVALID:
        return Outcome.OBJECTIVE_INVALID
    if reason in _REASON_PURSUIT_FAILED:
        return Outcome.PURSUIT_FAILED
    return Outcome.PURSUIT_FAILED


class Kernel:
    """Compose-first control loop for ONE level's attempt. Multi-level coast/recompose economy is Step 5;
    here the loop is: compose -> pursue -> attribute -> (explore+retry on pursuit-failure) ->
    (recompose on objective-invalid). Returns the attributed outcome and a per-attempt trace for the
    proctor gate (every decision shows its work)."""

    def __init__(self, compose_fn, pursue_fn, explore_fn,
                 max_recompose=4, max_pursue_retries=2):
        self.compose_fn = compose_fn       # perception -> {spec, justification, ...} | None
        self.pursue_fn = pursue_fn         # objective -> {validated|success, reason, ...}
        self.explore_fn = explore_fn       # objective -> navigates the obstacle (side effect); returns bool moved
        self.max_recompose = max_recompose
        self.max_pursue_retries = max_pursue_retries
        self.trace = []

    def _log(self, **kw):
        self.trace.append(kw)

    def run_level(self, perception):
        """Drive one level. Returns (Outcome, objective, trace)."""
        self.trace = []
        last_obj = None
        self._discovered = False                  # discovery-exploration fires at most once per level
        for rc in range(self.max_recompose):
            obj = self.compose_fn(perception)
            # UNEXPLAINABLE = UNCOMMITTED: no objective, or one with no justification, is not pursued.
            if obj is None or not obj.get("justification"):
                self._log(phase="compose", committed=False,
                          reason="no justifiable objective" if obj is None else "objective lacks justification")
                # EXPLORE TO DISCOVER -- ONCE. No justifiable objective yet is a cue to explore the space and
                # surface evidence, THEN recompose. But re-exploring (and re-RESETTING) on every recompose when
                # the first pass surfaced nothing is just reset-spam with nothing learned -- so we explore to
                # discover at most once per level; if it still can't commit, we give up rather than thrash RESET.
                if not self._discovered:
                    self._discovered = True
                    moved = self.explore_fn(None)
                    self._log(phase="explore", recompose=rc, discover=True, moved=bool(moved))
                    if moved:
                        continue                    # recompose with whatever the single discovery pass surfaced
                return Outcome.OBJECTIVE_INVALID, obj, self.trace
            last_obj = obj
            self._log(phase="compose", committed=True, recompose=rc,
                      objective=obj.get("spec"), justification=obj.get("justification"))

            # pursue, with explore-before-failure on pursuit shortfalls
            for attempt in range(self.max_pursue_retries + 1):
                res = self.pursue_fn(obj)
                outcome = attribute(res)
                self._log(phase="pursue", attempt=attempt, outcome=outcome,
                          reason=res.get("reason") if isinstance(res, dict) else None)
                if outcome == Outcome.SUCCESS:
                    return Outcome.SUCCESS, obj, self.trace
                if outcome == Outcome.OBJECTIVE_INVALID:
                    break                       # the rule is wrong -> recompose (do NOT keep pursuing it)
                # PURSUIT_FAILED: explore to navigate the obstacle, THEN retry -- never blame the composer yet
                if attempt < self.max_pursue_retries:
                    moved = self.explore_fn(obj)
                    self._log(phase="explore", attempt=attempt, moved=bool(moved))
                    if not moved:
                        break                   # explorer can't move either -> honest pursuit failure
            else:
                # exhausted pursue retries (+explore) without success and without objective-invalid
                return Outcome.PURSUIT_FAILED, obj, self.trace
            # fell through via break: if the break was objective-invalid, recompose; if explorer stuck, fail
            if outcome == Outcome.PURSUIT_FAILED:
                return Outcome.PURSUIT_FAILED, obj, self.trace
            # else outcome == OBJECTIVE_INVALID -> loop recomposes
        return Outcome.OBJECTIVE_INVALID, last_obj, self.trace

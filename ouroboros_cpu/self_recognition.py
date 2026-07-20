"""self_recognition.py -- the MIRROR SELF-RECOGNITION test, INDUCED, not forced.

We do not hand the agent an avatar/ghost split (that would be us supplying the answer). We give it only:
  (R) its OWN causal footprint-trajectory -- what responds to its actions, the causal-residual self that
      proprioception already computes; and
  (X) the trajectories of ALL other moving objects, UNLABELLED.
The agent then asks, of each object, "is that me -- under some molecule, at some lag?" by fitting the DELAY
operator against R, and COMMITS a self-recognition ONLY on a falsifiable match (residual near zero over a
real fraction of frames). The recognition is produced by the data; we supply the primitives + the question.

This is the anti-forcing stance: a ghost is recognised because it reproduces the agent's own footprints
(DELAY(self,k)), not because we told the agent which cells were ghosts. Objects that do NOT reproduce the
agent's footprints are left as reactive triggers -- the world the objective is about.
"""
import delay_operator as DLY


def induce(self_footprints, object_trajectories, shape, tol=1.0, max_lag=None):
    """self_footprints: the agent's own causal trajectory (reference R), list indexed by frame.
    object_trajectories: dict oid -> trajectory for every OTHER moving object (NOT pre-split).
    Returns recognised delayed-selves (each a typed component with a falsifiable prediction) + the residual
    reactive triggers. The agent proposes; the DELAY fit disposes."""
    if not self_footprints or not object_trajectories:
        return dict(recognized_selves=[], triggers=[])
    fork = DLY.classify_action_invariant(object_trajectories, self_footprints, shape, tol=tol, max_lag=max_lag)
    recognized = []
    for oid, fit in fork["delayed_self"]:
        recognized.append(dict(
            oid=oid, ctype="self", modality="delayed-self", fit=fit, description=DLY.describe(fit),
            confidence=round(max(0.5, 1.0 - fit["residual"]), 2),
            evidence=(f"object {oid} reproduces my own footprints as {DLY.describe(fit)} "
                      f"(residual {fit['residual']} over {fit['overlap']} frames) -> it is me, lagged"),
            prediction=dict(kind="delayed_self", molecule=fit["molecule"], lag=fit["lag"],
                            text=(f"object {oid} keeps tracking my path under {fit['molecule']} at lag "
                                  f"{fit['lag']}; if it stops reproducing my lagged footprints, it is NOT me"))))
    triggers = [dict(oid=oid, ctype="reactive-trigger", fit=fit) for oid, fit in fork["trigger"]]
    return dict(recognized_selves=recognized, triggers=triggers)

# P5-GOAL: pose the problem by minting one level up

**Idea (agreed with Isaiah).** The same MDL minting loop runs on two surprise streams. The TRANSITION residual
("did the world change as Γ predicted?") mints AFFORDANCES — the vocabulary of what's doable (built:
INTENDED_FREE). The REWARD/PROGRESS residual ("did success show up where my goal-guess predicted?") mints the
GOAL — a predicate `R(avatar, target)` whose truth coincides with progress, written in the affordance vocabulary.
This is the sensorimotor analog of an LLM posing a well-formed problem from an underspecified prompt: priors +
context → the most plausible intent. Here the "prior" is a small set of relations over salient objects, and the
"context" is the progress the avatar's own actions produce.

**Built this beat (`src/newhorse/redux_arch/goal.py`, `tests/test_goal.py`, 5 tests).**
- `pose_goal(steps)` — for each candidate target, score the best before-state predicate `R(avatar, candidate)`
  that compresses the progress stream by two-part MDL; return the candidate whose relation compresses it most.
  The load-bearing discovery is **TARGET SELECTION**: with a distractor object present, the poser must find that
  progress coincides with `ACTS_TOWARD` the RIGHT object. Verified it selects the reward-linked target (not the
  distractor), tracks that target when it moves, and returns NOTHING under (a) random progress and (b) near-empty
  reward — the noise and SUPPORT guards, exactly the ls20 zero-win / sparse-reward situation.
- `static_salient_targets(frames)` — design-prior candidate proposal: static (never-moving) non-avatar/non-bg
  colours, ranked by distinctness (smallest footprint first). Verified it picks the small distinct landmark over
  a large wall wash.
- **Design law pinned in code:** the NOVELTY TEST does not apply at the goal level — selecting an existing atom
  (`ACTS_TOWARD`) AS THE GOAL is correct, not a re-derivation failure. `LiveMintBridge`'s navigation-progress
  residual, earlier filed as "re-derives ACTS_TOWARD," IS the goal-poser reframed.

## LAW-0 signal audit (why real grounding is deferred, not skipped)
Rendered/inspected the tu93 recordings for a real, dense, POSITIVE progress signal to feed the poser. Findings:
- **The bottom bar is a TIMER, not a progress bar.** Row 63 starts full magenta (colour 6) and black (0) fills it
  as time ELAPSES. The run that WON (a9e77dad: `levels_completed` 0→1 at step 42) still had a FULL magenta bar at
  the win; the run that timed out filled to all-black with no level. So "bar fills = progress" is exactly
  backwards — it is a countdown. Using it as reward would invert the signal. (This is precisely the LAW-0 trap:
  the pixels, not the plausible name, decide.)
- **The only true positive reward is `levels_completed`**, and it is SPARSE (0 or 1 event per recorded episode;
  ls20: none ever). One positive cannot clear the MDL SUPPORT bar directly.

**Consequence / next step.** The goal-poser mechanism is proven; grounding it on REAL frames needs a real,
dense-enough, positive signal, which these passive recordings do not readily supply. The honest routes (next
beats): (1) anchor on the sparse win but densify with a *self-supervised* progress signal that is NOT the
per-candidate geometry (e.g. reduction of belief-state surprise, or a learned sub-goal detector), scored for
target selection against the win; (2) go LIVE and let the agent *probe* — act toward each salient candidate and
watch which one moves the true reward (active problem-posing, the interactive superpower replay can't exercise);
(3) once a target is posed, wire it into action selection so it can move `levels_completed`. Do not force a
circular geometric proxy on real frames — it would "select" whatever target the proxy was defined against.

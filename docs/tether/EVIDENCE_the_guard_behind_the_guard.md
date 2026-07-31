# EVIDENCE — THE GUARD BEHIND THE GUARD

*Recorded 2026-07-31 at commit `3129e65`. No live arm was run and none was needed; this is a source
receipt plus six synthetic tests (`tests/test_click_native_guard.py`). This is EVIDENCE. It records what
the source says and how to overturn it. It does not conclude.*

## What was believed, and on what

CLASSIFIER 14 read: *a natively click-routed game never reaches the escalation organ; `_decide` returns at
the `click_native` exit before `_modality_escalate` is called.* One live instance carried it — `su15`,
family `click`, `frozen=True`, `responsive_fraction 0.00`, 115 charged steps, one label ever emitted, `A7`
available and never tried, `escalations = 0`.

The NEXT list turned that reading into an arm: let the organ be consulted before the native-click return, or
move the return below it, because *"the gate is OPEN and reachability is the whole of it."* It also carried
its own precondition, in the same sentence: *"If that reasoning does not survive contact with the source, the
arm is not ready."*

## It did not survive contact with the source

`_decide` guards the `click_native` return at `policy.py:827`:

```python
if self.family == CLICK and self._pre_esc_family is None:
    return self._exit("click_native", self._act_click())
```

`_modality_escalate` opens, at `policy.py:873`, with the **same predicate**:

```python
if self.family == CLICK and self._pre_esc_family is None:
    return None                                  # the committed click organ owns this game
```

So on exactly the population the arm targets, control arriving at the organ changes nothing: the organ
refuses the game on its own account. The proposed change is a **provable no-op**, and it would have cost a
live sweep to discover that.

## The state is absorbing, so the exemption cannot lapse on its own

The only assignment of a non-None value to `_pre_esc_family` is `policy.py:916`, and it sits **inside**
`_modality_escalate`, downstream of the line-873 guard. A game routed to CLICK by action-set routing
(`family == PENDING and not dirs and 6 in avail`) therefore has `_pre_esc_family is None` for the whole
episode, by every path the code contains. Reachability is not the binding constraint; the second guard is,
and it is unreachable-to-lift from inside.

## The exemption is load-bearing, so lifting it is not a tweak

The organ's own docstring states that committed verified win organs — two-body, multi-avatar, *and a
natively-routed click game* — are "exempt outright". `tn36` is a banked click win. Removing the exemption
puts a win at risk and is a change that needs its own prereg, its own control arm, and its own beat. It is
not a reachability fix.

## What was banked instead

`tests/test_click_native_guard.py`, six tests, all green at `3129e65`:

- the precondition, measured not assumed: a click-only action set routes to CLICK and every decision leaves
  `_decide` at `click_native` (this is CLASSIFIER 14's half that *is* true);
- the finding: on the same frozen state, `EngagementMeter.escalate(labels)` hands back `A7` while
  `_modality_escalate(labels)` returns `None`;
- the A/B that isolates the guard — two policies driven through identical histories (same board, same action
  set, same 30 steps, `recent_window` asserted equal), differing **only** in `_pre_esc_family`: the exempt one
  gets `None`, the non-exempt one gets `A7`;
- the absorbing state, driven 120 steps past the escalation window;
- the source invariant that every non-None assignment to `_pre_esc_family` lives inside the organ;
- the no-op proof: the guard string appears in both `_decide` and `_modality_escalate`.

**Mutation check.** With the line-873 guard replaced by `if False:`, three of the six fail
(`test_the_meter_WOULD_escalate_but_the_organ_refuses_the_game`,
`test_the_guard_not_the_reachability_is_what_excludes_the_game`,
`test_the_two_guards_are_the_same_predicate`). The patch was reverted with `git checkout --`; the tree is
otherwise untouched. A test suite that would have passed either way would not be a receipt.

## How to overturn this

1. Show a non-None assignment to `_pre_esc_family` reachable **without** first passing line 873 — that breaks
   the absorbing-state argument and re-opens the arm as written.
2. Show a natively click-routed game whose family is CLICK with `_pre_esc_family` non-None in a live receipt —
   same consequence, measured rather than argued.
3. Decide, deliberately and with a prereg, that the click exemption should be lifted; then these tests are
   *supposed* to fail, and the failure is the notice that a banked win (`tn36`) is now in scope.

## What this re-prices

CLASSIFIER 14's wording — "The guard inside the organ is not the mechanism; control never arrives" — is half
wrong. Control never arrives, and the guard inside the organ *is* also the mechanism. Both are true; the
second one is the one that matters, because it is the one that survives the fix aimed at the first.

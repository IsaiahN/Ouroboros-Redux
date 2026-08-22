# PREREG — D-3: THE VERIFIER IS BLIND TO THE FAILURE IT EXISTS TO CATCH (2026-08-18)

## THE DEFECT, VERIFIED
`safe_cleanup.py:2250`, in `verify_critical_data()`:
```python
    # Positive-score games
    c.execute('SELECT COUNT(*) FROM game_results WHERE final_score > 0')
```
**AND `safe_cleanup.py:683`, in `_clean_zero_score_games()` — THE SAME FILE:**
```python
    evidence = ('(final_score > 0 OR win_detected = 1 OR level_completions > 0)')
```
**THE CLEANER WAS CORRECTED ON 2026-08-13 AND ITS VERIFIER WAS NOT.** The 2026-02-24
catastrophe was the deletion of **zero-score** rows — *"Zero-score game results are
essential scientific data. They record what agents tried and failed."* **A verifier that
counts only `final_score > 0` CANNOT SEE THAT LOSS. It would have reported the corpus
preserved throughout the exact event it is named for.**
**THIS IS WORSE THAN AN ABSENT CHECK: IT CERTIFIES.**

## THE CHANGE
One expression, aligned to the rule already live 1,500 lines above it in the same file:
count by **EVIDENCE** (`final_score > 0 OR win_detected = 1 OR level_completions > 0`),
not by score. The reported key is renamed so the metric cannot be misread as a score count.

## FALSIFIERS — two directions, both required
**F1 · IT DETECTS A LOSS THE OLD ONE MISSES.** Fixture with rows that are zero-score but
CARRY EVIDENCE (a win at score 0, a level completion at score 0). Delete them. **The OLD
verifier's count is UNCHANGED (blind). The NEW verifier's count DROPS.** If the new count
does not move, the fix does nothing.
**F2 · IT DOES NOT FIRE ON A NO-OP.** With nothing deleted, the new count is stable across
runs and equals the evidence-bearing row count exactly. If it drifts, it is not a verifier.
**AND THE KNOWN-NEGATIVE:** a genuinely worthless row — zero score, no win, no level — must
NOT be counted by either verifier. The fix must not simply count everything, which would
pass F1 for the wrong reason.

## UNDO
One expression. No schema change, no data migration, nothing rewritten.

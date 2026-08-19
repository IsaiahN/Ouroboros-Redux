# F-8c — HOW FAR BACK DO THE GREEN READINGS REACH?

AUTHORITY: Isaiah — *"everything it ever reported green can't be discharged by a code fix.
A verifier structurally blind to the failure it existed to catch means every green it
emitted was a statement about nothing, and how far back that reaches is a read nobody has
taken."* **This is that read. Nothing was fixed under it.**

THE SUBJECT: `safe_cleanup.py::verify_critical_data`, which until 2026-08-18 counted
`game_results WHERE final_score > 0` — the exact key whose deletion destroyed ~80% of the
metrics corpus on 2026-02-24. A verifier keyed on the condemned quantity certifies the
catastrophe it is named for.

---

## THE ANSWER COMES IN THREE PARTS, AND THEY DISAGREE ABOUT HOW BAD IT IS

### 1 · THE VERIFIER'S OWN GREENS: **THERE ARE NONE TO RE-READ. NOT ONE.**
Searched every `.runs` box, `log/`, every `.md`, and the full commit history:

| where a green could have been recorded | found |
|---|---|
| captured stdout in any `.runs` box or `log/` | **0** |
| any `.jsonl`, table, or status file | **0** |
| cited in any document | **0** (the only `.md` hits are my own writings *about* the defect) |
| cited in any commit message | **0** (only today's two commits, both naming it as a defect) |

`verify_critical_data` **prints to stdout and returns a dict. It persists nothing.** Every
textual match anywhere in the tree is source code, never output.

**THIS IS NOT RELIEF, AND I WILL NOT REPORT IT AS RELIEF.** "Nothing to re-read" here does
not mean the greens were harmless — it means **their history is unrecoverable.** We cannot
now know what was on screen when someone decided a cleanup had gone fine. **Rung 0e sitting
directly underneath F-8c: the record that would have needed re-reading was never made.**

### 2 · AND IT PRINTS `[OK]` WITH NO PREDICATE AT ALL
```python
print(f'  Positive-score games: {good_games:,} [OK]')
```
**There is no threshold, no comparison, and no before/after.** `[OK]` is printed
unconditionally — it would print `0 [OK]` on a totally destroyed corpus. So the defect is
worse than "keyed on the wrong quantity": **even keyed on the right quantity it could not
have failed**, because nothing about the number is ever tested. *(The D-3 fix corrected the
predicate; it did not add a verdict. That is still open — see below.)*

### 3 · THE GREENS THAT **WERE** EMITTED, REPEATEDLY, AND THIS IS THE REACH: **257 DAYS**
The re-readable greens are the **test's**, not the verifier's. `test_verify_critical_data`
in `tests/test_safe_cleanup.py`:

```python
c.execute('INSERT INTO game_results VALUES (?, ?, ?)', ('game1', 5, 'session1'))
stats = self.cleaner.verify_critical_data(verbose=False)
self.assertEqual(stats['good_games'], 1)
```

**The fixture holds ONE row, and its score is 5. There is no zero-score row in it.** On that
fixture the condemned predicate (`final_score > 0`) and the correct predicate (evidence)
**return the same answer**. The test is *structurally incapable* of failing on the defect it
appears to guard.

**HOW FAR BACK: authored 2025-12-04, green until 2026-08-18. 257 days, across 281 commits
to this repository.** Every one of those greens was a statement about nothing.

**AND A THIRD INDEPENDENT INSTANCE OF SITE-SCOPED KNOWLEDGE, INSIDE ONE TEST FILE.** The
same file already contains `_insert_game_results(zero_count, positive_count)` at line 122 —
a helper that writes exactly the discriminating fixture, used by other tests. **The test that
needed it sits 168 lines below it and hand-rolls a single positive row instead.** The right
tool was present, upstream, in the same buffer. Same shape as `safe_cleanup.py`'s 561-line
and 1,575-line cases.

---

## THE FINDING THAT MATTERS MOST OPERATIONALLY, AND IT WAS NOT WHAT WAS ASKED
**THE AUTOMATED CLEANUP PATH NEVER CALLS THE VERIFIER AT ALL.**

`health_monitor.run_safe_cleanup()` — the Rule-12 janitor that actually deletes rows in
production — calls `cleaner.cleanup(dry_run=False, verbose=False)` **and stops there.**
`verify_critical_data` has exactly one non-test caller: `safe_cleanup.py`'s `main()`, reached
only when a human types `python safe_cleanup.py`.

**So the deletions that actually happened were never verified — blind verifier or not.**
The blindness was the second line of defence failing. **The first was that the defence was
not on the road.** This is why part 1 found no records: there was no automated occasion on
which a green would have been produced.

### FOUND IN SITU — THE CADENCE COMMENT IS WRONG (feeds the divergence sweep)
`evolution_runner.py:1616` — `# Rule 12: Safe cleanup every 10 generations`
`health_monitor.py:119,126` — docstring **and code** say **every 30** (`current_generation % 30`).
**The caller's comment states a cadence three times more frequent than the callee runs.**

### AND ONE THAT IS MINE, INTRODUCED TODAY
The D-3 fix changed the predicate to evidence-based and **left the label reading
`Positive-score games`.** The output now says one thing and counts another — the mode-audit
genus, authored by me, eight hours old. **Named here rather than quietly patched**, and
fixed under the existing D-3 gate.

---

## WHAT THIS OWES UPWARD
1. **The verifier still has no verdict.** Counting the right rows is not verifying; it needs
   a before/after and a failing condition. That is a build, not a read — **held**, and
   written up in Decision Analysis form rather than taken.
2. **Putting the verifier on the automated path is APPARATUS → Seat 3**, and it interacts
   with the janitor question already awaiting ruling (V2).
3. **The 257-day green cannot be discharged retroactively.** What can be said is what the
   fixture could and could not distinguish, and that is now written down.

---

## TWO THINGS THE FIX-VERIFICATION TURNED UP, BOTH ABOUT MY OWN GATES

### A · THE PRE-COMMIT HOOK I INSTALLED TODAY COVERS 144 OF 473 FILES — AND NOT THIS ONE
`ruff check .` — what the hook runs — resolves to **144 `.py` files**: `tests/**` (89),
`engines/egocentric/**` (32), `tools/**` (23). The repo has **473**.
**`safe_cleanup.py` is not in the covered set**, and neither is any other root-level module.

**The scope is DELIBERATE and DOCUMENTED** — `pyproject.toml:5-15` states that legacy files
are out of scope via `include`. So this is not a hidden defect in the config.
**What was wrong was my claim.** I reported the hook as protection against the class of lint
failure I had shipped three times, and the file at the centre of D-1, D-2 and D-3 sits
outside it. **A gate's green is a statement about its scope, never about the repo** — which
is F-8c's own lesson arriving one level up, on my own instrument, the same day.
*(Checked, so this is not a guess: running ruff on `safe_cleanup.py` by name — which bypasses
`include` — reports E402, S608, S110 and SIM105 findings that `ruff check .` never sees.)*

### B · A STANDING RED THAT DEMANDS THE CONDEMNED BEHAVIOUR
`tests/test_safe_cleanup.py` has **4 failures, and they are pre-existing** — verified by
stash-and-rerun: **4 before my edit, 4 after, the same four names.** My change is neutral.

But one of them is not neutral in meaning:
```
test_zero_score_games_deleted
>  self.assertEqual(results['tables_cleaned']['game_results']['deleted'], 50)
E  AssertionError: 0 != 50
```
**The test asserts that 50 zero-score rows MUST be deleted.** That is precisely the behaviour
condemned on 2026-02-24 and removed on 2026-08-13. The function now correctly deletes 0.
**So the test has been RED for five days while encoding the defect as the requirement**, and
a red nobody reads is the same instrument failure as a green nobody checks.
**Not fixed here** — rewriting an assertion to match new behaviour is exactly the move that
needs a ruling, not a night shift. **SUBJECT/GROUND-GATED → Seat 3.**

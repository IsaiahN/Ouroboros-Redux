# THE PROPAGATION READ (2026-08-18) — READ, NOT SWEEP

AUTHORITY: Isaiah — *"I want it named as a genus, and I want to know how many other
known-fixed defects are live on a sibling branch. Read, not sweep."*
The genus is named in `record/canon/THE_LADDER.md` (**SITE-SCOPED KNOWLEDGE**). This is the count.
**Nothing was swept, moved, or fixed.**

---

## THE POPULATION, FIRST — BECAUSE THE FIRST ANSWER I GOT WAS AGAINST A WRONG DENOMINATOR
Deriving markers automatically from fix-shaped commits gave **"1 of 47"**. That number was
worthless and I am recording why rather than reporting it: **the lineages diverged at
`5800f9c`, 2026-02-17**, and 47 was dominated by commits *older than the fork*, which are
present in both by inheritance and can never fail to cross. Restricting to post-divergence
fixes collapsed the answerable population to **1**, because Redux's post-fork fix work went
almost entirely into files the sibling never had.

**So marker-matching is the wrong instrument here. Byte-identity is the right one**, and it
needs no proxies at all.

## THE MEASUREMENT

| | Redux (`v4-cold`) | sibling (`Ouroboros @ v4-economies-of-thought`, frozen 2026-08-10) |
|---|---|---|
| `.py` files | **473** | **364** |
| shared paths | **332** | |
| — **byte-IDENTICAL** | **323** | |
| — diverged | **9** | |
| files only on that side | 141 | 32 |

**THE NINE DIVERGED FILES** (`+added / −present-only-in-sibling`):
```
cognitive_loop.py                            +1497  -388
cognitive_game_player.py                      +554  -194
safe_cleanup.py                                +63    -6
tools/verify/hermetic.py                       +48   -16
engines/cognition/cognitive_router.py          +38    -2
engines/reasoning/symbolic_reasoning_engine.py +26   -24
engines/perception/perceiver.py                 +8   -22
tools/replay_viewer.py                          +3    -3
evolution_runner.py                             +0   -12
```

## THE ANSWER TO THE QUESTION AS ASKED: **NO OTHERS. TWO, AND THEY WERE ALREADY COUNTED.**
A byte-identical file **cannot** hold a fix here that is missing there. So the entire surface
on which a known fix could have failed to cross is those **9 files** — and of the nine,
`safe_cleanup.py` is the only one carrying known defect fixes. Its diff contains exactly the
two already on the board: the **2026-08-13 evidence rule** and the **2026-08-18 D-3
verifier**. **There is no third.** The exposure is bounded and enumerable, which is the
useful part of this result.

**R4, both ways.** Known-positive: `safe_cleanup.py` must appear as diverged — it does.
Known-negative: files nobody touched must appear identical — **323 do**, so the instrument
is not reporting divergence everywhere.

**AND THE INHERITANCE SURFACE IS THE MIRROR OF THAT NUMBER.** Those same 323 identical files
are where **every defect is guaranteed to be in both lineages with no instrument needed** —
D-1 and D-2 among them, as already measured. **Defect surface 323 files wide; fix surface 9.**
That ratio *is* the genus, stated in files.

---

## WHAT THE READ FOUND THAT NOBODY ASKED FOR — AND IT RUNS THE OTHER WAY

**`tools/fork_divergence.py` only ever looks in one direction: fixes here, missing there.**
Nothing had looked for **capability in the sibling that is missing HERE.** The `-12` on
`evolution_runner.py` is that, and it is not cosmetic:

```python
-from disk_space_monitor import DiskSpaceMonitor
...
-            # Disk-space report (report-only, generation boundary)
-            monitor = DiskSpaceMonitor(db_path=db_path)
-            ok, msg, info = monitor.check_disk_space()
```

**The sibling monitors disk space at every generation boundary. Redux removed the call site
on 2026-08-10** — the day work moved to the cold v4 run.

**`disk_space_monitor.py` WAS NEVER DELETED. It is still here, and it is called from
nowhere.** (Its only remaining mention in the tree is as a filename string in a cleanup
tool's keep-list.) **GENUS: built-plumbed-never-called, degree *the organ is never called* —
the second instance found today, after the frontier-checkpoint system.**

**AND THE SIBLING HAS THE GATE THAT WOULD HAVE CAUGHT IT: `tests/gate/test_disk_monitor_wired.py`.
Redux inherited neither the wiring nor its guard.**

### THE PART THAT LANDS ON ME
**On 2026-08-18 I built `tools/disk_ceiling.py` from scratch**, to Seat 3's order, without
knowing that a disk monitor existed in this repo, had been wired at the generation boundary,
had been silently unwired eight days earlier, and had a gate test guarding it one directory
across. **I rebuilt a capability the lineage already had because nothing indexed its
removal.** That is not a footnote to the genus, it is its cleanest receipt.

**IN MITIGATION, AND ONLY THIS MUCH:** the removed monitor was **report-only** — it printed
and continued. Isaiah's ruling was explicitly *"it gates, it does not warn... a ceiling that
logs is a ceiling that scrolls past."* So the rebuild is not a duplicate; it is strictly
stronger, and the removal of a report-only monitor was defensible. **What is not defensible
is that neither the removal nor the prior art was discoverable at the moment of rebuilding.**

## THE SHARPEST NUMBER IN THIS READ
| | Redux | sibling | **shared** |
|---|---|---|---|
| gate tests | **89** | **21** | **0** |

**Two lineages have written 110 gate tests between them and they share NOT ONE FILENAME.**
Every guard either lineage built is invisible to the other. The guards are exactly the
artefacts whose whole purpose is to stop a known defect recurring — **and they are the least
propagated thing in the project.**

---

## LIMITATIONS, STATED
- Byte-identity is measured on the **working trees** (both clean), not on branch heads.
- Identical filenames were compared; a guard **renamed** between lineages would read as
  absent on both sides. The 0-overlap figure is therefore an upper bound on the disjointness,
  though 89-vs-21 with zero matches is not plausibly all renaming.
- The sibling is **frozen and ON ICE**, so nothing there runs today. This is exposure, not
  active damage — and the 21 missing guards are the part that would matter on any revival.

## WHAT THIS OWES UPWARD
1. **`disk_space_monitor.py` is an orphaned organ in this repo right now.** Whether it is
   deleted, re-wired beneath the ceiling gate, or left as-is is **APPARATUS → Seat 3**.
2. **The one-directional instrument is a defect in my own tooling.** `fork_divergence.py`
   asks only "did our fix cross." The read that found something asked the reverse. Making it
   symmetric is a build, and I did not take it — it is in the Decision Analysis write-up.

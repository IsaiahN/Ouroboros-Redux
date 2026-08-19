# DECISION ANALYSIS — THE SCORECARD LINEAGE TAG (2026-08-19, for Seat 3)

**NOT BUILT. Awaiting a ruling.** Apparatus twice over: it changes the outward record, and it
touches allocation of what the leaderboard says this project is.

---

## THE PROBLEM, IN THREE FACTS

**1 · A hardcoded literal is on the live path.**
`game_player.py:142` `_create_scorecard_tags()` returns a list whose first element is the
string `"branch_Ouroboros-v3"`. It is called at `game_player.py:181` every time a scorecard is
opened. **8,835 of 8,836 scorecards in the worker logs carry it.** This project moved to
`v4-cold` on **2026-08-10**, so roughly nine days of published results credit the wrong branch.

**2 · A correct implementation exists and NEVER RUNS on this path.**
`arc_api_client.generate_tags()` (:357) shells `git rev-parse --abbrev-ref HEAD` and appends
`branch_{name}`, plus `commit_{short}`, `pid_`, `thread_`, `runmode_`, and a `git_unavailable`
fallback. **No `branch_v4-cold` appears in any worker log** — only `branch_Ouroboros-v3`. So
this is **not two competing tags. It is a correct organ that is not called here**, beside a
stale constant that is. *Built-plumbed-never-called, and site-scoped knowledge, in one place.*

**3 · THE PUBLISHED RECORD IS PROBABLY NOT CORRECTABLE BY US.**
Tags are set at scorecard creation (`tags: List[str]`, read from `data.get('tags', [])`).
**Our client implements no tag-update call.** Unless the ARC API supports retagging — which I
have not verified and would not test against live records without a ruling — **the 8,835
stand. Only the future is in scope.** *Every option below is about the next scorecard, not the
last one.*

---

## MUSTS (fail one → eliminated)
- **M1** future scorecards carry the branch actually in use
- **M2** nothing rewrites or backdates history; the past record is not reinterpreted
- **M3** scorecard creation cannot acquire a new failure mode — **this is the outward
  channel, and a tag builder that throws publishes nothing**
- **M4** it does not go stale at the next branch change *(this is a must and not a want,
  because a fix that goes stale is this project's most-catalogued genus)*

| option | M1 | M2 | M3 | M4 | verdict |
|---|---|---|---|---|---|
| **A · derive the branch from git at tag time**, via the SAME helper `arc_api_client` already uses (extract it so there is one implementation, not two) | ✓ | ✓ | ~ | ✓ | **survives** |
| **B · correct the literal to `"branch_v4-cold"`** | ✓ | ✓ | ✓ | **✗** | **eliminated** — same defect with a fresher value |
| **C · wire `generate_tags()` in and delete the hand-rolled list** | ✓ | ✓ | **✗** | ✓ | eliminated *for now* — changes every tag on every scorecard |
| **D · assert at startup that the tag matches git, fail loudly** | **✗** | ✓ | ✓ | n/a | eliminated — catches drift, fixes nothing |

**RECOMMENDATION: A now, C as a separate later prereg.**
A is the smallest change that satisfies the musts and reuses logic already proven in this
repo. **C is the right end state** — one tag builder rather than two is the actual cure for
the divergence — **but it rewrites every tag on the outward record and deserves its own
ruling, not a rider on this one.** D is worth keeping as a *companion* to A: an assertion
costs nothing and would have caught this nine days ago.

**M3 is marked `~` for A deliberately:** `git rev-parse` is a subprocess with a 5 s timeout, on
the scorecard-creation path, across 25 workers. **Mitigation: resolve the branch ONCE at
process start and cache it, never per scorecard.** A worker's branch cannot change mid-life.

---

## PPA — WHAT BREAKS IF THIS WORKS

**1 · THE CORPUS SILENTLY SPLITS AT THE FIX, AND THIS IS THE ONE THAT MATTERS.**
8,835 records say `v3`; everything after says `v4-cold`. **Nothing marks the boundary.** Any
query that filters by branch — ours or anyone else's — returns a truncated set with no
indication it is truncated, and a comparison of "v3 vs v4 performance" would be comparing a
**mislabelled mixture** against a correct label. *That is a worse epistemic state than
uniform wrongness, because uniform wrongness is at least detectable.*
**MITIGATION, and I would make it a condition of the fix:** stamp the first corrected
scorecards with a one-off marker tag (e.g. `lineagefix_20260819`) and record the boundary in
`PORT_LOG`, so the discontinuity is **findable rather than inferred.**

**2 · IT MAKES THE OLD RECORDS LOOK DELIBERATE.** Today the v3 tag is uniformly wrong, which
reads as a bug. After a fix it reads as a considered label that was later changed — which is a
claim nobody made.

**3 · A NEW FAILURE MODE ON THE OUTWARD CHANNEL.** Detached HEAD returns the literal string
`HEAD`; a packaged or Kaggle deploy has no git at all and gets `git_unavailable`. **A
plausible-but-meaningless tag is worse than a stable wrong one**, because it will not be
questioned. Caching at start-up bounds the cost but not this.

**4 · IT INVITES THE ASSUMPTION THAT THE REST OF THE TAG SET IS RIGHT.** `mode_`, `gen_`,
`agent_` and `game_` in that same hand-rolled list have never been checked against anything.
**Fixing the one tag that was audited implies the others were.**

---

## WHAT I AM NOT DOING, AND WHY
Not building it. **Seat 4 raised this and pressed for the one-line change; Seat 4 issues no
rulings**, and the outward record is not a place where an auditor acts on its own reading.
Ready on a ruling, with A + the caching mitigation + the boundary marker as one package.

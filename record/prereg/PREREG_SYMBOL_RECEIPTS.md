# PREREG — SYMBOL-ANCHORED RECEIPTS AND STRUCTURAL LAWS (2026-08-21)

Apparatus item approved from PROPOSAL_SYMBOL_RECEIPTS.md; KNOBS A4-2 queued the same fix for
the window laws on 2026-08-14. Two customers, one defect: a CLAIM ABOUT STRUCTURE ("this organ
is called from here"; "this call lives inside that function") is stored as a POSITION
(`file:line` ±30; a character offset from `def record_result`). Every insertion above the
position invalidates the claim without touching the fact. Measured this week: ~140 receipt
refreshes, every one a false positive; today (PORT_LOG 2026-08-21) the window laws BLOCKED the
settled suite at HEAD headroom of 50 chars (`.credit`) and 15 chars (`.route`), and the
"`_plan_gate` stays out of record_result" law fired on references at lines 4832–4975 — module-
bottom helpers AFTER `record_result` (ends 3005), not inside it. The module-bottom convention
that protects receipts is what the tail-slice law forbids. Position is not the claim.

## 1. RECEIPTS: THE FINGERPRINT IS THE CLAIM, THE LINE IS A COURTESY
1. **The site cell becomes** `file:ENCLOSING_QUALNAME/KIND:NAME#ORDINAL@LINE`. ENCLOSING is
   the innermost def/class qualname containing the site (`<module>` at top level); KIND is
   CALL (an `ast.Call` whose func is `Name`/`Attribute` named NAME), REF (a bare `Name`/
   `Attribute` of NAME — constants and annotations: route-ambiguous-band, perception-object,
   cost-flip), or DEF (the definition itself); ORDINAL is the 0-based index of that node among
   same-KIND same-NAME nodes inside ENCLOSING, in (line, column) order. NAME is the row's
   refname or its `[alias=]`, exactly as the gate resolves today. `@LINE` is the courtesy.
2. **The gate (test_wiring_registry.py) asserts, per LIVE row**: the file parses; ENCLOSING
   exists; at least ORDINAL+1 matching nodes exist inside it. The production-reference scan
   (b) is unchanged. The courtesy line is NEVER asserted: a stale `@LINE` is not red. Row
   width stays six cells — the unpack that caught the concatenation defect is kept.
3. **Per SEVERED row** the site is the organ's own DEF fingerprint (always resolvable:
   `test_symbol_still_defined` already asserts it) with the wire-break line as `@LINE`; the
   inverse-reference claim was position-free already and is untouched.
4. **The one legitimate refresh trigger** that remains: a NEW same-callee call inserted before
   the anchored one inside the same function, or a rename of the enclosing function. Both are
   structural changes to the organ's wiring; the gate names the row and the count seen.
5. **Courtesy refresh** is a tool run (`tools/wiring_receipts.py refresh`), never a gate
   failure and never CI. The gate does not write the registry.

## 2. LAWS: AST-ORDER, NOT CHARACTER DISTANCE
Each in-scope law, the fact it protects (read from the tests and KNOBS A4-2), its AST form:
- **L1 `.credit` window** (test_goal_abduction, test_level_conventions, test_lp_drive,
  test_link3 — four copies, `0 <= ci < 8000`). Fact: the spine is credited on level-up inside
  `record_result` (KNOBS A4-2: "proxies for 'the wiring call exists inside record_result'").
  AST: CALL `credit` inside `CognitiveLoop.record_result`. **The exemplar already exists and is
  green: `tests/gate/test_goal_spine.py::test_reward_wires_to_credit`.** The four copies
  become calls to a shared helper stating exactly that law.
- **L2 `.route` window** (same four, `0 <= ri < 20000`). Fact: every settlement routes
  through the residual router inside `record_result` (bank-core's note). AST: CALL `route`
  inside `record_result`.
- **L3 `_goal_abd(` after `.route(`** (test_goal_abduction, test_link3; plus `"_goal_abd(" in
  tail`). The test's own message says the order clause exists to protect L2's window. Residual
  fact: the level-up delta is banked in `record_result` after settlement routing. AST: CALL
  `_goal_abd` inside `record_result`; ORDER — the first `route` CALL precedes it in statement
  order within `record_result`.
- **L4 `_plan_gate` / `[PLAN-GATE]`** (test_plan_wire, two tests: inside the W4c→C33 comment
  region; absent from the file tail). Fact: the gate counters are initialised and narrated on
  the cycle path, before the bet commit, never in the result path. AST: the Assign to
  `self._plan_gate` and the Constant containing `[PLAN-GATE]` are inside `CognitiveLoop.cycle`
  and precede `cycle`'s `_bet_book.commit` CALL; the Dict assigned carries the keys
  g1–g7/shadow/drive/cycles; NO `_plan_gate` Name/Attribute inside `record_result`'s SUBTREE.
  Module-bottom helpers that increment the same dict (stage 4's g7 rule) are legal by design.
- **L5 the consumer clause** (test_link3 `abduced_plan(` +2000 chars; test_goal_abduction
  `abduced_plan`/`[PLAN]` in region). Fact: the abduced plan's site becomes the action inside
  `cycle`'s plan block. AST: CALL `abduced_plan` inside `cycle`, preceding the bet commit; in
  the statements after it within the same enclosing block: an Assign to `action_num` with
  Constant 6, a store to `action_data` whose value reads `_ap["site"]`, a `[PLAN]` Constant.
- **L6 lp-steer site** (test_lp_drive, SPEED-3 comment region). Fact: the ONE consumption call
  sits in the explore-widen branch of action selection. AST: exactly one CALL `lp_steer` in
  production, inside `CognitiveLoop._act`.
Out of scope, named so the boundary is closed: test_level_conventions' A3-2 comment-to-code
windows (600/1200 chars from a comment that moves WITH its code — local, never rotted) and
test_link3's player-side `"\n    def "` body slices (already function-membership). Unchanged.
Laws live in one tests-only helper (`tests/gate/_ast_laws.py`: inside / precedes / nth-call);
each of the six test files keeps its test names; bodies become helper calls.

## 3. MIGRATION
`tools/wiring_receipts.py migrate`: reads the registry with the gate's parser; for each row
resolves the claimed line to a fingerprint — a CALL/REF/DEF node of NAME whose span covers the
line, else the UNIQUE nearest such node within ±30 lines; writes the new cell with the resolved
line as `@LINE`; prints a census by KIND and a NAMED-ABSENCE list (row, claimed line, what the
region actually holds). Ties and empties are absences; the tool never chooses. Dry run on the
working tree at drafting (another build in flight): 56/60 LIVE rows resolve (19 exact, 37
within drift), all 20 SEVERED rows resolve to DEF; **four named absences**: router-core and
mint-core (the two receipts PORT_LOG already dispatched a repair for), decline-branch (site
`consumer.py:285` is `return out`; passes today on the substring "match"), goal-abduction-plan
(claims :1579; passes today on the IMPORT line at :1605 — the region check has the re-export
blind spot the reference scan closed; the call is at :1615). Absences are resolved by a
human writing the fingerprint, with the reason in the note. During migration the gate accepts
both cell forms per row (old form = integer after the first colon). The old form is retired —
parser branch deleted — in the commit after the last row leaves it.

## 4. THE ORACLE
On a scratch checkout, old gate and new gate run over the migrated registry; the per-row,
per-test verdict vectors must be IDENTICAL (reasons may differ — goal-abduction-plan and
decline-branch pass for the right reason for the first time). Then three mutations, each
asserted on both gates: (i) a deliberately rotted row (wrong ENCLOSING / ORDINAL beyond count;
old form: line set to 1) fails; (ii) a deliberately broken wire (the anchored call deleted in
the scratch copy) fails on BOTH `claim_site` and `referenced_from_production`; (iii) a pure
line shift (200 lines inserted above every cognitive_loop claim site) fails 24 rows on the
old gate and ZERO on the new. For the laws the oracle is the mutation set, not the 2026-08-21
verdicts: the five window-law reds and the tail-law red of today are PRE-NAMED as the verdicts
the new laws must NOT reproduce (the facts held; only positions moved).

## 5. FALSIFIERS (tests/gate/test_symbol_receipts.py, house style, shown failing first)
- **F1 · insertion is invisible**: 200 lines above every claim site AND 100 lines inside
  `record_result` before its first `credit` call → zero receipts red, zero laws red.
- **F2 · removal is not**: delete the anchored `credit` call → L1 red and click-economy/
  goal-spine rows red; delete the `_goal_abd` call → L3 red; delete any anchored call → its
  row red on both receipt tests.
- **F3 · order is real**: move `_goal_abd` above the first `route` call → L3 red; move the
  `_plan_gate` init into `record_result` → L4 red; a `_plan_gate` reference in a module-
  bottom helper → L4 green.
- **F4 · ordinal is honest**: a second `credit` call inserted BEFORE the anchored one → the
  row reds naming ordinal and count; inserted AFTER → green.
- **F5 · absences are named**: a registry with one unresolvable row → migrate reports it by
  name and writes nothing for it; the gate still reads the old form for that row.
- **F6 · the oracle of §4 passes**, including (iii)'s 24-vs-0.

## 6. THE RECEIPT TAX — PRE-COMMITTED WIN AND LOSS
Metric: per build commit touching `cognitive_loop.py`, the count of registry site cells
edited because the gate went red, read from the diff. Baseline this week: 24 / 1 / 23 on the
three named W-builds, ~140 in total, 0 of them a broken wire. **Win**: over the next five
builds that insert ≥20 lines above at least one loop claim site, gate-forced refreshes = 0,
and no test amendment is needed to place code inside `record_result`. **Loss** (→ §7): any
such build forces >2 fingerprint edits whose cause is not a §1.4 structural change, OR the
oracle's known-negative (§4 ii) ever passes on the new gate. Either is a reason to undo, not
to tune.

## 7. UNDO
One commit to revert (tests/gate, tools/, the registry, six law bodies); no production module
is touched by this build. `tools/wiring_receipts.py demote` rewrites every `@LINE` courtesy
back to `file:line` — the old form is carried inside the new cell for exactly this reason.
Reverting re-imposes the placement debt at today's headroom (50/15 chars at HEAD); say so in
the revert message rather than re-widening the windows silently.

## OPEN FOR REVIEW (not pinned)
Cell encoding (6 cells with `@LINE` vs a 7th column); ORDER clause of L3 kept or dropped with
its stated purpose; CALL fingerprints name the callee only (receiver not encoded); L6's comment
sub-block not anchored (function + uniqueness is the fact); old-form retirement timing.

## PROCTOR REVIEW (2026-08-21) — accepted with decisions
1 six cells, fingerprint carrying @LINE as courtesy (keeps the 6-field unpack that caught
the concatenation defect) — ACCEPTED. 2 L3's ORDER clause KEPT as a documented
settle-before-bank law. 3 callee-only fingerprints now, receiver-qualified later — ACCEPTED
with the tightening queued (a `.credit` on the wrong receiver is the false positive this
leaves open; named). 4 L6 as drafted. 5 old-form retirement on the commit after the last
row leaves it — ACCEPTED. 6 the four named absences: decline-branch and goal-abduction-plan
resolved by hand with the reason in the note (both pass today on SUBSTRING accidents — the
import-line and a `return out` — which is the proxy defect in miniature); router-core and
mint-core migrate after the dispatched repair lands. 7 keep the six test names, delegate
bodies to tests/gate/_ast_laws.py — ACCEPTED.
THE FINDING THAT MATTERS: the _plan_gate tail law is a tail SLICE — it forbids the
module-bottom convention that protects receipts. Two position-based disciplines in direct
conflict; the AST form dissolves the conflict. The repair builder was authorized to convert
the proxy laws to their AST forms (stronger, intent-preserving, names kept) rather than
contort the code. Build order: after the stage-4.5 structural repair commits.
RIDERS (Seat 4): L3's settle-before-bank ordering KEEPS ITS OWN JUSTIFICATION written as a
semantic law of the loop — not "protects L2's window" (which is going away). And the genus
gets its count: GUARDS PASSING ON AN ACCIDENT — docstring-mention refreshes (6), the
context-min row (+36 masked by a docstring), and now two substring receipts (decline-branch
on "match" in `return out`; goal-abduction-plan on an import line with the call 36 lines
below) — three instances, all position/substring proxies. Four of sixty rows assert
nothing today. That, not tidiness, is the migration's argument.

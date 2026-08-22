# BUILDER BRIEF — SYMBOL-ANCHORED RECEIPTS + AST LAWS (dispatch LAST: after every other queued build has landed and the tree is settled — the migration rewrites every registry row)

Reads first: record/prereg/PREREG_SYMBOL_RECEIPTS.md (ruled; the PROCTOR REVIEW decisions 1-7
and Seat 4's riders are binding), record/findings/PROPOSAL_SYMBOL_RECEIPTS.md, KNOBS A4-2,
tests/gate/test_wiring_registry.py (the gate and its parser — the 6-field unpack stays),
record/canon/WIRING_REGISTRY.md, the six law files (test_goal_abduction, test_level_conventions,
test_lp_drive, test_link3, test_plan_wire, test_goal_spine — the exemplar
`test_reward_wires_to_credit` is already in AST form; test_plan_wire's `_plan_gate` law was
converted to AST form on 2026-08-21 — keep it, migrate its siblings to the same helper),
record/canon/THE_LADDER.md.

Constraints: HOLD up — no commit, nothing under .runs/. Forbidden reads as standing. Never
print .env. No production module is touched by this build (prereg §7) — tests/gate, tools/,
the registry, the six law bodies only. The build is one revertable commit.

Build exactly the prereg: §1 the fingerprint cell `file:ENCLOSING/KIND:NAME#ORDINAL@LINE`
(six cells; @LINE a courtesy never asserted); the gate asserts parse / ENCLOSING exists /
ORDINAL+1 nodes — per LIVE row; SEVERED rows anchor to the organ's DEF with the wire-break
line as courtesy; §2 the laws L1-L6 in tests/gate/_ast_laws.py (inside / precedes /
nth-call), six test names kept, bodies delegated; L3's settle-before-bank ORDER clause kept
WITH ITS OWN semantic justification written in the law (Seat 4 rider — not "protects L2's
window"); §3 tools/wiring_receipts.py with `migrate` (census by KIND; NAMED-ABSENCE list;
ties and empties are absences, the tool never chooses), `refresh` (courtesy lines; never a
gate failure, never CI), `demote` (the undo); during migration the gate accepts both forms;
the old form retires in the commit AFTER the last row leaves it — state which rows still
carry it. The four named absences: decline-branch and goal-abduction-plan resolved BY HAND
with the reason in the note (both pass today on substring accidents — say so in the note);
router-core and mint-core: migrate normally if their repair has landed, else name them.

Gates (tests/gate/test_symbol_receipts.py, shown failing first): F1 insertion invisible
(200 lines above every claim site AND 100 inside record_result before its first credit → 0
red); F2 removal is not (delete the anchored call → its row and its law red); F3 order is
real; F4 ordinal is honest (before → red naming ordinal+count; after → green); F5 absences
named and nothing written for them; F6 THE ORACLE of §4 on a scratch checkout — per-row
per-test verdict vectors IDENTICAL between old and new gate over the migrated registry; the
three mutations, including (iii) 200-line shift: old gate reds 24 rows, new gate ZERO. The
six window-law reds and the tail-law red of 2026-08-21 are PRE-NAMED as verdicts the new
laws must NOT reproduce. Receiver-qualified fingerprints are QUEUED, not built (decision 3).

Receipt tax: record the baseline (24/1/23, ~140 total, 0 broken wires) in the registry
header and the pre-committed win/loss (§6) beside it. Discipline: ruff zero new; full
`pytest tests -q` once at the end, verbatim tail, every red yours or not; non-pinned
decisions numbered; terse structured report with the migration census and the absence list.

## THE LAWS THIS BUILD SATISFIES (figures/*.svg)
- FIGURE 10 — "install what can be violated"; "a convention nothing can check is a constant
  the seat authored, carrying the seat's authority". A position receipt (file:line ±30)
  was that constant: ~140 refreshes, zero broken wires — it checked nothing. The fingerprint
  is a convention that CAN be violated by a real structural change and by nothing else.
- FIGURE 2 — the anchor must not update because of what a frame thinks: the registry's
  claim is anchored to the symbol and its enclosing scope, not to a number that moves when
  anyone edits above it. The courtesy @LINE is explicitly NOT an anchor (never asserted).
- FIGURE 3 — a link with no instrument is a link nobody has looked at: the four rows that
  "assert nothing today" (substring accidents) are named absences, resolved by hand with the
  reason, never silently migrated.
State in your report which of these your tests assert and which are assumed.

## L7 — THE LAST-FUNCTION PIN (added 2026-08-21; in scope, found by the persistence build)
tests/gate/test_gate_stage1.py asserts the gate hook `_gate_step` is the module's LAST
function in cognitive_loop.py. That is a POSITIONAL law of exactly the genus this build
retires, and it is not one of L1-L6: the persistence builder had to place its own helper
ABOVE the hook because bottom-append was forbidden — a build shaped by a gate rather than
by design, the second such collision this week (the first was the `_plan_gate` tail slice).
THE FACT IT PROTECTS (read it from the test and state it in the law): the hook is a
MODULE-LEVEL def — not nested in a function, not a method on the class — so that inserting
it rots no receipt and the loop's body is untouched. "Last in the file" is a proxy for that
and forbids every later module-bottom helper.
AST FORM: the hook's `def` is a direct child of the Module body (not inside a ClassDef or
FunctionDef), and the loop's own class body contains no reference to it other than the ONE
call site the receipt names. Nothing about ordinal position among module-level defs.
FALSIFIERS: (i) moving the hook inside the class → red; (ii) appending a new module-level
helper after it → GREEN (today: red); (iii) deleting the hook → red on both the law and its
receipt. Keep the test's name; delegate the body to tests/gate/_ast_laws.py with L1-L6.

## COVERAGE, NOT JUST CORRECTNESS (added 2026-08-21 from the codebase inventory)
The registry gate today asserts that the rows PRESENT are true. It cannot see a module that
has NO ROW: engines/egocentric/relations.py is LIVE by import (depth 3, via the package
__init__), carries no row, and its three public functions are referenced nowhere in the
tree — inside the very package the gate was written to cover. Six instances of this
re-export blind spot exist (the inventory names them).
ADD A COVERAGE FALSIFIER: for every module statically reachable from the production
entrypoints, either a LIVE/SEVERED row exists, or the module is named in an explicit
NO-ROW allowlist with a reason (the allowlist is the convention that CAN be violated —
Figure 10). The falsifier goes red on a new reachable module with neither. Note in the row:
in-function imports make the live path 27 modules wider than a static scan shows, so the
reachability computation must include lazy imports (the inventory's method is the exemplar).

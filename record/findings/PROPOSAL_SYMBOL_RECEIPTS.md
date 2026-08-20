# PROPOSAL — SYMBOL-ANCHORED RECEIPTS (for Seat 3's queue, 2026-08-20)

**The arithmetic, now measured rather than argued:** three builds in one day (W1 narration,
W2a index, W2b scheduling), three mass-rots — 24, 1, 23 receipts — **~70 receipt refreshes,
every one a false positive**: no wire broke in any of them. The pattern is mechanical: any
build inserting lines above the cognitive loop's claim sites invalidates two dozen
`file:line` receipts at ±30 tolerance. **This tax will be paid again on stage 2 and on
every W3–W6 build.** The item has moved from *worth doing* → *demonstrated necessary* →
**cheaper to fix than to keep paying**.

**The fix:** receipts anchor to SYMBOLS (module:qualname + an AST-resolved call-site
fingerprint), not line coordinates. The wiring gate resolves the symbol's current location
at test time; drift becomes invisible because position was never the claim. Line numbers
stay as a human courtesy, auto-refreshed by the gate rather than by hand.

**Two W2b flags carried with it (Seat 4):**
1. `CHEAP_ROUTE_CONF_BAR = 0.5` (KNOBS G25, GUESSED) decides when the planner engages —
   **expect to re-derive it after the fourth window**, since stage 2 changes exactly the
   throughput that makes 0.5 look right today.
2. `on_fission` clears: second organ built-correct-and-called-never (binder's is the
   first). Gate-tested so it won't rot silently, but the genus now has two instances —
   worth one line in the fission work when it lands, so the callers arrive with the caller.

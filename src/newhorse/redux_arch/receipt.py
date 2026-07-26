"""
receipt.py -- A FIRING IS A RECEIPT, NOT A CLAIM (directive 5).

The chain claim is exactly one sentence: *a task FAILED here, the residual was THIS, φ was minted at THIS MDL
delta, φ was evaluated on a residual it was NOT minted for, φ FIRED there, and that cleared the break.* Anything
short of a rendered record of those six facts is a claim about the chain, not the chain.

So every break event writes a `ResidualEvent` from its real call site, whether or not anything fired. The record
of a NON-firing is as load-bearing as the record of a firing: it is what makes "no receipt ⇒ it did not fire"
a safe rule rather than a hope. And a receipt carries its own DEFEATERS -- how many exceptions, how many bits,
which KIND of echo -- so a later reader can overturn it without re-running anything (§5.1: record the classifier,
not the verdict).

ECHO KIND is ranked and printed, never elided:
    cross-game                    strongest -- φ minted on game A explained a residual on game B
    within-run-across-levels      weaker    -- same run, different level
    within-run-across-segments    weakest   -- same run, same level, different span of play
A within-game echo is a real transfer of a predicate across tasks it was not minted for, but it is a WEAKER
transfer claim than cross-game, because the two residuals share a palette, a control set and a mechanism. The
caveat goes IN the receipt so no downstream summary can quietly promote it.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

UNCLEARED_NOTE = ("NO -- and the reason is WIRING, not the drive layer: `ChainLedger.note_transfer_clear` has no "
                  "call site, because acting on a transferred phi is the OPERATOR layer -- the last link, and the "
                  "worst place for a first end-to-end run. The honest ceiling this beat is USED_NOCLEAR, and its "
                  "`indicts` field must NOT be read as a verdict on drive. test_tether_brick keeps this checkable.")

ECHO_KINDS = ("cross-game", "within-run-across-levels", "within-run-across-segments")
_ECHO_RANK = {k: i for i, k in enumerate(ECHO_KINDS)}
_ECHO_CAVEAT = {
    "cross-game": "φ explained a residual on a DIFFERENT GAME than it was minted on -- the strongest transfer claim.",
    "within-run-across-levels": ("WEAKER THAN CROSS-GAME: same run, different level -- shared palette, control set "
                                 "and mechanism, so the two residuals are not independent tasks."),
    "within-run-across-segments": ("WEAKEST: same run, same level, a different span of play -- the two residuals "
                                   "share everything except when they happened. Transfer across tasks is NOT "
                                   "demonstrated by this alone."),
}


def task_id(game_id: str, level: int, segment: int, stream: str = "tau") -> str:
    """The identity a residual is keyed by for ECHO purposes. Structured, so `echo_kind` can read the granularities
    back out of it instead of being told them by the caller (a caller-supplied kind is a verdict; a parsed one is a
    classifier).

    `stream` names WHICH residual this task's evidence came from -- `tau` for the transition residual R_τ (answers
    every step) or `rho` for the reward/progress residual R_ρ (speaks only on success). §4.3 treats these as two
    different streams of support, so a φ that echoed ACROSS them echoed on genuinely different evidence and must be
    readable as such from the receipt. The stream rides in the segment field, NOT the game field: tagging it onto
    the game id would make a same-game cross-stream echo render as 'cross-game', which would be a lie."""
    return "%s#L%d#s%d.%s" % (str(game_id or "?"), int(level), int(segment), str(stream))


def _parts(tid: str):
    g, _, rest = str(tid).partition("#")
    lvl, _, seg = rest.partition("#")
    return g, lvl, seg


def game_of(tid: str) -> str:
    """The GAME a task id belongs to. THE ONE PLACE that knows the id's shape. It was known in three places
    (`_parts` here, a hand-rolled split in swarm's carrier-reach pool, and now Γ's cross-game test); three copies of
    a format is how a later change to `task_id` silently turns a cross-game count into a within-game one while every
    test still passes."""
    return _parts(tid)[0]


def echo_kind(current: str, minted_on: List[str]) -> str:
    """The STRONGEST kind of echo represented by φ having been minted on `minted_on` and now firing on `current`.
    Strongest, not average: if any minting task was a different game, the transfer really did cross games."""
    g0, l0, _ = _parts(current)
    best = "within-run-across-segments"
    for t in minted_on or []:
        g, l, _s = _parts(t)
        if g != g0:
            return "cross-game"
        if l != l0 and _ECHO_RANK["within-run-across-levels"] < _ECHO_RANK[best]:
            best = "within-run-across-levels"
    return best


@dataclass
class ResidualEvent:
    """One break event, fully accounted. `stage` is back-filled from the ledger's own classification of the
    segment, so the receipt and the measured distribution can never tell different stories."""
    game: str = ""
    level: int = 0
    segment: int = 0
    reason: str = ""                      # death / run_end / advance -- how the task closed
    steps: int = 0                        # frames of play in the segment
    task_id: str = ""
    # WHICH EVIDENCE STREAM produced this receipt. §5.3: "a stream is a ground, and grounds are assessed PER
    # STREAM." R_tau is the transition residual (DIRECTIONAL games only, by identity); R_click is the click
    # residual. They are NEVER summed: `summary()` reports a per-stream breakdown precisely so that a second
    # stream coming online cannot be read as the first stream improving.
    stream: str = "R_tau"
    # the residual
    diff_ran: bool = False
    # WHY THE DIFF DID NOT RUN -- populated iff `diff_ran` is False, from `transition_residual`'s own report.
    # Until this existed, a DIED_PRE_DIFF segment produced NO RECEIPT AT ALL: the residual pass returned None
    # before it built one, so the single largest pile in the measured distribution was the one stage with zero
    # evidence behind it. That also made `summary()["break_events"]` -- defined as len(receipts) -- silently mean
    # "break events where the diff ran", which is why it printed identically equal to `diff_ran` on every sweep.
    # A number that cannot disagree with another number is not measuring it.
    no_diff_reason: Optional[str] = None   # no_focus_colour | no_learned_vecs | segment_too_short | no_testable_step
    scan_pairs: int = 0                    # frame pairs the residual scan actually walked
    scan_no_vec: int = 0                   # ...skipped because Γ has no displacement for the action taken
    scan_unlocatable: int = 0              # ...skipped because the focus colour was not on the board
    # R_click's own scan counters, kept in their OWN fields rather than reusing R_tau's. Reusing them would make
    # `no_diff_scan` a sum over two streams the moment the second one came online.
    scan_no_coord: int = 0                 # ...skipped because the action carried no coordinate
    scan_off_board: int = 0                # ...skipped because the clicked cell was off the board
    # when BOTH streams were silent, the second stream's classifier (the first's is `no_diff_reason`)
    click_no_diff_reason: Optional[str] = None
    n_exceptions: int = 0
    n_positive: int = 0
    baseline_bits: float = 0.0
    residual_nonempty: bool = False
    # reuse-BEFORE-mint (the transfer test, run on a FRESH residual)
    library_size_before: int = 0
    # THE CROSS-GAME Γ's OWN AUDIT COLUMN. `library_size_before` cannot answer the question the shared library was
    # built to answer: a Γ of four φ that THIS game minted is, for transfer purposes, an empty library. `foreign`
    # counts only promoted φ whose minting tasks contain NO task from this game -- i.e. the φ that would be a real
    # transfer if they fired here. The pre-registered undo for the shared Γ is written against this field, not
    # against `reuse_attempted`, because reuse_attempted goes positive the moment Γ is non-empty for ANY reason.
    library_foreign_before: int = 0
    reuse_attempted: bool = False
    reuse_attempted_foreign: bool = False  # this residual was offered a φ minted on a game that is NOT this game

    transferred: Optional[str] = None     # str(φ) that explained this residual without re-minting
    transfer_gain_bits: float = 0.0
    echo_kind: Optional[str] = None
    minted_on: List[str] = field(default_factory=list)
    # the mint
    minted: bool = False
    minted_phi: Optional[str] = None
    minted_bits: float = 0.0
    minted_support: int = 0
    # the MDL gate, exposed rather than inferred: how many candidates were CONSTRUCTED, how many were ELIGIBLE
    # (non-trivial on these before-state contexts), and what naming one therefore cost. MINT_UNFIRED is only
    # readable as a verdict if these three numbers are on the record next to it.
    n_constructed: int = 0
    n_eligible: int = 0
    selection_cost_bits: float = 0.0
    # the POOLED retry (persistent residual bank). Kept in SEPARATE fields from the fresh mint so the old
    # measurement stays comparable and a pooled mint can never be read as a fresh one.
    pool_size: int = 0                    # exceptions available from PAST segments of this game family
    pool_tasks: List[str] = field(default_factory=list)
    pool_attempted: bool = False
    minted_from_pool: bool = False
    pool_n_eligible: int = 0
    pool_selection_cost_bits: float = 0.0
    promoted: bool = False                # this mint pushed φ over the echo threshold into Γ
    echo_count: int = 0                   # distinct tasks φ has now been minted on
    key: Optional[str] = None
    # the close
    cleared: bool = False
    stage: Optional[str] = None

    @property
    def fired(self) -> bool:
        """A FIRING is a transfer: a promoted φ explained a residual it was not minted for. Not a mint, not a
        promotion, not an advance."""
        return bool(self.transferred)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["fired"] = self.fired
        return d


def render_one(ev: ResidualEvent) -> str:
    """Directive 5's six-field record for ONE firing, plus its caveat. Never called on a non-firing: a rendered
    'receipt' for an event that did not fire is exactly the thing that turns a claim into fake evidence.

    A MISREPORT FIXED HERE, FOUND BY READING THE FIRST SWEEP THAT ACTUALLY FIRED. Two DIFFERENT predicates pass
    through one break event -- the φ that TRANSFERRED (scored out of Γ, before any minting) and the φ that was
    freshly MINTED on the same residual afterwards -- and they are routinely not the same predicate. The old
    layout printed the minted φ, then said "for the task(s) named below", then printed `minted_on`, which is the
    provenance of the TRANSFERRED φ. On the real receipt that read as `INTENDED_FREE` having been minted on four
    sp80 tasks, when sp80 is where `INTENDED_COLOUR==9` came from and `INTENDED_FREE` had never touched that game.
    A receipt that misattributes provenance is worse than no receipt: it is the fake evidence directive 5 exists
    to forbid, produced by the very artifact meant to prevent it. So the two φ now live in separate blocks, each
    carrying its own provenance, and neither block's prose can reach across to the other's fields.

    The minting GAMES are printed alongside the tasks because the cross-game claim -- the strongest one the chain
    can make -- is otherwise only checkable by parsing task ids by eye."""
    kind = ev.echo_kind or "within-run-across-segments"
    games = sorted({game_of(t) for t in (ev.minted_on or [])})
    here = game_of(ev.task_id) if ev.task_id else str(ev.game)
    elsewhere = [g for g in games if g != here]
    if ev.minted_phi is None:
        mint_block = ["  ALSO MINTED HERE   (nothing was minted on this residual)"]
    elif ev.transferred is not None and str(ev.minted_phi) == str(ev.transferred):
        mint_block = ["  ALSO MINTED HERE   %s -- the SAME phi, re-minted on this residual (%.2f bits, support %d)"
                      % (ev.minted_phi, ev.minted_bits, ev.minted_support),
                      "                     A re-mint is not a second piece of evidence: it is this game agreeing"
                      " with itself."]
    else:
        mint_block = ["  ALSO MINTED HERE   %s (%.2f bits, support %d) -- a DIFFERENT phi from the one that fired"
                      % (ev.minted_phi, ev.minted_bits, ev.minted_support),
                      "                     Its provenance is THIS task (%s) and nothing above or below applies"
                      " to it." % ev.task_id]
    return "\n".join([
        "--- TETHER FIRING RECEIPT --------------------------------------------------",
        "  BASE FAILED HERE   game=%s level=%d segment=%d closed_by=%s after %d steps"
        % (ev.game, ev.level, ev.segment, ev.reason, ev.steps),
        "  RESIDUAL WAS       %s: %d testable steps, %d predicted-correctly, baseline %.2f bits"
        % (ev.stream or "R_tau", ev.n_exceptions, ev.n_positive, ev.baseline_bits),
        "  PHI THAT FIRED     %s" % ev.transferred,
        "    ...WAS MINTED ON tasks %s" % (", ".join(ev.minted_on) or "(unknown)"),
        "    ...I.E. ON GAMES %s%s" % (", ".join(games) or "(unknown)",
                                       ("  <-- INCLUDING %s, WHICH IS NOT THIS GAME" % ", ".join(elsewhere))
                                       if elsewhere else "  (all of them THIS game -- a within-game echo)"),
        "    ...AND EXPLAINED %s here, compressing it by %.2f bits without re-minting"
        % (ev.task_id, ev.transfer_gain_bits),
        "    ...SCORED BEFORE any mint ran on this residual, so no fresh mint answered its own question",
    ] + mint_block + [
        "  THAT CLEARED       %s" % ("yes -- the transferred operator closed the break" if ev.cleared
                                     else UNCLEARED_NOTE),
        "  ECHO KIND          %s" % kind,
        "  CAVEAT             %s" % _ECHO_CAVEAT[kind],
        "  SEGMENT SCORED     %s" % (ev.stage or "(unscored: advance or empty segment)"),
        "----------------------------------------------------------------------------",
    ])


def firings(events: List[ResidualEvent]) -> List[ResidualEvent]:
    return [e for e in (events or []) if e.fired]


def render(events: List[ResidualEvent]) -> str:
    """The whole record: every firing rendered in full, then the accounting that makes the ABSENCE of a firing
    a measured result rather than a silence."""
    evs = list(events or [])
    fs = firings(evs)
    out = [render_one(e) for e in fs]
    if not fs:
        out.append("NO FIRING. Not a claim about the architecture -- a count:")
    out.append(summary_line(evs))
    return "\n".join(out)


def summary_line(events: List[ResidualEvent]) -> str:
    """Counts over the events GIVEN. Callers must pass EVERY break event, never a firings-only subset: fed the
    subset it prints "break events=0" on a run that had many, which renders a silence as a measured zero."""
    evs = list(events or [])
    ran = sum(1 for e in evs if e.diff_ran)
    ne = sum(1 for e in evs if e.residual_nonempty)
    at = sum(1 for e in evs if e.reuse_attempted)
    mi = sum(1 for e in evs if e.minted)
    pr = sum(1 for e in evs if e.promoted)
    fi = len(firings(evs))
    cl = sum(1 for e in evs if e.cleared)
    return ("  break events=%d | residual computed=%d | non-empty=%d | minted=%d | promoted into Γ=%d | "
            "offered to Γ=%d | FIRED=%d | cleared=%d" % (len(evs), ran, ne, mi, pr, at, fi, cl))


def summary(events: List[ResidualEvent]) -> Dict[str, Any]:
    """Machine-readable form of the same counts, for pooling across a sweep. Kinds are counted separately so a
    pooled report can never add a within-run echo to a cross-game one and call the sum 'transfers'."""
    evs = list(events or [])
    kinds: Dict[str, int] = {}
    for e in firings(evs):
        k = e.echo_kind or "within-run-across-segments"
        kinds[k] = kinds.get(k, 0) + 1
    # WHICH φ was minted, and on WHICH tasks -- the carrier-verification measure for the NEXT carrier, kept as an
    # instrument reading rather than a guess. A cross-game Γ can only ever fire if two DIFFERENT games mint the SAME
    # key; pooled across a sweep this says whether that carrier has a live instance BEFORE anyone wires it (the
    # 43rd-audit caution). Task ids carry the game id, so the pooled sets stay attributable.
    minted_keys: Dict[str, List[str]] = {}
    for e in evs:
        if e.minted and e.key:
            ts = minted_keys.setdefault(e.key, [])
            if e.task_id not in ts:
                ts.append(e.task_id)
    # WHY THE DIFF DID NOT RUN, pooled. This histogram is the whole point of emitting a receipt on the dead path:
    # DIED_PRE_DIFF is the biggest number on the board and it was the only stage with no evidence under it. The
    # sub-counters are summed only over the segments that actually walked frames (`no_testable_step`), because a
    # segment that died at `no_focus_colour` never scanned anything and averaging its zeros in would flatten the
    # very distinction the reasons exist to draw.
    reasons: Dict[str, int] = {}
    for e in evs:
        if not e.diff_ran:
            r = e.no_diff_reason or "unrecorded"
            reasons[r] = reasons.get(r, 0) + 1
    scanned = [e for e in evs if not e.diff_ran and e.no_diff_reason == "no_testable_step"]
    # THE SECOND STREAM'S OWN CLASSIFIER, on the segments where BOTH streams were silent. Without this column a
    # DIED_PRE_DIFF that R_κ also could not address is indistinguishable from one it was never offered.
    click_reasons: Dict[str, int] = {}
    for e in evs:
        if not e.diff_ran and e.click_no_diff_reason:
            click_reasons[e.click_no_diff_reason] = click_reasons.get(e.click_no_diff_reason, 0) + 1
    return dict(minted_keys={k: sorted(v) for k, v in sorted(minted_keys.items())},
                break_events=len(evs),
                # §5.3: A STREAM IS A GROUND AND GROUNDS ARE ASSESSED PER STREAM. This breakdown exists so that a
                # second stream arriving can never be read as the first one getting better -- the top-level totals
                # below are a convenience, and this is the number that carries the claim.
                by_stream=_by_stream(evs),
                no_diff_reasons=dict(sorted(reasons.items())),
                click_no_diff_reasons=dict(sorted(click_reasons.items())),
                click_scan=dict(pairs=sum(e.scan_no_coord + e.scan_off_board for e in evs if not e.diff_ran),
                                no_coord=sum(e.scan_no_coord for e in evs if not e.diff_ran),
                                off_board=sum(e.scan_off_board for e in evs if not e.diff_ran)),
                no_diff_scan=dict(segments=len(scanned),
                                  pairs=sum(e.scan_pairs for e in scanned),
                                  no_vec=sum(e.scan_no_vec for e in scanned),
                                  unlocatable=sum(e.scan_unlocatable for e in scanned),
                                  steps_median=_median([e.steps for e in scanned])),
                diff_ran=sum(1 for e in evs if e.diff_ran),
                residual_nonempty=sum(1 for e in evs if e.residual_nonempty),
                minted=sum(1 for e in evs if e.minted),
                promoted=sum(1 for e in evs if e.promoted),
                reuse_attempted=sum(1 for e in evs if e.reuse_attempted),
                # counted SEPARATELY from `reuse_attempted`, never folded into it: an offer of a φ this same game
                # minted is not a transfer opportunity, and a single "attempts" total would let a shared Γ that
                # never crossed a game boundary read exactly like one that did.
                reuse_attempted_foreign=sum(1 for e in evs if e.reuse_attempted_foreign),
                fired=len(firings(evs)),
                cleared=sum(1 for e in evs if e.cleared),
                firing_kinds=kinds,
                # the mint gate, pooled: what the MDL code was actually charged, and what the persistent bank
                # added. `minted_from_pool` is reported SEPARATELY from `minted` -- a pooled mint is a weaker
                # claim (it used evidence from segments other than the one it is recorded on) and adding the two
                # into one 'minted' number would hide exactly the thing that needs checking.
                mint_gate=dict(
                    eligible_median=_median([e.n_eligible for e in evs if e.residual_nonempty]),
                    constructed_median=_median([e.n_constructed for e in evs if e.residual_nonempty]),
                    selection_cost_median=_median([e.selection_cost_bits for e in evs if e.residual_nonempty]),
                    baseline_median=_median([e.baseline_bits for e in evs if e.residual_nonempty]),
                    pool_attempted=sum(1 for e in evs if e.pool_attempted),
                    pool_size_median=_median([e.pool_size for e in evs if e.pool_attempted]),
                    minted_from_pool=sum(1 for e in evs if e.minted_from_pool),
                ))


def _by_stream(evs: List[ResidualEvent]) -> Dict[str, Any]:
    """Per-stream counts AND per-stream stage distribution (§5.3). A receipt whose diff did not run is attributed to
    the stream that was tried LAST and still failed, which is how it is filed; a receipt whose diff ran is attributed
    to the stream that produced the exceptions. Nothing here adds two streams together."""
    out: Dict[str, Any] = {}
    names = sorted({(e.stream or "R_tau") for e in evs})
    for s in names:
        sub = [e for e in evs if (e.stream or "R_tau") == s]
        stages: Dict[str, int] = {}
        for e in sub:
            if e.stage:
                stages[e.stage] = stages.get(e.stage, 0) + 1
        out[s] = dict(break_events=len(sub),
                      diff_ran=sum(1 for e in sub if e.diff_ran),
                      residual_nonempty=sum(1 for e in sub if e.residual_nonempty),
                      minted=sum(1 for e in sub if e.minted),
                      promoted=sum(1 for e in sub if e.promoted),
                      fired=len(firings(sub)),
                      cleared=sum(1 for e in sub if e.cleared),
                      stages=dict(sorted(stages.items())))
    return out


def _median(xs) -> float:
    """Median, not mean: one 300-exception pool must not be able to describe a run of five-item residuals."""
    v = sorted(float(x) for x in xs)
    if not v:
        return 0.0
    m = len(v) // 2
    return v[m] if len(v) % 2 else 0.5 * (v[m - 1] + v[m])

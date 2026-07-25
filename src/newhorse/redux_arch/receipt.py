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
    # the residual
    diff_ran: bool = False
    n_exceptions: int = 0
    n_positive: int = 0
    baseline_bits: float = 0.0
    residual_nonempty: bool = False
    # reuse-BEFORE-mint (the transfer test, run on a FRESH residual)
    library_size_before: int = 0
    reuse_attempted: bool = False
    transferred: Optional[str] = None     # str(φ) that explained this residual without re-minting
    transfer_gain_bits: float = 0.0
    echo_kind: Optional[str] = None
    minted_on: List[str] = field(default_factory=list)
    # the mint
    minted: bool = False
    minted_phi: Optional[str] = None
    minted_bits: float = 0.0
    minted_support: int = 0
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
    'receipt' for an event that did not fire is exactly the thing that turns a claim into fake evidence."""
    kind = ev.echo_kind or "within-run-across-segments"
    return "\n".join([
        "--- TETHER FIRING RECEIPT --------------------------------------------------",
        "  BASE FAILED HERE   game=%s level=%d segment=%d closed_by=%s after %d steps"
        % (ev.game, ev.level, ev.segment, ev.reason, ev.steps),
        "  RESIDUAL WAS       R_tau: %d testable steps, %d predicted-correctly, baseline %.2f bits"
        % (ev.n_exceptions, ev.n_positive, ev.baseline_bits),
        "  PHI RE-MINTED HERE %s   (%.2f bits saved, support %d) -- the ORIGINAL mint's delta is in the receipt"
        % (ev.minted_phi or "(nothing re-minted on this residual)", ev.minted_bits, ev.minted_support),
        "                     for the task(s) named below, which is where phi was actually created.",
        "  EVALUATED BEFORE   phi was minted on %s and scored against THIS residual before any new mint"
        % (", ".join(ev.minted_on) or "(unknown)"),
        "  PHI FIRED HERE     %s explained task %s, compressing it by %.2f bits without re-minting"
        % (ev.transferred, ev.task_id, ev.transfer_gain_bits),
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
    return dict(minted_keys={k: sorted(v) for k, v in sorted(minted_keys.items())},
                break_events=len(evs),
                diff_ran=sum(1 for e in evs if e.diff_ran),
                residual_nonempty=sum(1 for e in evs if e.residual_nonempty),
                minted=sum(1 for e in evs if e.minted),
                promoted=sum(1 for e in evs if e.promoted),
                reuse_attempted=sum(1 for e in evs if e.reuse_attempted),
                fired=len(firings(evs)),
                cleared=sum(1 for e in evs if e.cleared),
                firing_kinds=kinds)

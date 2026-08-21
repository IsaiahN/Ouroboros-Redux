"""gate.py -- REASONING GATE STAGE 1: SHADOW MODE (PREREG_GATE_STAGE1_SHADOW.md).

THE GATE IS AN EXECUTOR AND A LEDGER, NEVER A JUDGE (PROPOSAL_REASONING_GATE
par.2). It holds no authored rule set: every clause of every utterance pays
in exactly one currency --
  * LEDGER      looked up in the agent's own earned records (Gamma, the
                action book, the frontier book, composite records, this
                stream's own earlier utterances);
  * EXECUTABLE  run through the world's own mechanics (effects.apply_effect,
                delta composition, frame lookup, the bank's residual
                recompute BY IDENTITY);
  * COMPLETENESS  the CHANGED set checked as a SET against compute_d --
                never economised: a cost overrun is a finding, not a trim.
PARSE precedes all three (grammar.compose raises -> `ill-typed` at the head).
Every refusal names the failing head and a FIXED token, never prose.

THIS STAGE BLOCKS NOTHING. Every non-replay action is evaluated and logged
on the personal `gate` topic; no verdict reaches the action path -- the one
hook is a void call beside the spine's act() (cognitive_loop._gate_step,
called from _narr_bet) and `refuse` is zero by construction: no code path in
this module returns a blocking verdict. `would_refuse` is the shadow count.

THE BUILDER / GATE SPLIT (load-bearing): the UTTERANCE-BUILDER (build_*)
translates the loop's existing decision state into utterances and reads ONLY
the agent's own state -- its perceived opener frame and the previous frame
it tracked, the plan's atoms, the frontier book, action and rung, the bank's
settlement, its own prior utterance. The GATE (check_*) reads the world
(apply_effect, compute_d, frames) and the ledger. Neither reads the other's
sources, so "unreported change" on live play measures perceptual coverage,
not the builder's access to compute_d. The builder's BET-side functions are
GUARDED by the import-time AST wall below (no_posthoc, salvaged): a builder
that reads an after-state name fails import.

THE ROLLOUT LADDER (primitive_ledger's, salvaged): env REASONING_GATE in
off / observe / active, DEFAULT observe (an inert default would measure
nothing). `active` is NOT BUILT in stage 1 -- it resolves to observe with one
DOWNGRADE record, so stage 2 is a flip, not a rename. THE STAGE-2 DEADLINE IS
A MECHANISM (Seat 3's ruling): ENFORCEMENT_ENABLED + PERCEIVE_HOME below, and
deadline_violation() -- the gate test FAILS if enforcement is enabled while
the opener-side PERCEIVE still lives on this topic rather than in the spine.

SALVAGE (each seam new code with its own constructed case): grammar primes
+ compose (new-horse); no_posthoc's import-time wall; primitive_ledger's
ladder with would_refuse separate from refuse; objective_validator's
Discrepancy(measure, active); question_tropism's discrimination() scorer;
action_book reads; composer.is_citable / citation_allowed (this tree).

Containment: the gate never raises into the host loop (step() swallows into
`errors`); the wall raises at IMPORT, where a bound belongs. Records are
JSON-plain; numpy stays inside the checks.
"""
from __future__ import annotations

import ast
import math
import os
import time
from collections import namedtuple
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

from engines.egocentric import action_book as _book
from engines.egocentric import grammar as G
from engines.egocentric import narration as _na
from engines.egocentric.bank import PredictorBank as _Bank
from engines.egocentric.composer import ROLE_BET, ROLE_GROUND, citation_allowed
from engines.egocentric.discrepancy import compute_d
from engines.egocentric.effects import (
    DONT_CARE,
    ORIGIN_IMPORTED,
    ORIGIN_LOCAL,
    Gamma,
    apply_effect,
    origin_of,
)
from engines.egocentric.router import ResidualRouter as _Router

__all__ = ["TOPIC", "MODE_ENV", "MODE_OFF", "MODE_OBSERVE", "MODE_ACTIVE", "MODES",
           "DEFAULT_MODE", "ENFORCEMENT_ENABLED", "PERCEIVE_HOME", "SPINE_TOPIC",
           "DEADLINE_REASON", "deadline_violation", "resolve_mode", "TOKENS",
           "CLASSES", "RESIDUAL", "Discrepancy", "want_discrepancy",
           "discrimination", "probe_score", "stratum_of", "standing_change",
           "GUARDED", "AFTER_NAMES", "PostHocRead", "check_no_posthoc", "audit",
           "announce", "build_perceive", "build_bet", "build_act", "classify",
           "check_perceive", "check_bet", "check_act", "ReasoningGate",
           "coverage_report", "record_of", "held_for_action"]

TOPIC = "gate"                         # the personal stream: one record per utterance
SPINE_TOPIC = _na.TOPIC                # where the agent's spine narrates ("narration")

# -- the ladder (primitive_ledger's off / observe / active, salvaged) --------
MODE_ENV = "REASONING_GATE"
MODE_OFF, MODE_OBSERVE, MODE_ACTIVE = "off", "observe", "active"
MODES = (MODE_OFF, MODE_OBSERVE, MODE_ACTIVE)
DEFAULT_MODE = MODE_OBSERVE            # prereg par.4: an inert default measures nothing

# -- THE STAGE-2 DEADLINE MECHANISM (SEAT 3 RULING, 2026-08-21) -------------
# Stage 2 flips ENFORCEMENT_ENABLED. The opener-side PERCEIVE lives on THIS
# topic in stage 1 (PERCEIVE_HOME == TOPIC); stage 2 must relocate it into
# the agent's spine (PERCEIVE_HOME == SPINE_TOPIC) BEFORE enforcement. The
# gate test asserts deadline_violation(ENFORCEMENT_ENABLED, PERCEIVE_HOME) is
# None on the shipped tree -- flipping the flag first turns it red. A
# convention that decides outcomes is not a convention.
ENFORCEMENT_ENABLED = False
PERCEIVE_HOME = TOPIC
DEADLINE_REASON = "perceive-not-relocated"


def deadline_violation(enforcement_enabled: bool, perceive_home: str) -> Optional[str]:
    """The mechanism, pure: the token iff enforcement is on while the
    opener-side PERCEIVE still lives on the gate topic; None otherwise."""
    if bool(enforcement_enabled) and str(perceive_home) == TOPIC:
        return DEADLINE_REASON
    return None


def resolve_mode(value: Optional[str] = None) -> Tuple[str, bool]:
    """(mode, downgraded). Resolved ONCE per gate from REASONING_GATE (or an
    explicit value). Unrecognised -> the default (observe). `active` is not
    built in stage 1: it resolves to observe with downgraded=True, so the
    value exists and stage 2 is a flip. Only an enforcement-enabled tree
    keeps `active` -- and the deadline test guards that flip."""
    v = (value if value is not None else os.environ.get(MODE_ENV, "")).strip().lower()
    if v not in MODES:
        v = DEFAULT_MODE
    if v == MODE_ACTIVE and not ENFORCEMENT_ENABLED:
        return MODE_OBSERVE, True
    return v, False


# -- refusal tokens (fixed; never prose) and non-verdicts ---------------------
ILL_TYPED = "ill-typed"                # parse
MISMATCH = "mismatch"                  # executable
NOT_HELD = "not-held"                  # ledger
NOT_EARLIER = "not-earlier"
WRONG_STEP = "wrong-step"
WRONG_KIND = "wrong-kind"              # right type, wrong record kind (ledger)
NOT_IN_PERCEIVE = "not-in-perceive"
UNSETTLED_COMPOSITE = "unsettled-composite"
ALREADY_SETTLED = "already-settled"
PRICE_MISMATCH = "price-mismatch"
PRICE_INVENTED = "price-invented"
FALSE_IGNORANCE = "false-ignorance"
STANDING_MISMATCH = "standing-mismatch"
UNREPORTED_CHANGE = "unreported-change"  # completeness
FALSE_CHANGE = "false-change"
MISALIGNED = "misaligned"              # the Discrepancy x compute_d seam
VACUOUS = "vacuous"
TOKENS = (ILL_TYPED, MISMATCH, NOT_HELD, NOT_EARLIER, WRONG_STEP, WRONG_KIND,
          NOT_IN_PERCEIVE, UNSETTLED_COMPOSITE, ALREADY_SETTLED, PRICE_MISMATCH,
          PRICE_INVENTED, FALSE_IGNORANCE, STANDING_MISMATCH, UNREPORTED_CHANGE,
          FALSE_CHANGE, MISALIGNED, VACUOUS)
# named NON-verdicts (counted apart; never a pass)
BOOK_ABSENT = "book-absent"
NO_PREVIOUS = "no-previous"
NO_PREDICTION = "no-prediction"
NO_AVATAR = "no-avatar"
UNCOMPILABLE = "uncompilable"

PASS, REFUSE, UNVERDICTED = "pass", "refuse", "unverdicted"

# utterance classes (the three numbers + the decomposition of the unlabeled)
DERIVATION, NEGATIVE, PROBE, UNBUILDABLE = ("derivation", "negative-derivation",
                                            "probe", "unbuildable")
CLASSES = (DERIVATION, NEGATIVE, PROBE, UNBUILDABLE)

# standings (STAND's ATTR values) and the record kinds
STRENGTHENED, WEAKENED, DIED = "strengthened", "weakened", "died"
K_PERCEIVE, K_BET, K_ACT, K_ATOM, K_COMPOSITE, K_FRONTIER = (
    "perceive", "bet", "act", "atom", "composite", "frontier")
SLOT = "WORKSPACE"                      # the one slot the builder renders this stage
# the two BROKEN bins, read from narration's bin table (a weakened standing);
# BROKEN_REBINDING stays the SEVERED bin it is -- this names no new reader of it
_BROKEN_BINS = tuple(b for b in _na.BINS if str(b).startswith("BROKEN_"))
SELF = "self"
WALL_AWARE_RUNG = "wall_aware_navigation"  # the proposal's negative-derivation class

# THE RESIDUAL FUNCTION ROUTE BINS ON and the threshold it bins at, both
# named BY IDENTITY (as stage 4 named g7): no constant of this module's own.
RESIDUAL = _Bank._grid_residual
SETTLE_EPS = _Router().eps
# the atoms stream, under a name the consumer scanner cannot confuse with TOPIC
ATOMS_TOPIC = Gamma.TOPIC

# -- the salvaged Discrepancy (objective_validator: measure(g)==0 iff holds; active = cells) --
Discrepancy = namedtuple("Discrepancy", ["measure", "active"])


# ── THE WALL (no_posthoc, salvaged): bet-side builders never read the after-state ─────────────

# the BET-side builders of THIS module (a predicate is a question asked BEFORE you act)
GUARDED: List[Tuple[str, str]] = [
    ("gate.py", "build_bet"),
    ("gate.py", "_bet_cells"),          # the bet's predicate: the cells it predicts
    ("gate.py", "_build_want"),
    ("gate.py", "_build_ground"),
    ("gate.py", "_build_derive"),
    ("gate.py", "_build_need"),
]
# no_posthoc's names + the loop's outcome names (the seam the prereg pins)
AFTER_NAMES: Set[str] = {"g_after", "after", "post", "b_objs", "nxt", "observed",
                         "post_array", "_narr_settle"}


class PostHocRead(Exception):
    """A bet that reads the outcome is a tautology with a name on it."""


def _reads_after(fn_node: ast.AST, after_names: Set[str]) -> Set[str]:
    bad: Set[str] = set()
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in after_names:
            bad.add(n.id)
        if isinstance(n, ast.arg) and n.arg in after_names:
            bad.add(n.arg)
    return bad


def check_no_posthoc(root: Optional[str] = None,
                     guarded: Optional[List[Tuple[str, str]]] = None,
                     after_names: Optional[Set[str]] = None,
                     source: Optional[str] = None) -> bool:
    """Raise PostHocRead if any guarded builder reads an after-state name.
    Called at import over this module's own source; `source` lets a
    constructed variant be walled in a test (the seam's own case)."""
    guarded = GUARDED if guarded is None else guarded
    after_names = AFTER_NAMES if after_names is None else after_names
    root = root or os.path.dirname(os.path.abspath(__file__))
    viol: List[str] = []
    for fname, fnname in guarded:
        if source is None:
            path = os.path.join(root, fname)
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
        else:
            src = source
        tree = ast.parse(src)
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef) and n.name == fnname:
                bad = _reads_after(n, after_names)
                if bad:
                    viol.append("%s::%s reads the after-state via %s"
                                % (fname, fnname, sorted(bad)))
    if viol:
        raise PostHocRead(
            "POST-HOC BET -- a bet-side builder that reads the outcome states a "
            "tautology the world can never refute:\n  " + "\n  ".join(viol))
    return True


def audit() -> Dict[str, Any]:
    """What the wall covers, and what it deliberately does not."""
    return {"guarded": ["%s::%s" % g for g in GUARDED],
            "not_guarded": [
                "_build_settle -- reads the OPENER (last step's outcome under its opener "
                "name): a settle is a label, it must read what the world answered",
                "_build_see_changed -- the agent's perceived opener and tracked previous "
                "frame: perception, not prediction",
                "check_* -- the GATE reads the world; the wall guards the builder's bet side",
            ],
            "after_names": sorted(AFTER_NAMES),
            "rule": "a bet is asked BEFORE the action; a label is what the world "
                    "answered; nothing may be both"}


def announce(emit: Callable[[str], Any]) -> None:
    """A bound that only speaks when violated is a bound nobody knows is
    there: state it once, in the stream, plainly."""
    try:
        emit("BOUND  no bet-side builder may read the after-state := ENFORCED at import "
             "over %d builders [%s]" % (len(GUARDED), audit()["rule"]))
    except Exception:
        pass


# ── salvaged scorers: Discrepancy x compute_d, question_tropism's discrimination ─────────────

def _want_cells_of(obj: Any) -> Optional[List[Tuple[int, int, int]]]:
    """The cells a WANT names: ALL/SOME/ONE/NONE(BECOME(OBJECT, ATTR cells))."""
    if not isinstance(obj, G.Term) or obj.type is not G.T.OBJ or len(obj.args) != 1:
        return None
    rel = obj.args[0]
    if not isinstance(rel, G.Term) or rel.head != "BECOME":
        return None
    attr = rel.args[1]
    if not isinstance(attr, G.Leaf):
        return None
    try:
        return [(int(r), int(c), int(v)) for r, c, v in attr.value]
    except Exception:
        return None


def want_discrepancy(obj: Any) -> Optional[Discrepancy]:
    """WANT compiles to Discrepancy(measure = compute_d["differing"] on the
    cited cells, active = those cells). THE SEAM: compute_d returns -1 on a
    shape mismatch (a non-answer) while a Discrepancy's measure is
    non-negative with 0 = holds -- measure() passes the -1 THROUGH as the
    non-answer (never read as satisfied or as a magnitude); the gate refuses
    `misaligned` on it. None when the OBJ is not compilable."""
    cells = _want_cells_of(obj)
    if cells is None:
        return None

    def _pair(g: Any) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        a = np.asarray(g)
        if a.ndim != 2:
            return None
        h, w = a.shape
        if any(not (0 <= r < h and 0 <= c < w) for r, c, _v in cells):
            return None
        ws = np.asarray([a[r, c] for r, c, _v in cells])
        ref = np.asarray([v for _r, _c, v in cells])
        return ws, ref

    def measure(g: Any) -> float:
        p = _pair(g)
        if p is None:
            return -1.0
        return float(compute_d(p[0], p[1])["differing"])

    def active(g: Any) -> List[Tuple[int, int]]:
        p = _pair(g)
        if p is None:
            return []
        return [(r, c) for (r, c, _v), w, t in zip(cells, p[0], p[1], strict=True) if w != t]

    return Discrepancy(measure, active)


def _satisfied(v: Any) -> Optional[bool]:
    if v is None:
        return None
    try:
        holds, total = v
        return None if not total else holds == total
    except Exception:
        return None


def discrimination(seq: List[Dict[str, Any]], win_mask: List[bool]) -> Dict[str, float]:
    """question_tropism's scorer, salvaged verbatim (the question generator is
    not): normalised mutual information between `satisfied` and `win` per
    name over the ring -- 1.0 = satisfied EXACTLY at win frames."""
    names = set().union(*[set(s.keys()) for s in seq]) if seq else set()
    out: Dict[str, float] = {}
    n = len(seq)
    if n == 0:
        return out
    for name in sorted(names):
        a = b = c = d = 0
        defined = 0
        for i, s in enumerate(seq):
            sat = _satisfied(s.get(name))
            if sat is None:
                continue
            defined += 1
            win = bool(win_mask[i])
            if sat and win:
                a += 1
            elif sat and not win:
                b += 1
            elif (not sat) and win:
                c += 1
            else:
                d += 1
        if defined < 2:
            out[name] = 0.0
            continue
        tot = a + b + c + d
        rows = [(a + b), (c + d)]
        cols = [(a + c), (b + d)]
        mi = 0.0
        for cnt, r, cc in ((a, 0, 0), (b, 0, 1), (c, 1, 0), (d, 1, 1)):
            if cnt == 0:
                continue
            pxy = cnt / tot
            px = rows[r] / tot
            py = cols[cc] / tot
            if px > 0 and py > 0:
                mi += pxy * math.log2(pxy / (px * py))

        def _h(ps: List[float]) -> float:
            return -sum(p * math.log2(p) for p in ps if p > 0)

        hnorm = min(_h([rows[0] / tot, rows[1] / tot]), _h([cols[0] / tot, cols[1] / tot]))
        out[name] = max(0.0, (mi / hnorm) if hnorm > 1e-9 else 0.0)
    return out


def probe_score(entry: Optional[Dict[str, Any]]) -> Optional[float]:
    """The probe's recorded VALUE (shadow-only; gates nothing; rank never
    confers validity): discrimination() over the book's recorded effect
    distribution for the action -- the 2x2 is (satisfied = the DOMINANT
    recorded effect kind fired) x (win = the frame changed), from the
    atoms' ttype counts and the traces' change counts. None when either
    side is the explicit null (absence is absence)."""
    try:
        atoms = (entry or {}).get("atoms")
        traces = (entry or {}).get("traces")
        if not atoms or not traces:
            return None
        ttypes = atoms.get("ttypes") or {}
        n = int(traces.get("n") or 0)
        changed = int(traces.get("frame_changed_n") or 0)
        if n <= 0 or not ttypes:
            return None
        dominant = max(int(v) for v in ttypes.values())
        dominant = min(dominant, changed)
        seq: List[Dict[str, Any]] = []
        win: List[bool] = []
        seq += [{"N": (1, 1)}] * dominant + [{"N": (0, 1)}] * (changed - dominant)
        win += [True] * changed
        seq += [{"N": (0, 1)}] * (n - changed)
        win += [False] * (n - changed)
        return discrimination(seq, win).get("N")
    except Exception:
        return None


def stratum_of(entry: Optional[Dict[str, Any]]) -> Optional[int]:
    """The action's book evidence stratum floor(log2(n+1)), n = atoms + traces
    observations; None when no book is loaded (absence is not stratum 0)."""
    if entry is None:
        return None
    n = 0
    for side in ("atoms", "traces"):
        part = entry.get(side)
        if isinstance(part, dict):
            n += int(part.get("n") or 0)
    return int(math.floor(math.log2(n + 1)))


def standing_change(settled_atom: Any, atom_id: str) -> Optional[str]:
    """The fabric's standing change for `atom_id` this step, from the bank's
    last settlement (atom key, ROUTE bin): TRANSFERRED strengthens, a BROKEN
    bin weakens, anything else is no change (None). `died` has no ledger
    source this stage -- never produced, and refused when claimed."""
    try:
        key, bn = settled_atom
    except Exception:
        return None
    if key is None or str(key) != str(atom_id):
        return None
    if bn == _na.TRANSFERRED:
        return STRENGTHENED
    if bn in _BROKEN_BINS:
        return WEAKENED
    return None


# ── ledger reads shared by builder (the agent's own fabric) and gate ──────────────────────────

def record_of(gamma: Any, aid: str) -> Optional[Dict[str, Any]]:
    """The atom's ENVELOPE record (id, origin, atom) -- Gamma.get returns the
    atom dict alone, and the memory-range tag needs the origin."""
    try:
        recs = gamma.fabric.query("collective", ATOMS_TOPIC,
                                  where=lambda r: r.get("id") == aid)
    except Exception:
        return None
    return recs[-1] if recs else None


def held_for_action(gamma: Any, game: str, action: int) -> List[Dict[str, Any]]:
    """Every EFFECT atom this agent's fabric holds for (game, action)."""
    try:
        g, a = str(game), int(action)
        recs = gamma.fabric.query(
            "collective", ATOMS_TOPIC,
            where=lambda r: (str(r.get("game")) == g
                             and (r.get("atom") or {}).get("kind") == "EFFECT"
                             and int((r.get("atom") or {}).get("action", -1)) == a))
    except Exception:
        return []
    return [r["atom"] for r in recs if isinstance(r.get("atom"), dict)]


def _tag_of(rec: Optional[Dict[str, Any]]) -> Optional[str]:
    """The memory-range tag an envelope resolves to, read THROUGH the marker's
    one total reader (effects.origin_of, never the raw key): an imported atom
    is [COL]; a locally minted one is this agent's own history [OWN] (EP vs
    OWN is not readable from the record; OWN is the conservative tag); the
    pre-marker vintage (ORIGIN_UNKNOWN -- not local, and possibly a legacy
    import) claims NO tag at all, because absence is not a range."""
    org = origin_of(rec)
    if org == ORIGIN_IMPORTED:
        return _na.COL
    if org == ORIGIN_LOCAL:
        return _na.OWN
    return None


def _cells(a: np.ndarray) -> Set[Tuple[int, int]]:
    return {(int(r), int(c)) for r, c in np.argwhere(a)}


def _anchor_of(ctx: np.ndarray, frame: np.ndarray) -> Optional[Tuple[int, int]]:
    """First exact context match in row-major order (the loop's own site scan)."""
    ph, pw = ctx.shape
    h, w = frame.shape[:2]
    for r in range(h - ph + 1):
        for c in range(w - pw + 1):
            if (frame[r:r + ph, c:c + pw] == ctx).all():
                return r, c
    return None


# ── THE UTTERANCE-BUILDER: agent state in, utterances out (reads NO world, NO after-state) ───

def classify(state: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """(class, unbuildable-reason). By what the loop HELD: a plan's atoms ->
    derivation; a wall-aware rung with a fatal prior held -> negative
    derivation; an exploration rung or nothing held -> probe; a state the
    builder cannot render -> unbuildable with the missing clause named."""
    if state.get("spine_bet") is None:
        return UNBUILDABLE, "no-bet"
    if state.get("opener") is None:
        return UNBUILDABLE, "no-frame"
    steps = state.get("plan_steps") or []
    if steps:
        if state.get("want_cells") is None:
            return UNBUILDABLE, "want-predicate"       # the abduced path's WANT, unrendered
        if state.get("atom_of") is None or state["atom_of"](steps[0]) is None:
            return UNBUILDABLE, "atom-unresolved"
        return DERIVATION, None
    if (str(state.get("rung") or "") == WALL_AWARE_RUNG and state.get("fatal")
            and state.get("avatar") is not None):
        return NEGATIVE, None
    return PROBE, None


def _bet_cells(state: Dict[str, Any]) -> Optional[Dict[Tuple[int, int], int]]:
    """The cells the derivation predicts, with their colours -- from the
    agent's OWN held prediction: a composite drive's predicted frames, or
    the plan atom's stored after-patch at the site its context matches in
    the agent's perceived opener. None when unrenderable."""
    drive = state.get("drive")
    cur = int(state.get("chain_cursor") or 0)
    if isinstance(drive, dict) and drive.get("frames"):
        try:
            f_from = np.asarray(drive["frame0"] if cur == 0 else drive["frames"][cur - 1])
            f_pred = np.asarray(drive["frames"][cur])      # the agent's OWN prediction
            return {(int(r), int(c)): int(f_pred[r, c])
                    for r, c in np.argwhere(f_from != f_pred)}
        except Exception:
            return None
    steps = state.get("plan_steps") or []
    rec = state["atom_of"](steps[0]) if steps else None
    atom = (rec or {}).get("atom") or rec
    if not isinstance(atom, dict) or atom.get("kind") != "EFFECT":
        return None
    try:
        ctx = np.asarray(atom["context"])
        out = np.asarray(atom["transform"]["after"])
        anchor = _anchor_of(ctx, np.asarray(state["opener"]))
        if anchor is None or out.shape != ctx.shape:
            return None
        r0, c0 = anchor
        return {(r0 + i, c0 + j): int(out[i, j])
                for i in range(out.shape[0]) for j in range(out.shape[1])
                if int(out[i, j]) != DONT_CARE}
    except Exception:
        return None


def _build_see_changed(state: Dict[str, Any], cited: Set[Tuple[int, int]]
                       ) -> Tuple[List[G.Term], List[G.Term]]:
    """SEE over the cited cells (the agent's perceived opener); CHANGED over
    the diff of the frame the agent TRACKED (its previous frame) vs the
    opener -- scope cited U changed, never the board (the cost pin)."""
    opener = np.asarray(state["opener"])
    h, w = opener.shape[:2]
    see = [G.compose(G.SEE, G.Leaf(G.T.OBJECT, SLOT), G.Leaf(G.T.REGION, (r, c)),
                     G.Leaf(G.T.ATTR, int(opener[r, c])))
           for r, c in sorted(cited) if 0 <= r < h and 0 <= c < w]
    changed: List[G.Term] = []
    prev = state.get("prev")
    if prev is not None and np.asarray(prev).shape == opener.shape:
        prev = np.asarray(prev)
        changed = [G.compose(G.CHANGED, G.Leaf(G.T.REGION, (r, c)),
                             G.Leaf(G.T.ATTR, int(prev[r, c])), G.Leaf(G.T.ATTR, int(opener[r, c])))
                   for r, c in sorted(_cells(prev != opener))]
    return see, changed


def _build_settle(state: Dict[str, Any]) -> Optional[G.Term]:
    """SETTLE the builder's own prior BET by id: held or broke, by d -- the
    residual of its stated prediction against the opener it now perceives
    (a label: legitimately reads the opener, last step's outcome)."""
    pb = state.get("prev_bet") or {}
    pred = pb.get("predicted") or {}
    if (not pb.get("id") or not pred or pb.get("settled")
            or int(pb.get("step", -99)) != int(state.get("step", 0)) - 1):
        return None                    # only step N-1's unsettled bet is settleable
    opener = np.asarray(state["opener"])
    h, w = opener.shape[:2]
    if any(not (0 <= r < h and 0 <= c < w) for r, c in pred):
        return None
    d = float(sum(1 for (r, c), v in pred.items() if int(opener[r, c]) != int(v)))
    head = "SAME" if d <= SETTLE_EPS else "OTHER"
    verdict = G.compose(head, G.Leaf(G.T.ATTR, ("residual", d)),
                        G.Leaf(G.T.ATTR, ("residual", 0.0)))
    return G.compose(G.SETTLE, G.ref(pb["id"], K_BET), verdict)


def _build_stand(state: Dict[str, Any]) -> List[G.Term]:
    """STAND from the bank's last settlement (the agent's own standing ledger)."""
    key, _bn = (state.get("settled_atom") or (None, None))
    if key is None:
        return []
    st = standing_change(state.get("settled_atom"), str(key))
    if st is None:
        return []
    return [G.compose(G.STAND, G.ref(key, K_ATOM), G.Leaf(G.T.ATTR, st))]


def build_perceive(state: Dict[str, Any]) -> Dict[str, Any]:
    """The PERCEIVE utterance + the facts the BET builder needs (class, the
    cited cells, the predicted cells). Never raises past `unbuildable`."""
    cls, why = classify(state)
    out: Dict[str, Any] = {"class": cls, "unbuildable": why, "term": None,
                           "cited": set(), "predicted": None, "fatal_cell": None}
    if why is not None:
        return out
    cited: Set[Tuple[int, int]] = set()
    if cls == DERIVATION:
        pred = _bet_cells(state)
        if pred is None:
            out.update(**{"class": UNBUILDABLE, "unbuildable": "bet-cells"})
            return out
        out["predicted"] = pred
        cited |= set(pred)
    elif cls == NEGATIVE:
        av = state["avatar"]
        cell = min(sorted(state["fatal"]),
                   key=lambda x: max(abs(x[0] - av[0]), abs(x[1] - av[1])))
        out["fatal_cell"] = cell
        cited |= {cell, (int(av[0]), int(av[1]))}
    # scope = cited U changed (the cost pin): SEE over what the derivation
    # reads, CHANGED over what moved -- never the board
    see, changed = _build_see_changed(state, cited)
    clauses: List[G.Term] = list(see) + list(changed)
    settle = _build_settle(state)
    if settle is not None:
        clauses.append(settle)
    clauses += _build_stand(state)
    out["term"] = G.compose(G.PERCEIVE, *clauses)
    out["cited"] = cited
    return out


def _build_want(state: Dict[str, Any]) -> G.Term:
    cells = state.get("want_cells")
    if cells is None:
        return G.compose(G.WANT, G.T.OBJ)                 # a template: probes only
    obj = G.compose("ALL", G.compose("BECOME", G.Leaf(G.T.OBJECT, SLOT),
                                     G.Leaf(G.T.ATTR, tuple((int(r), int(c), int(v))
                                                            for r, c, v in cells))))
    return G.compose(G.WANT, obj)


def _build_ground(state: Dict[str, Any], perceive_id: str, cls: str,
                  fatal_cell: Optional[Tuple[int, int]]) -> G.Term:
    refs: List[G.Leaf] = [G.ref(perceive_id, K_PERCEIVE)]
    if cls == DERIVATION:
        for aid in (state.get("plan_steps") or []):
            refs.append(G.ref(aid, K_ATOM, tag=_tag_of(state["atom_of"](aid))))
    elif cls == NEGATIVE and fatal_cell is not None:
        refs.append(G.ref("frontier:%s:%s:%d,%d" % (state.get("game"), state.get("level"),
                                                    fatal_cell[0], fatal_cell[1]),
                          K_FRONTIER))
    return G.compose(G.GROUND, *refs)


def _build_derive(state: Dict[str, Any], ground: G.Term, cls: str,
                  predicted: Optional[Dict[Tuple[int, int], int]],
                  fatal_cell: Optional[Tuple[int, int]]) -> G.Term:
    if cls == DERIVATION:
        steps = state.get("plan_steps") or []
        recs: List[G.Leaf] = [G.ref(steps[0], K_ATOM)]
        if state.get("composite"):
            recs.append(G.ref(state["composite"], K_COMPOSITE))   # the driven chain IS the bet
        bet = G.compose("BECOME", G.Leaf(G.T.OBJECT, SLOT),
                        G.Leaf(G.T.ATTR, tuple((r, c, v) for (r, c), v in sorted(
                            (predicted or {}).items()))))
        return G.compose(G.DERIVE, ground, *recs, bet)
    if cls == NEGATIVE:
        bet = G.compose("NOT", G.compose("BE_AT", G.Leaf(G.T.OBJECT, SELF),
                                         G.Leaf(G.T.REGION, fatal_cell)))
        return G.compose(G.DERIVE, ground, ground.args[1], bet)
    return G.compose(G.DERIVE, ground, G.T.PRED)          # the probe: a typed hole


def _build_pay(state: Dict[str, Any]) -> G.Term:
    """PAY from the agent's own citable ledger, the action book: the recorded
    spend with its n; the explicit null with the book's reason; a composite's
    derived price when the chain carries one (None -> null, never a number)."""
    if state.get("composite"):
        p = state.get("composite_price")
        return G.compose(G.PAY, G.price(None if p is None else float(p), None,
                                       "derived" if p is not None else "underivable"))
    if not state.get("book_loaded"):
        return G.compose(G.PAY, G.price(None, None, BOOK_ABSENT))
    cost = state.get("cost")
    if not isinstance(cost, dict):
        return G.compose(G.PAY, G.price(None, None, "explicit-null"))
    spend = (cost.get("budget_spend") or {}).get("mean")
    return G.compose(G.PAY, G.price(None if spend is None else float(spend),
                                   int(cost.get("n") or 0)))


def build_bet(state: Dict[str, Any], perceive: Dict[str, Any],
              perceive_id: str) -> Optional[G.Term]:
    """The BET utterance: WANT, GROUND (citing the perceive just emitted),
    DERIVE, PAY. GUARDED by the wall: reads agent state only."""
    cls = perceive["class"]
    if cls == UNBUILDABLE:
        return None
    want = _build_want(state)
    ground = _build_ground(state, perceive_id, cls, perceive.get("fatal_cell"))
    derive = _build_derive(state, ground, cls, perceive.get("predicted"),
                           perceive.get("fatal_cell"))
    return G.compose(G.BET, want, ground, derive, _build_pay(state))


def _build_need(state: Dict[str, Any], bet_id: str) -> G.Term:
    return G.compose(G.NEED, G.ref(bet_id, K_BET), G.Leaf(G.T.ATTR, int(state["action"])))


def build_act(state: Dict[str, Any], bet_id: str) -> G.Term:
    return G.compose(G.ACT, _build_need(state, bet_id))


# ── THE GATE: checks per head (executable / ledger / completeness) ────────────────────────────

def _v(verdict: str, token: Optional[str] = None, note: Optional[str] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"verdict": verdict, "token": token}
    if note is not None:
        out["note"] = note
    return out


def _ok() -> Dict[str, Any]:
    return _v(PASS)


def _in(frame: np.ndarray, r: int, c: int) -> bool:
    return 0 <= r < frame.shape[0] and 0 <= c < frame.shape[1]


def check_see(clause: G.Term, opener: np.ndarray) -> Dict[str, Any]:
    """EXECUTABLE: exact lookup on the opener frame."""
    _obj, region, attr = clause.args
    try:
        r, c = int(region.value[0]), int(region.value[1])
        if not _in(opener, r, c) or int(opener[r, c]) != int(attr.value):
            return _v(REFUSE, MISMATCH)
    except Exception:
        return _v(REFUSE, MISMATCH)
    return _ok()


def check_changed_set(clauses: List[G.Term], prev: Optional[np.ndarray],
                      opener: np.ndarray) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """COMPLETENESS, as a SET against compute_d(prev_opener, opener): every
    differing cell in some clause (else `unreported-change`), every clause in
    the diff with the right a -> b (else `false-change`). Returns (verdict,
    counts {differing, reported, unreported}). Never economised."""
    counts = {"differing": None, "reported": len(clauses), "unreported": None}
    if prev is None:
        return _v(UNVERDICTED, NO_PREVIOUS), counts
    d = compute_d(prev, opener)
    if d["differing"] < 0:
        return _v(UNVERDICTED, MISALIGNED), counts
    diff = _cells(np.asarray(prev) != np.asarray(opener))
    counts["differing"] = int(d["differing"])
    reported: Set[Tuple[int, int]] = set()
    for cl in clauses:
        region, a, b = cl.args
        try:
            r, c = int(region.value[0]), int(region.value[1])
            if ((r, c) not in diff or int(prev[r, c]) != int(a.value)
                    or int(opener[r, c]) != int(b.value)):
                counts["unreported"] = len(diff - reported)
                return _v(REFUSE, FALSE_CHANGE), counts
        except Exception:
            return _v(REFUSE, FALSE_CHANGE), counts
        reported.add((r, c))
    unreported = diff - reported
    counts["unreported"] = len(unreported)
    if unreported:
        return _v(REFUSE, UNREPORTED_CHANGE, note="%d" % len(unreported)), counts
    return _ok(), counts


def check_settle(clause: G.Term, opener: np.ndarray, step: int,
                 prev_bet: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """LEDGER + EXECUTABLE: the id resolves to this agent's step-N-1 BET,
    unsettled; the verdict equals the residual RECOMPUTED by identity with
    the function ROUTE bins on (PredictorBank._grid_residual)."""
    rf, verdict = clause.args
    if rf.kind != K_BET:
        return _v(REFUSE, WRONG_KIND)
    if not prev_bet or str(rf.value) != str(prev_bet.get("id")):
        return _v(REFUSE, NOT_HELD)
    if int(prev_bet.get("step", -99)) != int(step) - 1:
        return _v(REFUSE, WRONG_STEP)
    if prev_bet.get("settled"):
        return _v(REFUSE, ALREADY_SETTLED)
    pred = prev_bet.get("predicted") or {}
    if not pred:
        return _v(UNVERDICTED, NO_PREDICTION)
    if any(not _in(opener, r, c) for r, c in pred):
        return _v(UNVERDICTED, MISALIGNED)
    predicted = np.array(opener, copy=True)
    for (r, c), v in pred.items():
        predicted[r, c] = int(v)
    d = float(RESIDUAL(predicted, opener))
    held = d <= SETTLE_EPS
    try:
        claimed = float(verdict.args[0].value[1])
    except Exception:
        return _v(REFUSE, MISMATCH)
    if verdict.head not in ("SAME", "OTHER") or (verdict.head == "SAME") != held or claimed != d:
        return _v(REFUSE, MISMATCH, note="d=%g" % d)
    return _ok()


def check_stand(clause: G.Term, settled_atom: Any, settle_broke: bool,
                prev_bet_atoms: Set[str]) -> Dict[str, Any]:
    """LEDGER: equals the fabric's standing change for that id this step; an
    id cited in a bet that broke cannot strengthen in the same PERCEIVE."""
    rf, attr = clause.args
    if rf.kind != K_ATOM:
        return _v(REFUSE, WRONG_KIND)
    claimed = str(attr.value)
    if settle_broke and str(rf.value) in prev_bet_atoms and claimed == STRENGTHENED:
        return _v(REFUSE, STANDING_MISMATCH, note="cited-in-broken-bet")
    if standing_change(settled_atom, str(rf.value)) != claimed:
        return _v(REFUSE, STANDING_MISMATCH)
    return _ok()


def check_perceive(term: G.Term, opener: np.ndarray, prev: Optional[np.ndarray],
                   step: int, prev_bet: Optional[Dict[str, Any]],
                   settled_atom: Any) -> Dict[str, Any]:
    """Every clause checked and logged (shadow wants the whole picture); the
    first refusal is the named one."""
    clauses: List[Dict[str, Any]] = []
    changed = [cl for cl in term.args if cl.head == G.CHANGED]
    settle_broke = False
    for cl in term.args:
        if cl.head == G.SEE:
            v = check_see(cl, opener)
        elif cl.head == G.SETTLE:
            v = check_settle(cl, opener, step, prev_bet)
            settle_broke = cl.args[1].head == "OTHER"
        elif cl.head == G.STAND:
            v = check_stand(cl, settled_atom, settle_broke,
                            set((prev_bet or {}).get("atoms") or ()))
        else:
            continue
        clauses.append({"head": cl.head, "check": G.head_check(cl.head), **v})
    cv, counts = check_changed_set(changed, prev, opener)
    clauses.append({"head": G.CHANGED, "check": G.head_check(G.CHANGED), "n": len(changed),
                    **cv})
    return {"clauses": clauses, "completeness": counts, **_fold(clauses)}


def _fold(clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """pass iff every clause passes; the FIRST refusal is the named one;
    unverdicted iff no refusal and some clause has no verdict."""
    for cl in clauses:
        if cl["verdict"] == REFUSE:
            return {"verdict": REFUSE, "head": cl["head"], "token": cl["token"]}
    if any(cl["verdict"] == UNVERDICTED for cl in clauses):
        nv = next(cl for cl in clauses if cl["verdict"] == UNVERDICTED)
        return {"verdict": UNVERDICTED, "head": nv["head"], "token": nv["token"]}
    return {"verdict": PASS, "head": None, "token": None}


def check_want(clause: G.Term, opener: np.ndarray) -> Dict[str, Any]:
    """EXECUTABLE via the Discrepancy seam: -1 -> misaligned (never satisfied,
    never a magnitude); 0 -> vacuous; >0 -> pass with active = the cells."""
    obj = clause.args[0]
    if G.is_hole(obj):
        return _v(PASS, note="template")
    disc = want_discrepancy(obj)
    if disc is None:
        return _v(UNVERDICTED, UNCOMPILABLE)
    m = disc.measure(opener)
    if m < 0:
        return _v(REFUSE, MISALIGNED)
    if m == 0:
        return _v(REFUSE, VACUOUS)
    return _v(PASS, note="active=%d" % len(disc.active(opener)))


def check_ground(clause: G.Term, derive: G.Term, records: Dict[str, Dict[str, Any]],
                 step: int, bet_sq: int, perceive_terms: Dict[str, G.Term],
                 ledger: Dict[str, Any]) -> Dict[str, Any]:
    """LEDGER: the perceive is this step's, earlier in sequence; every cell
    DERIVE names appears in its SEE U CHANGED; every atom is held under the
    tag its memory range resolves to; a composite passes citation_allowed
    (ROLE_GROUND: settled only); a frontier record is a banked fatal cell."""
    pr = clause.args[0]
    if pr.kind != K_PERCEIVE:
        return _v(REFUSE, WRONG_KIND)
    meta = records.get(str(pr.value))
    if meta is None or meta["terminal"] != G.PERCEIVE or int(meta["step"]) != int(step):
        return _v(REFUSE, WRONG_STEP)
    if int(meta["sq"]) >= int(bet_sq):
        return _v(REFUSE, NOT_EARLIER)
    pterm = perceive_terms.get(str(pr.value))
    seen: Set[Tuple[int, int]] = set()
    for cl in (pterm.args if pterm is not None else ()):
        if cl.head in (G.SEE, G.CHANGED):
            reg = cl.args[1] if cl.head == G.SEE else cl.args[0]
            seen.add((int(reg.value[0]), int(reg.value[1])))
    for r, c in _derive_cells(derive):
        if (r, c) not in seen:
            return _v(REFUSE, NOT_IN_PERCEIVE)
    gamma = ledger.get("gamma")
    for rf in clause.args[1:]:
        if rf.kind == K_ATOM:
            rec = record_of(gamma, str(rf.value)) if gamma is not None else None
            if rec is None or (rf.tag is not None and _tag_of(rec) != rf.tag):
                return _v(REFUSE, NOT_HELD)
        elif rf.kind == K_COMPOSITE:
            if not citation_allowed(str(rf.value), ROLE_GROUND, gamma):
                return _v(REFUSE, UNSETTLED_COMPOSITE)
        elif rf.kind == K_FRONTIER:
            try:
                cell = tuple(int(x) for x in str(rf.value).rsplit(":", 1)[1].split(","))
            except Exception:
                return _v(REFUSE, NOT_HELD)
            if cell not in (ledger.get("fatal") or set()):
                return _v(REFUSE, NOT_HELD)
        else:
            return _v(REFUSE, WRONG_KIND)
    return _ok()


def _derive_cells(derive: G.Term) -> Set[Tuple[int, int]]:
    bet = derive.args[-1]
    if G.is_hole(bet):
        return set()
    if bet.head == "BECOME":
        try:
            return {(int(r), int(c)) for r, c, _v in bet.args[1].value}
        except Exception:
            return set()
    if bet.head == "NOT":
        try:
            reg = bet.args[0].args[1].value
            return {(int(reg[0]), int(reg[1]))}
        except Exception:
            return set()
    return set()


def check_derive(clause: G.Term, opener: np.ndarray, action: int,
                 ledger: Dict[str, Any]) -> Dict[str, Any]:
    """EXECUTABLE, three forms one head: positive (apply_effect of the cited
    atoms in order equals the bet on the cells it names), inverse (the two
    recorded deltas compose to identity; evidence n from inverse_of stated
    verbatim), negative (NOT over a banked fatal cell the chosen action does
    not enter). A typed hole in the bet position is the PROBE: its own
    ledger check against the book -- `book-absent` is a named non-verdict."""
    bet = clause.args[-1]
    recs = [a for a in clause.args[1:-1] if isinstance(a, G.Leaf)]
    gamma, game = ledger.get("gamma"), ledger.get("game")
    if G.is_hole(bet):
        return _check_probe(opener, action, ledger)
    for rf in recs:
        if rf.kind == K_COMPOSITE and not citation_allowed(str(rf.value), ROLE_BET, gamma):
            return _v(REFUSE, NOT_HELD, note="composite-unrecorded")
    atoms: List[Dict[str, Any]] = []
    for rf in recs:
        if rf.kind == K_ATOM:
            rec = record_of(gamma, str(rf.value)) if gamma is not None else None
            atom = (rec or {}).get("atom")
            if not isinstance(atom, dict):
                return _v(REFUSE, MISMATCH, note="unresolved:%s" % rf.value)
            atoms.append(atom)
    if bet.head == "BECOME":
        frame = np.asarray(opener)
        for atom in atoms:
            res = apply_effect(atom, frame)
            if res is None:
                return _v(REFUSE, MISMATCH, note="inapplicable")
            frame = res
        try:
            for r, c, v in bet.args[1].value:
                if not _in(frame, int(r), int(c)) or int(frame[r, c]) != int(v):
                    return _v(REFUSE, MISMATCH)
        except Exception:
            return _v(REFUSE, MISMATCH)
        return _ok()
    if bet.head == "SAME":                         # the inverse form
        try:
            _tag, a, b, n = bet.args[0].value
        except Exception:
            return _v(REFUSE, MISMATCH)
        if not ledger.get("book_loaded"):
            return _v(UNVERDICTED, BOOK_ABSENT)
        if _book.inverse_of(game, a) != (int(b), int(n)):
            return _v(REFUSE, MISMATCH, note="inverse-evidence")
        if len(atoms) != 2:
            return _v(REFUSE, MISMATCH, note="two-atoms")
        frame = np.asarray(opener)
        for atom in atoms:
            frame = apply_effect(atom, frame)
            if frame is None:
                return _v(REFUSE, MISMATCH, note="inapplicable")
        if frame.shape != opener.shape or not (frame == opener).all():
            return _v(REFUSE, MISMATCH, note="not-identity")
        return _ok()
    if bet.head == "NOT":                          # the negative form
        try:
            cell = tuple(int(x) for x in bet.args[0].args[1].value)
        except Exception:
            return _v(REFUSE, MISMATCH)
        if cell not in (ledger.get("fatal") or set()):
            return _v(REFUSE, MISMATCH, note="not-fatal")
        av = ledger.get("avatar")
        if av is None:
            return _v(UNVERDICTED, NO_AVATAR)
        delta = (ledger.get("deltas") or {}).get(int(action))
        if delta is None:
            return _v(UNVERDICTED, BOOK_ABSENT)
        if (int(av[0]) + int(delta[0]), int(av[1]) + int(delta[1])) == cell:
            return _v(REFUSE, MISMATCH, note="enters-fatal")
        return _ok()
    return _v(REFUSE, MISMATCH, note="unknown-form")


def _check_probe(opener: np.ndarray, action: int, ledger: Dict[str, Any]) -> Dict[str, Any]:
    if not ledger.get("book_loaded"):
        return _v(UNVERDICTED, BOOK_ABSENT)
    entry = _book.effect_summary(ledger.get("game"), action)
    if entry is None:
        return _v(UNVERDICTED, BOOK_ABSENT)
    if entry.get("atoms") is None:
        return _v(PASS, note="null-shape")
    held = ledger.get("held_for_action")
    atoms = held(int(action)) if callable(held) else []
    for atom in atoms:
        if apply_effect(atom, np.asarray(opener)) is not None:
            return _v(REFUSE, FALSE_IGNORANCE)
    return _v(PASS, note="no-applicable-atom")


def check_pay(clause: G.Term, action: int, ledger: Dict[str, Any],
              composite: Optional[str] = None) -> Dict[str, Any]:
    """LEDGER: equals action_book.cost_of with its n; a composite's derived
    price; where the book's cost is an explicit null PAY must state the null
    -- a number without evidence refuses as invented."""
    value, n, _reason = clause.args[0].value
    if composite is not None:
        derived = ledger.get("composite_price")
        if derived is None:
            return _ok() if value is None else _v(REFUSE, PRICE_INVENTED)
        return _ok() if value == float(derived) else _v(REFUSE, PRICE_MISMATCH)
    if not ledger.get("book_loaded") or _book.effect_summary(ledger.get("game"), action) is None:
        return _v(UNVERDICTED, BOOK_ABSENT)
    cost = _book.cost_of(ledger.get("game"), action)
    if not isinstance(cost, dict):
        return _ok() if value is None else _v(REFUSE, PRICE_INVENTED)
    if n is None:
        return _v(REFUSE, PRICE_INVENTED)
    spend = (cost.get("budget_spend") or {}).get("mean")
    if value != spend or int(n) != int(cost.get("n") or 0):
        return _v(REFUSE, PRICE_MISMATCH)
    return _ok()


def check_bet(term: G.Term, opener: np.ndarray, action: int, step: int, bet_sq: int,
              records: Dict[str, Dict[str, Any]], perceive_terms: Dict[str, G.Term],
              ledger: Dict[str, Any]) -> Dict[str, Any]:
    want, ground, derive, pay = term.args
    composite = next((str(a.value) for a in derive.args[1:-1]
                      if isinstance(a, G.Leaf) and a.kind == K_COMPOSITE), None)
    clauses = [
        {"head": G.WANT, "check": G.head_check(G.WANT), **check_want(want, opener)},
        {"head": G.GROUND, "check": G.head_check(G.GROUND),
         **check_ground(ground, derive, records, step, bet_sq, perceive_terms, ledger)},
        {"head": G.DERIVE, "check": G.head_check(G.DERIVE),
         **check_derive(derive, opener, action, ledger)},
        {"head": G.PAY, "check": G.head_check(G.PAY),
         **check_pay(pay, action, ledger, composite)},
    ]
    return {"clauses": clauses, **_fold(clauses)}


def check_need(clause: G.Term, step: int, act_sq: int,
               records: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """LEDGER: the bet is this step's, earlier in sequence (W1's F1 rule);
    the action is the one the bet ran or the probe names."""
    rf, attr = clause.args
    if rf.kind != K_BET:
        return _v(REFUSE, WRONG_KIND)
    meta = records.get(str(rf.value))
    if meta is None or meta["terminal"] != G.BET or int(meta["step"]) != int(step):
        return _v(REFUSE, WRONG_STEP)
    if int(meta["sq"]) >= int(act_sq):
        return _v(REFUSE, NOT_EARLIER)
    if int(attr.value) != int(meta.get("action", -1)):
        return _v(REFUSE, MISMATCH)
    return _ok()


def check_act(term: G.Term, step: int, act_sq: int,
              records: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    clauses = [{"head": G.NEED, "check": G.head_check(G.NEED),
                **check_need(term.args[0], step, act_sq, records)}]
    return {"clauses": clauses, **_fold(clauses)}


# ── rendering (records are JSON-plain) ───────────────────────────────────────────────────────

def _plain(x: Any) -> Any:
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (list, tuple, set)):
        return [_plain(i) for i in x]
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    return x


def render(x: Any) -> Any:
    if isinstance(x, G.Term):
        return {"head": x.head, "args": [render(a) for a in x.args]}
    if isinstance(x, G.Leaf):
        out: Dict[str, Any] = {"t": x.type.value, "v": _plain(x.value)}
        if x.kind is not None:
            out["k"] = x.kind
        if x.tag is not None:
            out["tag"] = x.tag
        return out
    if isinstance(x, G.T):
        return {"hole": x.value}
    return _plain(x)


# ── THE GATE OBJECT: one per game; the hook's single entry is step() ─────────────────────────

class ReasoningGate:
    """Shadow evaluation of PERCEIVE -> BET -> ACT per non-replay step. Its
    cross-step state: the previous opener frame (the gate's) and the
    previous BET's facts (id, predicted cells, cited atoms -- what SETTLE
    resolves). One fabric append per record; never raises past `errors`."""

    TOPIC = TOPIC

    def __init__(self, fabric: Any, game: str = "game", mode: Optional[str] = None,
                 game_dir: Optional[str] = None):
        self.fabric = fabric
        self.game = str(game)
        self.mode, self.downgraded = resolve_mode(mode)
        self.told = False
        self._sq = 0
        self._prev_opener: Optional[np.ndarray] = None
        self._prev_bet: Optional[Dict[str, Any]] = None
        self._records: Dict[str, Dict[str, Any]] = {}      # id -> {terminal, step, sq, action}
        self._perceive_terms: Dict[str, G.Term] = {}
        self.counters: Dict[str, int] = dict.fromkeys(
            ("evaluated", "pass", "would_refuse", "refuse", "unverdicted", "unbuildable",
             "replay", "errors", "downgrades"), 0)
        self.would_refuse_by_head: Dict[str, int] = {}
        # THE F3 COST DATA (gate wall-clock per step) lives HERE, in process --
        # never on a fabric stream: every stream is byte-identical across
        # identically-seeded runs (tests/gate/test_system_determinism.py), and
        # the narration log is held to the same law. coverage_report reads it
        # when passed {game: gate.cost}; a cost overrun is reported, not trimmed.
        self.cost: Dict[str, Any] = {"n": 0, "total_ms": 0.0, "max_ms": 0.0,
                                     "last_ms": None}
        self.book_loaded = False
        if self.mode != MODE_OFF:
            # THE FIRST LIVE CONSUMER of the action book (stage 0's named
            # promise): loaded FOR THIS GAME, or absent -- a box's book keyed to
            # other game ids is absence here, never evidence.
            if game_dir is not None:
                _book.load_action_book(game_dir)
            self.book_loaded = _book.effect_summary(self.game, 0) is not None

    # -- emission -------------------------------------------------------------------------------
    def _emit(self, terminal: str, step: int, payload: Dict[str, Any],
              ref: Optional[str] = None) -> Optional[str]:
        try:
            self._sq += 1
            rid = "g:%s:%d:%d" % (self.game, int(step), self._sq)
            rec: Dict[str, Any] = {"id": rid, "step": int(step), "sq": self._sq,
                                   "terminal": terminal, "ref": ref, "game": self.game,
                                   "mode": self.mode}
            for k, v in payload.items():
                if k not in rec:
                    rec[k] = _plain(v)
            self.fabric.append("personal", TOPIC, rec)
            return rid
        except Exception:
            self.counters["errors"] += 1
            return None

    def _tell(self, step: int) -> None:
        """The ladder narrated ONCE (like the ARM record), carrying the wall's
        announcement and the deadline marker; the downgrade record exactly
        once when `active` was asked for."""
        if self.told:
            return
        self.told = True
        bound: List[str] = []
        announce(bound.append)
        self._emit("MODE", step, {"value": self.mode, "downgraded": self.downgraded,
                                  "enforcement": ENFORCEMENT_ENABLED,
                                  "perceive_home": PERCEIVE_HOME,
                                  "deadline": deadline_violation(ENFORCEMENT_ENABLED,
                                                                 PERCEIVE_HOME),
                                  "book_loaded": self.book_loaded,
                                  "bound": bound[0] if bound else None})
        if self.downgraded:
            self.counters["downgrades"] += 1
            self._emit("DOWNGRADE", step, {"from": MODE_ACTIVE, "to": self.mode,
                                           "reason": "not-built-stage-1"})

    # -- the step -------------------------------------------------------------------------------
    def step(self, step: int, state: Dict[str, Any], ledger: Dict[str, Any]) -> None:
        """Evaluate one non-replay action: build, check, log. Returns None --
        there is no verdict to return; nothing here reaches the action path."""
        if self.mode == MODE_OFF:
            return
        t0 = time.perf_counter()
        try:
            self._tell(step)
            self._step(int(step), state, ledger, t0)
        except Exception:
            self.counters["errors"] += 1

    def _step(self, step: int, state: Dict[str, Any], ledger: Dict[str, Any],
              t0: float) -> None:
        state = dict(state)
        state["prev_bet"] = self._prev_bet
        opener = state.get("opener")
        world_opener = None if opener is None else np.asarray(opener)
        self.counters["evaluated"] += 1
        stratum = stratum_of(_book.effect_summary(self.game, state.get("action") or 0)
                             if self.book_loaded else None)
        summary: Dict[str, Any] = {
            "class": None, "rung": state.get("rung"), "action": state.get("action"),
            "anchor": state.get("anchor"), "stratum": stratum, "ids": {},
            "verdicts": {}, "completeness": None, "score": None,
            "unbuildable": None}                 # no wall-clock: streams are deterministic
        try:
            p = build_perceive(state)
        except G.TypeError_ as e:
            p = {"class": UNBUILDABLE, "unbuildable": ILL_TYPED, "term": None,
                 "note": str(e)}
        summary["class"] = p["class"]
        if p["class"] == UNBUILDABLE:
            summary["unbuildable"] = p["unbuildable"]
            self.counters["unbuildable"] += 1
            self._finish(step, state, summary, t0, world_opener)
            return
        # PERCEIVE: emit, then check against the GATE's own retained previous opener
        pv = check_perceive(p["term"], world_opener, self._prev_opener, step,
                            self._prev_bet, ledger.get("settled_atom"))
        pid = self._emit(G.PERCEIVE, step, {"utterance": render(p["term"]), **pv},
                         ref=state.get("spine_bet"))
        if pid is None:
            return
        self._records[pid] = {"terminal": G.PERCEIVE, "step": step, "sq": self._sq}
        self._perceive_terms[pid] = p["term"]
        summary["ids"][G.PERCEIVE] = pid
        summary["verdicts"][G.PERCEIVE] = pv["verdict"]
        summary["completeness"] = pv.get("completeness")
        if self._prev_bet is not None and any(cl.head == G.SETTLE for cl in p["term"].args):
            self._prev_bet["settled"] = True
        # BET
        try:
            bterm = build_bet(state, p, pid)
        except G.TypeError_ as e:
            bterm = None
            summary["unbuildable"] = ILL_TYPED
            summary["note"] = str(e)
        if bterm is None:
            summary["class"] = UNBUILDABLE
            self.counters["unbuildable"] += 1
            self._finish(step, state, summary, t0, world_opener)
            return
        bet_sq = self._sq + 1
        bv = check_bet(bterm, world_opener, int(state["action"]), step, bet_sq,
                       self._records, self._perceive_terms, ledger)
        bid = self._emit(G.BET, step, {"utterance": render(bterm), **bv,
                                       "action": state.get("action")},
                         ref=state.get("spine_bet"))
        if bid is None:
            return
        self._records[bid] = {"terminal": G.BET, "step": step, "sq": self._sq,
                              "action": int(state["action"])}
        summary["ids"][G.BET] = bid
        summary["verdicts"][G.BET] = bv["verdict"]
        if p["class"] == PROBE and self.book_loaded:
            summary["score"] = probe_score(_book.effect_summary(self.game, state["action"]))
        # ACT
        aterm = build_act(state, bid)
        act_sq = self._sq + 1
        av = check_act(aterm, step, act_sq, self._records)
        aid = self._emit(G.ACT, step, {"utterance": render(aterm), **av},
                         ref=state.get("spine_bet"))
        summary["ids"][G.ACT] = aid
        summary["verdicts"][G.ACT] = av["verdict"]
        # what SETTLE resolves next step
        self._prev_bet = {"id": bid, "step": step, "settled": False,
                          "predicted": dict(p.get("predicted") or {}),
                          "atoms": [str(a.value) for a in bterm.args[2].args[1:-1]
                                    if isinstance(a, G.Leaf) and a.kind == K_ATOM]}
        self._count(pv, bv, av)
        self._finish(step, state, summary, t0, world_opener)

    def _count(self, *verdicts: Dict[str, Any]) -> None:
        refusals = [v for v in verdicts if v["verdict"] == REFUSE]
        if refusals:
            # OBSERVE counts what it WOULD refuse; `refuse` is active's counter
            # and nothing in stage 1 increments it -- structurally zero.
            self.counters["would_refuse"] += 1
            for v in verdicts:
                for cl in v["clauses"]:
                    if cl["verdict"] == REFUSE:
                        k = "%s:%s" % (cl["head"], cl["token"])
                        self.would_refuse_by_head[k] = self.would_refuse_by_head.get(k, 0) + 1
        elif any(v["verdict"] == UNVERDICTED for v in verdicts):
            self.counters["unverdicted"] += 1
        else:
            self.counters["pass"] += 1

    def _finish(self, step: int, state: Dict[str, Any], summary: Dict[str, Any],
                t0: float, world_opener: Optional[np.ndarray]) -> None:
        self._emit("SUMMARY", step, summary, ref=state.get("spine_bet"))
        # the cost accumulates in process AFTER the write -- never in a record
        ms = (time.perf_counter() - t0) * 1000.0
        self.cost["n"] += 1
        self.cost["total_ms"] += ms
        self.cost["max_ms"] = max(float(self.cost["max_ms"]), ms)
        self.cost["last_ms"] = ms
        self._prev_opener = None if world_opener is None else np.array(world_opener, copy=True)
        # the step's records are the only ones citable: the ledger forgets the rest
        self._records = {k: v for k, v in self._records.items() if v["step"] == step}
        self._perceive_terms = {k: v for k, v in self._perceive_terms.items()
                                if k in self._records}


# ── THE THREE-NUMBER REPORT (per game; stratified; never folded) ──────────────────────────────

def coverage_report(gate_records: List[Dict[str, Any]],
                    narration_records: Optional[List[Dict[str, Any]]] = None,
                    cost: Optional[Dict[str, Dict[str, Any]]] = None
                    ) -> Dict[str, Any]:
    """Per game: derivations : negative derivations : probes as THREE numbers,
    with unverdicted / unbuildable / replay beside them, each stratified by
    the action's book evidence stratum floor(log2(n+1)) (None = book absent).
    Replay steps produce no gate record (they never pass the hook); they are
    counted from the spine's [REPLAY] narration, joined by game. Plus the
    would-refuse tokens per head. `cost` = {game: ReasoningGate.cost} carries
    the in-process wall-clock (the F3 cost finding's data -- it is NOT on
    the stream, by the determinism law) into the report beside the numbers."""
    out: Dict[str, Any] = {}

    def _game(g: str) -> Dict[str, Any]:
        return out.setdefault(str(g), {"strata": {}, "would_refuse": {}, "replay": 0,
                                       "cost": None})

    def _bucket(g: str, stratum: Any) -> Dict[str, int]:
        key = "book-absent" if stratum is None else str(int(stratum))
        return _game(g)["strata"].setdefault(key, {
            DERIVATION: 0, NEGATIVE: 0, PROBE: 0, UNBUILDABLE: 0, "unverdicted": 0})

    for rec in gate_records:
        if rec.get("terminal") != "SUMMARY":
            continue
        b = _bucket(rec.get("game"), rec.get("stratum"))
        cls = rec.get("class")
        if cls in b:
            b[cls] += 1
        verdicts = rec.get("verdicts") or {}
        if cls != UNBUILDABLE and verdicts and all(
                v != REFUSE for v in verdicts.values()) and any(
                v == UNVERDICTED for v in verdicts.values()):
            b["unverdicted"] += 1
    for rec in gate_records:
        if rec.get("terminal") in (G.PERCEIVE, G.BET, G.ACT) and rec.get("verdict") == REFUSE:
            wr = _game(rec.get("game"))["would_refuse"]
            for cl in rec.get("clauses") or []:
                if cl.get("verdict") == REFUSE:
                    k = "%s:%s" % (cl.get("head"), cl.get("token"))
                    wr[k] = wr.get(k, 0) + 1
    for rec in (narration_records or []):
        if rec.get("side") == _na.SIDE_REPLAY:
            _game(rec.get("game"))["replay"] += 1
    for g, c in (cost or {}).items():
        _game(g)["cost"] = dict(c)
    return out


# THE WALL, at import: the code will not load if a bet-side builder reads the outcome.
check_no_posthoc()

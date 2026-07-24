"""Locksmith L1.5 / audit module #1: GENERAL workspace/reference role detection by MUTATION. Across families A (match),
B (order), D (arrange) the agent brings a WORKSPACE to a REFERENCE; the general cue for WHICH is which is invariance --
the WORKSPACE is the region the agent CHANGES, the REFERENCE is the invariant target of the same shape. Role by
invariance, not position or size or any per-game pixel threshold (the displays move between corners across levels). This
feeds DIRECTED MATCH. Names no game; built + tested purely on synthetic streams."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.relation import RelationBank, RelationCtx
from newhorse.redux_arch.referent import Referent

R = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 1, 2, 3], [4, 5, 6, 7]])
WS_BB, REF_BB = (1, 9, 4, 12), (1, 1, 4, 4)


def _frame(ws, ref):
    g = np.zeros((6, 16), dtype=int)
    g[1:5, 1:5] = ref; g[1:5, 9:13] = ws
    return g


def _run(seq_ws, ref=R):
    bank = RelationBank(min_obs=4, min_range=1.0)
    ws_panel = Referent("panel", WS_BB, None, {})
    ref_panel = Referent("panel", REF_BB, None, {})
    ctxs = []
    for ws in seq_ws:
        ctx = RelationCtx(cursor=None, passable=frozenset(), bg=0)
        bank.observe(_frame(ws, ref), [ws_panel, ref_panel], ctx)
        ctxs.append(ctx)
    return bank, ctxs


def test_mutating_region_is_workspace_invariant_is_reference():
    # the workspace ROTATES toward the reference over the stream (it mutates); the reference is fixed
    seq = [np.rot90(R, 2), np.rot90(R, 2), np.rot90(R, 1), np.rot90(R, 1), R, R]
    bank, ctxs = _run(seq)
    assert bank.role_bboxes() == (WS_BB, REF_BB)              # role by invariance: the changing region = workspace
    assert ctxs[-1].match_roles is not None                   # directed (workspace, reference) exposed to MATCH


def test_two_invariant_panels_assign_no_roles():
    bank, ctxs = _run([R, R, R, R, R, R])                     # neither region changes -> no workspace can be named
    assert bank.role_bboxes() is None
    assert ctxs[-1].match_roles is None


def test_directed_match_uses_workspace_to_reference():
    # workspace ends one 90-degree rotation from the reference -> directed distance 1 (one operator), not raw pixels
    seq = [np.rot90(R, 2), np.rot90(R, 2), np.rot90(R, 2), np.rot90(R, 1), np.rot90(R, 1), np.rot90(R, 1)]
    bank, ctxs = _run(seq)
    assert bank.role_bboxes() == (WS_BB, REF_BB)
    assert bank.discrepancies()["MATCH"] == 1.0              # measured directed workspace->reference (rot90)


def test_role_by_invariance_not_by_position_or_size():
    """If the LEFT region is the one that mutates, IT is the workspace (roles are not tied to position)."""
    bank = RelationBank(min_obs=4, min_range=1.0)
    ws_panel = Referent("panel", REF_BB, None, {})           # left region is now the mutator
    ref_panel = Referent("panel", WS_BB, None, {})           # right region is now fixed
    seq = [np.rot90(R, 2), np.rot90(R, 2), np.rot90(R, 1), np.rot90(R, 1), R, R]
    for ws in seq:
        g = np.zeros((6, 16), dtype=int); g[1:5, 1:5] = ws; g[1:5, 9:13] = R
        bank.observe(g, [ws_panel, ref_panel], RelationCtx(cursor=None, passable=frozenset(), bg=0))
    assert bank.role_bboxes() == (REF_BB, WS_BB)             # the LEFT (mutating) region is the workspace

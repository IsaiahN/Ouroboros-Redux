"""Locksmith L3 -- the operator planner that makes MATCH drivable. Given the residual (what still
separates workspace from reference) + the learned operator map + the sites, it targets the site whose
operator reduces the residual; explores an untried site when none is known; acts on the workspace when
there are no separate sites (click-to-transform, e.g. cd82); and drives nothing once the residual is
identity. Names no game."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.operator_planner import OperatorPlanner
from newhorse.redux_arch.operator_effect import EDIT_KEY
from newhorse.redux_arch.transform import Transform


def _geom_residual():
    return Transform("geom", "rot90", None, 1.0)          # workspace needs a rotation to match reference


def test_no_drive_when_residual_solved():
    p = OperatorPlanner()
    assert p.plan(None, {}, [], None)[0] is None
    ident = Transform("identity", None, None, 0.0)
    assert p.plan(ident, {}, [], None)[0] is None


def test_targets_a_known_relevant_operator():
    p = OperatorPlanner()
    sites = [("A", (10, 10, 12, 12)), ("B", (20, 20, 22, 22))]
    operators = {"A": ("recolour", None, None), "B": ("geom", "rot90", None)}   # B rotates, A recolours
    cell, note = p.plan(_geom_residual(), operators, sites, workspace_bbox=(0, 0, 4, 4))
    assert cell == (21, 21) and note.startswith("match:apply-operator(B)")       # a geom residual -> the geom operator


def test_explores_untried_site_when_no_known_relevant_operator():
    p = OperatorPlanner()
    sites = [("A", (10, 10, 12, 12)), ("B", (20, 20, 22, 22))]
    operators = {"A": ("recolour", None, None)}            # only A known, and it's the wrong kind for a geom residual
    cell, note = p.plan(_geom_residual(), operators, sites, workspace_bbox=None)
    assert cell == (21, 21) and note.startswith("match:explore-site(B)")         # go learn the untried site


def test_acts_on_workspace_when_no_separate_sites():
    p = OperatorPlanner()
    cell, note = p.plan(_geom_residual(), {}, [], workspace_bbox=(30, 30, 34, 34))
    assert cell == (32, 32) and note == "match:act-on-workspace"                 # click-to-transform (cd82/ft09)


def test_edit_residual_wants_an_edit_site():
    p = OperatorPlanner()
    sites = [("E", (5, 5, 5, 5))]
    operators = {"E": EDIT_KEY}
    resid = Transform("edit", None, None, 3.0)
    cell, note = p.plan(resid, operators, sites, workspace_bbox=(0, 0, 2, 2))
    assert cell == (5, 5) and note.startswith("match:apply-operator(E)")

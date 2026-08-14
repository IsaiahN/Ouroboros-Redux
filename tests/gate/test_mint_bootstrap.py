"""The mint-bootstrap fix: NOVEL workspace evidence must reach the mint, or the first atom
can never be born (assembly1's first live finding: [MINT] 0 -- BROKEN-mechanism requires a
known atom to be wrong, but a fresh Gamma knows nothing, so everything routes NOVEL and the
mint starves). The mint's own guards (SUPPORT x NOVELTY x MDL) do the filtering -- that is
what guards are for.
"""
from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def test_novel_workspace_evidence_feeds_the_mint():
    src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
               errors="replace").read()
    i = src.find("NOVEL")
    assert i != -1
    # the W4c mint drain must consider NOVEL workspace items, not only mint_queue
    assert "import_queue" in src
    j = src.find(".consider(")
    window = src[max(0, j - 3000):j + 500]
    assert "NOVEL" in window or "novel" in window, (
        "the mint eats only BROKEN-mechanism -- with an empty Gamma the first atom can never "
        "be born; NOVEL workspace evidence must also be offered (the guards filter)")


def test_fabric_seeds_env_is_read():
    """Swarm prerequisite: the loop's fabric init must mount read-only seed dirs from
    OURO_FABRIC_SEEDS (';'-separated) -- the official swarm shape's no-merge cross-mounting."""
    src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
               errors="replace").read()
    assert "OURO_FABRIC_SEEDS" in src, "no seeds env -- workers cannot cross-mount fabrics"
    i = src.find("OURO_FABRIC_SEEDS")
    window = src[max(0, i - 500):i + 800]
    assert "seeds" in window and "KnowledgeFabric" in window, (
        "the env var is read but never reaches the fabric constructor")


def test_the_primal_path_click_with_change_reaches_the_mint():
    """Second bootstrap gap (swarm vitals): NOVEL routing requires a BET, and WORKSPACE
    cannot bet without atoms -- the starvation moved one link up. The primal path: a click
    that changed the frame is offered to the mint DIRECTLY (dense R_tau mints EFFECT atoms);
    NOVELTY dedups, MDL filters, the bar gates."""
    src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
               errors="replace").read()
    i = src.find("primal")
    assert i != -1, "no primal mint path -- the mint still starves behind the bet requirement"
    window = src[max(0, i - 1500):i + 1500]
    assert ".consider(" in window and "frame_changed" in window, (
        "the primal path must offer click-with-change evidence to consider()")

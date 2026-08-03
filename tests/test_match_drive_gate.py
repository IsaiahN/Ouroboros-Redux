"""B2 MATCH drive is FLAG-GATED: OURO_MATCH_DRIVE off = MATCH stays non-drivable (zero runtime change);
on = drive_target may pursue the MATCH target. And _drive_match never crashes the policy."""
import os, numpy as np, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.relation import RelationBank, RelationCtx

def _bank(flag):
    os.environ.pop("OURO_MATCH_DRIVE", None)
    if flag: os.environ["OURO_MATCH_DRIVE"] = "1"
    b = RelationBank(); os.environ.pop("OURO_MATCH_DRIVE", None); return b

def test_match_not_drivable_when_flag_off():
    b = _bank(False); b.last_target["MATCH"] = (5, 5); b.selected = lambda: "MATCH"
    assert b.drive_target() != (5, 5)          # off -> MATCH not drivable -> falls through (REACH/CONNECT None)

def test_match_drivable_when_flag_on():
    b = _bank(True); b.last_target["MATCH"] = (5, 5); b.selected = lambda: "MATCH"
    assert b.drive_target() == (5, 5)          # on -> MATCH drivable -> pursues its target

def test_drive_match_never_crashes():
    b = _bank(True)
    b.observe(np.zeros((10, 10), dtype=int), [], RelationCtx())   # no panels/roles -> no-op, no crash
    assert True

"""
The NOVELTY-claim tripwire. A NOVEL mint must never be self-certified by the build -- it is parked as an
UNCONFIRMED claim until a HUMAN confirms it. RE-DERIVATION passes through (nothing invented to certify).
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.novelty_ledger import (record_novelty_claim, is_confirmed, guarded_promote, claim_key)


def test_re_derivation_passes_through(tmp_path):
    cp = str(tmp_path / "claims.jsonl"); fp = str(tmp_path / "confirmed.txt")
    # a RE-DERIVATION invents nothing -> build may proceed, and NO claim is recorded
    assert guarded_promote("RE-DERIVATION", "NEAR(focus,target)", 47.7, "m0r0", claims_path=cp, confirmed_path=fp) is True
    assert not os.path.exists(cp)


def test_novel_is_parked_until_human_confirms(tmp_path):
    cp = str(tmp_path / "claims.jsonl"); fp = str(tmp_path / "confirmed.txt")
    # first time a NOVEL fires: recorded UNCONFIRMED, build is NOT allowed to act
    allowed = guarded_promote("NOVEL", "COUNT_EQUALS(k)", 61.0, "xx99", context="collect-all", claims_path=cp, confirmed_path=fp)
    assert allowed is False
    rec = json.loads(open(cp).read().splitlines()[-1])
    assert rec["status"] == "UNCONFIRMED" and rec["name"] == "COUNT_EQUALS(k)" and rec["game"] == "xx99"
    # a human writes the key into the confirmations file
    with open(fp, "w") as f:
        f.write("# confirmed by Isaiah after review\n" + claim_key("COUNT_EQUALS(k)", "xx99") + "\n")
    # now (and only now) the build may act on it
    assert guarded_promote("NOVEL", "COUNT_EQUALS(k)", 61.0, "xx99", claims_path=cp, confirmed_path=fp) is True


def test_confirmation_is_specific_to_the_claim(tmp_path):
    cp = str(tmp_path / "claims.jsonl"); fp = str(tmp_path / "confirmed.txt")
    with open(fp, "w") as f:
        f.write(claim_key("A", "g1") + "\n")
    assert is_confirmed("A", "g1", confirmed_path=fp) is True
    assert is_confirmed("B", "g1", confirmed_path=fp) is False     # a different predicate is not covered
    assert is_confirmed("A", "g2", confirmed_path=fp) is False     # nor the same predicate on another game

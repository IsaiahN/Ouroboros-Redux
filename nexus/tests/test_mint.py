"""The sensor mint: sensors compete like hypotheses, priced by how much a channel's value reduces
uncertainty about DEATH. An informative channel is kept (minted); an irrelevant one biodegrades."""
from nexus.sensorium.mint import SensorMint


def test_informative_channel_earns_positive_gain():
    m = SensorMint(min_evidence=4, min_gain=0.02)
    # SELF_LOCAL perfectly predicts death; NOISE is constant (carries nothing)
    for _ in range(6):
        m.observe("A4", {"SELF_LOCAL": ("wall",), "NOISE": (0,)}, fatal=True)
        m.observe("A4", {"SELF_LOCAL": ("open",), "NOISE": (0,)}, fatal=False)
    assert m.information_gain("SELF_LOCAL") > 0.5   # separates fatal from survived
    assert m.information_gain("NOISE") == 0.0        # constant -> no information about death


def test_active_channels_needs_evidence_then_mints():
    m = SensorMint(min_evidence=6, all_channels=("AVAILABLE", "SELF_LOCAL"))
    assert m.active_channels() == ()                 # nothing learned yet -> not minted
    for _ in range(8):
        m.observe("A4", {"AVAILABLE": (1, 2, 3, 4), "SELF_LOCAL": ("wall",)}, fatal=True)
        m.observe("A4", {"AVAILABLE": (1, 2, 3, 4), "SELF_LOCAL": ("open",)}, fatal=False)
    ch = m.active_channels()
    assert "SELF_LOCAL" in ch and "AVAILABLE" in ch  # the discriminating sensor is minted (+ affordance kept)


def test_unhashable_channel_value_does_not_crash():
    m = SensorMint(min_evidence=1)
    m.observe("A1", {"WEIRD": {"a": [1, 2]}}, fatal=True)   # dict value -> stringified, not an error
    assert m.information_gain("WEIRD") == 0.0        # single class -> no gain, but survived the observe

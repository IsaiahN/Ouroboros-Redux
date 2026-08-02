"""nexus.sensorium -- composition as minted perception.

The embodiment lever from DESIGN_the_sensorium_composition_as_minted_perception: give the agent a
sensorium whose sensors are the INFORMATION a sense provides, expressed as typed before-state
functions, minted per game and priced by the ground -- never a ported sensor list, never a closed
vocabulary. Four organs:

  ForwardModel  (forward.py) -- efference copy: predict the next grid, yield self-mask + residual.
  Sensorium     (sensors.py) -- the open typed sensor registry + the self-relative danger signature.
  SensorMint    (mint.py)    -- the proposer minting which channels carry danger (ground-priced).
  build_sensorium()          -- wires them into a drop-in `signature_fn` for the verdict circuit.
"""
from .forward import ForwardModel, as_grid2d, background_colour
from .sensors import Sensorium, SensedState, register_channel
from .self_family import (SelfModelFamily, TranslationSelf, GrowthEdgeSelf,
                          ValueLatentSelf, RegionToggleSelf)
from .mint import SensorMint


def build_sensorium(min_evidence: int = 6, unmodeled_threshold: float = 0.6):
    """Wire the organs into a Sensorium: a non-simulable self-hypothesis family + the sensor mint.
    Returns the Sensorium; use `sensorium.signature` as the runner's `signature_fn` and call
    `sensorium.observe(...)` per step."""
    return Sensorium(mint=SensorMint(min_evidence=min_evidence),
                     unmodeled_threshold=unmodeled_threshold)

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
from .mint import SensorMint


def build_sensorium(window: int = 2, min_evidence: int = 6):
    """Wire the four organs into a Sensorium with an attached mint. Returns the Sensorium; use
    `sensorium.signature` as the runner's `signature_fn` and call `sensorium.observe(...)` per step."""
    s = Sensorium(window=window, mint=SensorMint(min_evidence=min_evidence))
    return s

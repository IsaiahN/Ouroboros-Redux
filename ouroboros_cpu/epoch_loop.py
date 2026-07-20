"""
EPOCH LOOP  —  the generation boundary, and the selection that happens at it.

WHY THIS FILE EXISTS
--------------------
`_epoch_check` and `_macro_sync` were nested functions inside `_avatar_solve` -- a 2002-line host with 63 nested
defs. They work today by accident rather than design: they happen to keep their state on `adapter._micro_market`
rather than in the closure, so they survive when the host returns. Everything beside them that used a local -- which
boosters were drained, which targets were unreachable, where the agent had already been -- did not.

That is not a property anyone chose. It is a coin landing the right way up, in a file where the same coin landed
wrong five times. Selection is the mechanism the whole architecture rests on; it should not be reachable only from
inside one regime's closure, and it should not depend on which variable a past edit happened to hang state from.

WHAT AN EPOCH IS
----------------
A LIFE. The generation boundary has to be something the WORLD does, not a number chosen by whoever wrote the loop --
otherwise selection is being paid for in a currency the author minted, and by ROOT IV that is a Levin-null loop with
extra steps. This game kills you: death is the boundary, and the body count is the one currency the board itself
issues. Where a game has no loss signal, an action ceiling stands in for one -- an artificial mortality, so the
population still turns over instead of one lineage riding a single life forever.

WHAT IT IS NOT
--------------
It is not a scheduler. Nothing here decides WHO wins; the ledger does, priced against frames the agent did not
author. This module decides only WHEN the population turns over, which is the one thing the environment gets to say.
"""

import os


class EpochLoop:
    """One per game. Holds nothing the market does not already hold; owns only the boundary."""

    DEFAULT_CAP = 120                 # fallback ONLY -- see _cap()

    def __init__(self, emit=None):
        self.emit = emit or (lambda s: None)
        self.epochs = 0
        self.by_death = 0
        self.by_ceiling = 0
        self.history = []

    @staticmethod
    def _cap(adapter=None):
        """The stand-in mortality, when a game offers no death signal. It must BE a life.

        This was 120, on a board whose life is 42 -- an artificial mortality nearly THREE TIMES the real one. Where
        a game does kill you, real death fires first and the cap never mattered, which is exactly why nobody noticed.
        On a game that does not kill you, this number IS the generation boundary, and a boundary three lives long
        means selection runs a third as often as the world allows.

        An epoch is a LIFE. So ask the board how long a life is; only fall back if it has not said yet.
        """
        env = os.environ.get("OURO_EPOCH_ACTIONS")
        if env:
            try:
                return int(env)
            except Exception:
                pass
        if adapter is not None:
            try:
                import budget_model as _BM
                life = _BM.get(adapter).one_life()
                if life:
                    return int(life)
            except Exception:
                pass
        return EpochLoop.DEFAULT_CAP

    @staticmethod
    def _dead(adapter):
        try:
            return "GAME_OVER" in str(getattr(getattr(adapter, "_obs", None), "state", "") or "").upper()
        except Exception:
            return False

    def due(self, adapter, epoch_actions):
        """Has the world ended a generation, or has the stand-in mortality?"""
        if self._dead(adapter):
            return "death (the game's own loss signal)"
        cap = self._cap(adapter)
        if epoch_actions >= cap:
            return "action ceiling %d = one measured life (no loss signal available)" % cap
        return None

    def step(self, adapter, st):
        """Run one generation boundary if one is due. Returns the evolution report, or None."""
        why = self.due(adapter, st.get("epoch_actions", 0))
        if why is None:
            return None
        self.epochs += 1
        if "death" in why:
            self.by_death += 1
        else:
            self.by_ceiling += 1
        st["epoch"] = st.get("epoch", 0) + 1
        rep = None
        try:
            if st.get("evo") is not None:
                rep = st["evo"].step()
        except Exception:
            pass
        try:
            if st.get("pariah") is not None:
                st["pariah"].tick()          # toxicity decays: a bad idea is not bad forever, only bad for now
        except Exception:
            pass
        self.history.append({"epoch": st["epoch"], "why": why,
                             "levels_this_epoch": st.get("epoch_levels", 0)})
        if len(self.history) > 60:
            self.history.pop(0)
        st["epoch_actions"] = 0
        st["epoch_levels"] = 0
        st["wins_this_epoch"] = 0
        self.emit("EPOCH %d ends: %s -> selection runs" % (st["epoch"], why))
        return rep

    def report(self):
        return {"epochs": self.epochs, "by_death": self.by_death, "by_action_ceiling": self.by_ceiling,
                "recent": self.history[-5:]}

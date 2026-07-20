"""
BUDGET MODEL  —  one model of the agent's own resources, for the whole agent.

WHY THIS FILE EXISTS
--------------------
There were two, and the second one exists *because* the first was unreachable.

`_hud_units()`, `_rate()` and `_budget_actions()` are defined inside `_avatar_solve` -- a 2002-line function with 63
nested defs. Nothing outside that closure can call them. So when the market needed to reason about the budget, it
could not reach the model that already existed, and `Q1Hud` was written to induce the same quantities from scratch.

Two models of one board, neither able to see the other. They disagreed -- the closure said the drain rate was a
guessed 4.0, `Q1Hud` induced 4.0 from a polluted sample, and the board charges 2 -- and both were debugged separately,
for hours, each internally consistent and confidently wrong. That is Mars Climate Orbiter with the units the other way
round: *both parties internally consistent, both confident, no shared instrument check.*

The trap did not merely hide the code. It CAUSED a duplicate implementation of the code. That is the strongest
evidence in this tree that burying a mechanism in a monolith has a price, and the price is not readability.

This module is subtractive: it replaces both.

WHAT IT KNOWS, AND HOW IT KNOWS IT
----------------------------------
Nothing about any game. Every quantity is induced from watching the frame:

  the meter    -- the colour that only ever decreases between refills
  the bar      -- meters are BARS; the bar's LENGTH is the quantity, in the units the agent spends
  one life     -- the longest that bar has ever been
  lives        -- a colour that falls at refills and can never be bought back
  actions left -- read off the bar. Not inferred, not divided by a guessed constant. COUNTED.

THE READING THAT MATTERS
------------------------
`_budget_actions()` used to compute `area / rate`: it counted the bar's AREA (84 = 42 columns x 2 rows) and divided by
a GUESSED rate of 4, getting 21. The bar is 42 columns wide and one column is one action. **The agent believed it had
half its budget for the life of the project**, and priced every resource decision against that. The rate was never a
fact to discover -- it is an artefact of the bar being two pixels tall. Measure the length; the constant disappears.
"""

import numpy as np
from collections import Counter, deque

MIN_OBS = 8
HUD_LO, HUD_HI = 56, 64

# The bar's LENGTH is measured in columns. What ONE ACTION COSTS, in columns, is a QUANTITY -- not a constant.
# A short window (not a lifetime tally) because the price CHANGES at a level boundary and a lifetime mode would
# average the old level's price into the new one's. Same class as the lifetime-ratio-as-a-decision bug.
MIN_RATE_OBS = 3
RATE_WINDOW = 8


class BudgetModel:
    """Induced, not configured. One instance per adapter, held for the whole game."""

    def __init__(self, lo=HUD_LO, hi=HUD_HI, emit=None):
        self.lo, self.hi = lo, hi
        self.emit = emit                  # the model that decides how many actions remain must be able to say so
        self._said = set()
        self.meter = None                 # the colour that measures what an action costs
        self.lives = None                 # the colour that counts what cannot be bought back
        self.hist = []                    # colour -> count, per observation
        self.frames = []                  # recent raw frames, so the BAR can be measured not inferred
        self.rises = set()                # colours seen to increase -> cannot be a lives counter
        self.fell_at_refill = {}          # colour -> refills it fell at; lives falls at ALL of them
        self.refills = 0
        self.full_seen = 0                # the longest the bar has ever been = one life, in actions
        self.full_cols_seen = 0           # ...held in COLUMNS, which is rate-independent, so a change in the
        #                                   column-price re-prices one_life() instead of leaving a stale maximum
        self.col_drops = deque(maxlen=RATE_WINDOW)   # what each action actually cost, in columns. Watched, not set.
        self._rate_said = None
        self.obs = 0

    # ---- induction ---------------------------------------------------------------------------------------------
    def observe(self, before, after):
        """One action's evidence. Cheap; safe to call on every action, and it must be."""
        try:
            self.obs += 1
            hb, ha = self._hist(before), self._hist(after)
            if not hb or not ha:
                return
            self.hist.append(ha)
            self.frames.append(self._band(after))
            if len(self.hist) > 400:
                self.hist.pop(0)
            if len(self.frames) > 8:
                self.frames.pop(0)
            for c, n in ha.items():
                if n > hb.get(c, 0):
                    self.rises.add(c)
            if self.meter is None and len(self.hist) >= MIN_OBS:
                self._induce_meter()
            if self.meter is not None:
                d = ha.get(self.meter, 0) - hb.get(self.meter, 0)
                if d > 0:                                   # THE METER REFILLED -> a life boundary or a booster
                    self.refills += 1
                    for c in set(list(hb.keys()) + list(ha.keys())):
                        if c == self.meter:
                            continue
                        if ha.get(c, 0) < hb.get(c, 0):
                            self.fell_at_refill[c] = self.fell_at_refill.get(c, 0) + 1
                    if self.lives is None and self.refills >= 2:
                        self._induce_lives()
                else:
                    # NOT a refill. Whatever the bar just lost is what one action COSTS -- the board quoting its
                    # own price. This is the only place that price is ever established; nothing sets it.
                    cb, ca = self._bar_cols(self._band(before)), self._bar_cols(self._band(after))
                    if cb is not None and ca is not None and cb > ca:
                        self.col_drops.append(cb - ca)
                        self._say_rate()
                cols = self._bar_cols(self._band(after))
                if cols:
                    self.full_cols_seen = max(self.full_cols_seen, cols)
                n = self.bar_actions(self._band(after))
                if n:
                    self.full_seen = max(self.full_seen, n)
        except Exception:
            pass

    def _say_rate(self):
        """The price is the one budget fact that CHANGES mid-game, so it is the one that must re-speak when it does.
        `_say` is once-per-claim by design (a line repeated every action is noise); a changed price is a NEW claim,
        and the change itself is the finding -- so the key carries the value."""
        r = self.cols_per_action()
        if r is None or r == self._rate_said:
            return
        was, self._rate_said = self._rate_said, r
        life = self.one_life()
        if was is None:
            self._say("BUDGET  price := %d column(s)/action  [MEASURED off %d of my own actions -- the board quoted "
                      "it by charging me; a full bar is therefore %s actions, not %s]"
                      % (r, len(self.col_drops), life, self.full_cols_seen or "?"), "rate:%d" % r)
        else:
            self._say("BUDGET  price CHANGED := %d -> %d column(s)/action  [the board is charging %.1fx what it did. "
                      "A full bar was %s actions and is now %s. Every route I priced before this line was priced at "
                      "the OLD rate and is wrong by that factor -- re-price before committing]"
                      % (was, r, r / float(was), (self.full_cols_seen // was if was else "?"), life),
                      "rate:%d->%d" % (was, r))

    def _say(self, msg, key):
        """Once per distinct claim. The stream is the evidentiary record, not a log: a line repeated every action
        is noise, and noise is where a real finding goes to hide."""
        if self.emit is None or key in self._said:
            return
        self._said.add(key)
        try:
            self.emit(msg)
        except Exception:
            pass

    def _induce_meter(self):
        """The meter is the colour that only ever falls between refills. Nothing is told; it is watched."""
        cand = {}
        for i in range(1, len(self.hist)):
            for c, n in self.hist[i].items():
                prev = self.hist[i - 1].get(c, 0)
                if n < prev:
                    cand[c] = cand.get(c, 0) + 1
                elif n > prev:
                    cand[c] = cand.get(c, 0) - 3          # a resource does not refill itself mid-life
        best = [c for c, v in sorted(cand.items(), key=lambda t: -t[1]) if v > 0]
        if best:
            self.meter = best[0]
            self._say("BUDGET  meter := colour %s  [BECAUSE it is the only colour that ONLY EVER FALLS between "
                      "refills -- nothing told me; I watched it]" % self.meter, "meter")

    def _induce_lives(self):
        """A life cannot be bought back: the lives colour never rises, and falls at every refill."""
        best, score = None, 0
        for c, k in self.fell_at_refill.items():
            if c in self.rises:
                continue
            if k > score:
                best, score = c, k
        if best is not None and score >= 2:
            self.lives = best
            self._say("BUDGET  lives := colour %s  [BECAUSE it NEVER rises and falls at every refill -- a life is "
                      "the one thing on this board that cannot be bought back]" % self.lives, "lives")

    # ---- the readings ------------------------------------------------------------------------------------------
    def _bar_cols(self, band=None):
        """The bar's LENGTH, in columns. The raw reading -- before anything is divided into it."""
        if self.meter is None:
            return None
        try:
            b = self._band(band) if band is not None and np.ndim(band) > 1 and np.shape(band)[0] > (self.hi - self.lo) \
                else (band if band is not None else (self.frames[-1] if self.frames else None))
            if b is None:
                return None
            ys, xs = np.where(np.asarray(b) == self.meter)
            return int(len(np.unique(xs))) if len(xs) else 0
        except Exception:
            return None

    def cols_per_action(self):
        """What ONE ACTION COSTS, in columns. MEASURED from this level's own transitions.

        THE CORRECTION THIS FILE'S OWN DOCSTRING NEEDS
        ----------------------------------------------
        The header above says the rate 'is an artefact of the bar being two pixels tall' and that counting columns
        makes the constant disappear: 'one column, one action.' That is TRUE ON THE FIRST LEVEL AND FALSE ON THE
        SECOND. Measured live on two independent recordings of ls20, the board charges:

            level 1 -> 1 column per action   (42 columns = 42 actions)   <- 'one column, one action' holds
            level 2 -> 2 columns per action  (42 columns = 21 actions)   <- it does not

        So the previous fix traded a GUESSED rate of 4 for an ASSUMED rate of 1. Both are guesses; the assumed one
        happens to be right where it was tested. The agent then walked onto level 2 believing 42 and holding 21,
        priced a 17-step route to the exit at 40% of budget when it was 85%, and died four-fifths of the way there
        on every life -- confidently, and with correct arithmetic on a wrong constant.

        The constant did not evaporate. It CHANGED. A quantity that changes is not a constant to be reasoned away;
        it is a thing to keep watching. So: count the drops, take the mode of the recent ones, and let the level
        boundary re-price it the same way the board does -- by charging.
        """
        if len(self.col_drops) < MIN_RATE_OBS:
            return None
        # The board has charged the same NEW price MIN_RATE_OBS times running -> that IS the price, now. Taking the
        # mode of the whole window instead would keep quoting the old level's price until the new one outvoted it,
        # which measured out at ~10 actions of a 21-action tank spent at a rate the board had already stopped using.
        # A price is not a poll of history; it is what you were last charged, consistently.
        recent = list(self.col_drops)[-MIN_RATE_OBS:]
        if len(set(recent)) == 1 and recent[0] > 0:
            return int(recent[0])
        r = Counter(self.col_drops).most_common(1)[0][0]
        return int(r) if r > 0 else None

    def bar_actions(self, band=None):
        """ACTIONS remaining, MEASURED off the bar: its length in columns, divided by what an action costs.

        Until the price has been watched enough times (MIN_RATE_OBS), this reports the raw column count -- the old
        behaviour, which is right on level 1 -- and says so rather than pretending to a precision it has not earned.
        """
        cols = self._bar_cols(band)
        if cols is None:
            return None
        r = self.cols_per_action()
        return int(cols // r) if r else int(cols)

    def one_life(self):
        """How many actions a full meter buys. Induced: the longest the bar has ever been, at TODAY's price."""
        r = self.cols_per_action()
        if self.full_cols_seen:
            return int(self.full_cols_seen // r) if r else int(self.full_cols_seen)
        return self.full_seen or None

    def lives_left(self, frame=None):
        if self.lives is None:
            return None
        try:
            b = self._band(frame) if frame is not None else (self.frames[-1] if self.frames else None)
            if b is None:
                return None
            per = self._per_life_unit()
            n = int((np.asarray(b) == self.lives).sum())
            return int(round(n / per)) if per else n
        except Exception:
            return None

    def actions_left(self, frame=None):
        """Actions until GAME OVER -- this life plus every life still in hand."""
        this = self.bar_actions(self._band(frame) if frame is not None else None)
        if this is None:
            return None
        lv = self.lives_left(frame)
        full = self.one_life() or 0
        return float(this) + (lv * full if (lv and full) else 0.0)

    def _per_life_unit(self):
        """How many pixels one life is drawn with -- so 3 lives do not read as 12."""
        try:
            counts = sorted({h.get(self.lives, 0) for h in self.hist if h.get(self.lives, 0)})
            if len(counts) >= 2:
                d = counts[1] - counts[0]
                return d if d > 0 else 1
        except Exception:
            pass
        return 1

    # ---- plumbing ----------------------------------------------------------------------------------------------
    def _band(self, g):
        a = np.asarray(g)
        if a.ndim == 3:
            a = a[0]
        return a[self.lo:self.hi] if a.shape[0] > (self.hi - self.lo) else a

    def _hist(self, g):
        try:
            b = self._band(g)
            v, c = np.unique(b, return_counts=True)
            return {int(x): int(y) for x, y in zip(v, c)}
        except Exception:
            return {}

    # ---- cadence ------------------------------------------------------------------------------------------------
    REPORT_FRACTION = 0.25            # speak ~4x per life: often enough to steer inside one, rare enough to read
    REPORT_MIN = 5                    # never spam: below this the stream stops being evidence and becomes noise
    REPORT_MAX = 60                   # and never go quiet: an unmeasurable life must not mean an unmeasured model

    def report_interval(self):
        """How often a self-report should land, in ACTIONS, measured off THIS game's life.

        The interval was hardcoded at 30. A life on ls20 is 42, so 30 happened to be reasonable -- by luck. A life is
        a property of the GAME, not of the code: at 200 actions per life a fixed 30 reports six times per life and
        drowns the stream; at 12 it reports never, and the model is mute for the whole life it was meant to inform.
        The same defect as pricing a carving on a lifetime hit-rate, and the same fix -- measure it, do not choose it.

        A fraction, bounded both ways:
          - the FLOOR stops the stream degrading into noise on a very short life;
          - the CEILING is the interesting one. If the meter never drains, or there is no meter, or a life is
            effectively unbounded, `one_life()` is None or enormous -- and a fraction of infinity is silence. An
            unmeasurable life must not produce an unmeasured model, so the cadence falls back to the cap and the
            agent keeps reporting regardless.
        """
        life = self.one_life()
        if not life or life <= 0:
            return self.REPORT_MAX                     # no life measured yet -> speak at the cap, not never
        n = int(life * self.REPORT_FRACTION)
        return max(self.REPORT_MIN, min(self.REPORT_MAX, n))

    def actions_fraction(self, frac, lo=2, hi=None, default=None):
        """Any budget denominated in ACTIONS must be a FRACTION OF A LIFE, not a number somebody liked.

        Audited against the measured 42-action life, every action-denominated constant in this tree was chosen:

            MINT_PROBE_BUDGET  24  =  57% of a life   -- under a comment reading "a probe, not a campaign"
            _goto cap          40  =  95%             -- one navigation call may spend a whole life
            epoch DEFAULT_CAP 120  = 286%             -- the artificial mortality is 3x the real one
            max_depth          40  =  95%             -- planning 40 steps ahead when you have 42

        None of them are wrong by a little. They are wrong by the same amount as the thing they are budgeting, and
        they are wrong on a board that publishes its own life on the bar every single frame. A constant in actions is
        a claim about how much of a life something deserves -- so it has to be priced in lives, or it is not a budget,
        it is a wish.

        `hi` defaults to one life: nothing that spends actions may exceed the life it spends them from.
        """
        life = self.one_life()
        if not life or life <= 0:
            return default if default is not None else max(lo, int(20 * frac))
        cap = hi if hi is not None else life
        return int(max(lo, min(cap, round(life * frac))))

    def report(self):
        return {"meter": self.meter, "lives_colour": self.lives, "lives_left": self.lives_left(),
                "report_interval": self.report_interval(),
                "bar_actions_now": self.bar_actions(), "one_life_is": self.one_life(),
                "actions_left": self.actions_left(), "refills": self.refills, "obs": self.obs}


def get(adapter, emit=None):
    """One model per adapter. The whole point is that everyone reads the SAME one."""
    m = getattr(adapter, "_budget_model", None)
    if m is None:
        m = adapter._budget_model = BudgetModel(emit=emit)
    elif emit is not None and m.emit is None:
        m.emit = emit
    return m

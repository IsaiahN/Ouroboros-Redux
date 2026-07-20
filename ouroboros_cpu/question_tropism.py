"""
question_tropism.py  --  growth-toward-discrimination for the composer's generated win-questions.

The grammar (_win_predicate_lib) GENERATES candidate win-questions from the frame (relation-templates instantiated on
whatever objects are present). The current induction is PASSIVE: it waits to observe a win, composes every predicate that
transitioned violated->satisfied, then needs a SECOND win to prune coincidences.

This adds the TROPISM -- the ranking half of the 20-questions loop: order the generated questions by how much each one
DISCRIMINATES the win (mutual-information between "predicate satisfied" and "is-win-frame"), so the most informative
question is identified from the FIRST win instead of waiting for re-confirmation. This is "sort by most useful" /
binary-search-over-hypothesis-space: the question worth the most bits is asked first.

NOT the active-probing half. Active probing (act to generate the discriminating frame) needs the forward model to predict
each probe's outcome -- currently dormant. This is passive ranking of already-observed questions: the growth-toward step
without the tropic gradient yet. It is the falsifiable unit: does ranking-by-information-gain pin the answer in fewer
observations than passive induction?

Observe-capable (OURO_TROPISM = off|observe|active). Judged on observations-to-answer vs the passive baseline.
"""
from __future__ import annotations
import os, math

MODE = os.environ.get("OURO_TROPISM", "active").strip().lower()


def _satisfied(v):
    """A predicate value (holds, total) is 'satisfied' when holds == total > 0."""
    if v is None:
        return None
    holds, total = v
    if total <= 0:
        return None
    return holds >= total


def discrimination(seq, win_mask):
    """Mutual-information-style score per question: how cleanly does 'satisfied' track 'is-win-frame'?
    seq: list of {name: (holds,total)} over the ring. win_mask: list of bool, True where that frame is a win/satisfied
    end-state. Returns {name: score in [0,1]} -- 1.0 = satisfied EXACTLY at win frames and violated elsewhere (max bits).
    """
    names = set().union(*[set(s.keys()) for s in seq]) if seq else set()
    out = {}
    n = len(seq)
    if n == 0:
        return out
    for name in names:
        # 2x2 contingency: (satisfied?, win?) -- count only frames where the predicate is defined
        a = b = c = d = 0   # a: sat&win  b: sat&~win  c: ~sat&win  d: ~sat&~win
        defined = 0
        for i, s in enumerate(seq):
            sat = _satisfied(s.get(name))
            if sat is None:
                continue
            defined += 1
            win = bool(win_mask[i])
            if sat and win: a += 1
            elif sat and not win: b += 1
            elif (not sat) and win: c += 1
            else: d += 1
        if defined < 2:
            out[name] = 0.0
            continue
        # normalized mutual information between (satisfied) and (win)
        tot = a + b + c + d
        def _mi():
            mi = 0.0
            rows = [(a + b), (c + d)]      # satisfied, not-satisfied
            cols = [(a + c), (b + d)]      # win, not-win
            cells = [((a, 0, 0)), (b, 0, 1), (c, 1, 0), (d, 1, 1)]
            for cnt, r, cc in cells:
                if cnt == 0: continue
                pxy = cnt / tot
                px = rows[r] / tot
                py = cols[cc] / tot
                if px > 0 and py > 0:
                    mi += pxy * math.log2(pxy / (px * py))
            # normalize by min entropy so a perfect discriminator scores ~1.0
            def _H(ps):
                return -sum(p * math.log2(p) for p in ps if p > 0)
            hnorm = min(_H([rows[0] / tot, rows[1] / tot]), _H([cols[0] / tot, cols[1] / tot]))
            return (mi / hnorm) if hnorm > 1e-9 else 0.0
        out[name] = max(0.0, _mi())
    return out


def rank_questions(seq, win_mask):
    """Return the generated win-questions ordered by discrimination (most-informative first) -- the tropic ordering."""
    d = discrimination(seq, win_mask)
    return sorted(d.items(), key=lambda kv: -kv[1])


def top_answer(seq, win_mask, margin=0.15):
    """The composed answer from ranking alone: the top question IF it clears the runner-up by `margin` (a confident
    single-observation pin). Returns (name, score, decisive: bool). If no clear winner, decisive=False (stay in spread)."""
    r = rank_questions(seq, win_mask)
    if not r:
        return (None, 0.0, False)
    if len(r) == 1:
        return (r[0][0], r[0][1], r[0][1] > 0.5)
    (n0, s0), (n1, s1) = r[0], r[1]
    return (n0, s0, (s0 > 0.5 and (s0 - s1) >= margin))

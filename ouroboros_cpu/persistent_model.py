"""persistent_model.py -- Step 6: the cross-level component model that accumulates understanding and
supplies the recalibration signals. It is what coast.py's explanation_quality() callable is wired to.

Four commitments (the design, §11.322):

1. PERSISTENCE -- the typed-component model accumulates ACROSS levels and never resets. Level N's
   confirmed rules layer UNDER level N+1 (every level adds a mechanic on top of the old ones). Resetting
   between levels would re-pay for understanding already earned -- the elaboration trap in reverse.

2. STRUCTURAL vs QUANTITATIVE error (kept distinct, never collapsed):
     STRUCTURAL  -- the component is mis-TYPED or the grammar is wrong (a predicted constraint actually
                    responds; a self predicted to translate is actually located). Judged by DESCRIPTIVE
                    ALIGNMENT (does the asserted type still describe the behaviour?), NOT by residual size.
                    Fix = hypothesis revision (re-type).
     QUANTITATIVE-- the structure is RIGHT, a value is off (moved 3 not 2). Fix = controller/observer
                    correction. The Kalman/observer intuition lives HERE ONLY -- applying it to a
                    structural error just smooths over a wrong model.

3. DETECTION vs VERDICT -- prediction error is the DETECTOR (something is off); descriptive alignment is
   the VERDICT (which kind). A prediction error alone never condemns the structure.

4. PHASE-GATED -- prediction error is LOAD-BEARING in EXPLOIT (a surprise while exploiting a known rule
   means recalibrate) and EXPECTED/valuable in EXPLORE (surprises are how probing learns; recalibrating on
   every one makes the agent oscillate instead of discover).

Verified on SYNTHETIC scenarios constructed from these principles (NOT real games).
"""


class PersistentModel:
    def __init__(self, model_break_thresh=0.5, quant_tol=0.10):
        self.components = []          # accumulated typed components; NEVER reset
        self._index = {}              # (type, identity) -> component, for dedupe/layering
        self.level = 0
        self.model_break_thresh = model_break_thresh
        self.quant_tol = quant_tol

    # ---- 1. persistence: layer this level's components UNDER the accumulated model ----
    def absorb(self, level_components):
        self.level += 1
        added = 0
        for c in level_components:
            key = (c.get("type"), c.get("identity"))
            if key not in self._index:
                self.components.append(c); self._index[key] = c; added += 1
            else:
                # reinforce confidence of an already-known rule (it held again)
                prev = self._index[key]
                prev["confidence"] = round(min(1.0, prev.get("confidence", 0.5) + 0.05), 2)
        return added

    def known_types(self):
        return {c.get("type") for c in self.components}

    def vocabulary(self):
        return set(self._index.keys())

    # ---- the explanation-quality signal coast.py consumes (recalibration trigger) ----
    def explanation_quality(self, frame_components):
        """Fraction of the new frame's components the accumulated model can DESCRIBE in its vocabulary.
        1.0 = fully describable (coast). < model_break_thresh = a different game (from-scratch)."""
        if not frame_components:
            return 1.0
        known = 0
        for c in frame_components:
            if (c.get("type"), c.get("identity")) in self._index or c.get("type") in self.known_types():
                known += 1
        return known / len(frame_components)

    def is_model_break(self, frame_components):
        return self.explanation_quality(frame_components) < self.model_break_thresh

    # ---- 2+3+4. error classification: detection (prediction error) -> verdict (descriptive alignment) ----
    def classify_error(self, asserted_type, observed_type, predicted_value, observed_value, phase):
        """phase in {'exploit','explore'}. Returns the verdict + whether to recalibrate + the fix locus."""
        # DETECTION (prediction error): is anything off at all?
        denom = max(1.0, abs(float(predicted_value)))
        quant_err = abs(float(predicted_value) - float(observed_value)) / denom
        type_mismatch = (asserted_type != observed_type)
        detected = type_mismatch or (quant_err > self.quant_tol)

        # PHASE GATE: in EXPLORE, prediction error is expected -- do NOT recalibrate (no oscillation)
        if phase == "explore":
            return dict(detected=detected, verdict="expected", recalibrate=False,
                        quant_err=round(quant_err, 3),
                        detail="exploring: surprise is information, not a model fault")

        # EXPLOIT: prediction error is load-bearing
        if not detected:
            return dict(detected=False, verdict="ok", recalibrate=False, quant_err=round(quant_err, 3))

        # VERDICT by DESCRIPTIVE ALIGNMENT (not residual size):
        if type_mismatch:
            return dict(detected=True, verdict="structural", recalibrate=True,
                        fix="hypothesis revision (re-type the component / revise grammar)",
                        quant_err=round(quant_err, 3),
                        detail=f"asserted '{asserted_type}' but behaves as '{observed_type}' -- descriptive misalignment")
        # right type, value off -> QUANTITATIVE (Kalman/observer intuition lives ONLY here)
        return dict(detected=True, verdict="quantitative", recalibrate=True,
                    fix="controller/observer correction (Kalman) -- structure is right, value is off",
                    quant_err=round(quant_err, 3))

    # ---- articulation (the halt-invariant: explain the accumulated model) ----
    def explain(self):
        if not self.components:
            return "persistent model: empty (level 0)"
        lines = [f"persistent model after {self.level} level(s), {len(self.components)} components:"]
        for c in self.components:
            lines.append(f"  {c.get('type')}({c.get('identity')}) conf={c.get('confidence')}")
        return "\n".join(lines)

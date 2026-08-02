"""nexus.proposer.fluent -- the FLUENT proposer: a tiny LM that aims the proposal distribution.

Same role as EnumerationProposer, but the candidates come from a small transformer trained to be
fluent in Γ (esp32-ai's model.py, unchanged) rather than from raw enumeration. This is the
grammar-fluent proposer of `claude/DESIGN_the_grammar_fluent_proposer.md`, retargeted from the
objective grammar to the EVALUABLE predicate DSL so it plugs straight into the Nexus loop.

Stage 1 only (grammatical fluency): it emits well-typed predicates cheaply and locally, removing
the API-rate ceiling on population size. It PROPOSES, never scores, never promotes. Its own loss is
a training signal, not an acceptance metric -- RLVR (the ground) decides every candidate.
"""
from __future__ import annotations
import math, random
from typing import List, Dict, Optional
import numpy as np
import torch
from .model import Config, TinyLM
from ..kernel import Predicate, enumerate_predicates, serialize, parse, is_valid, vocab_for


class FluentProposer:
    def __init__(self, palette, max_size: int = 2, seq_len: int = 16):
        self.palette = list(palette)
        self.itos = vocab_for(palette)
        self.stoi = {t: i for i, t in enumerate(self.itos)}
        self.seq_len = seq_len
        self.model: Optional[TinyLM] = None

    # ---- corpus + training (reuses the esp32-ai TinyLM unchanged) ------------------------------
    def _stream(self, preds: List[Predicate]) -> np.ndarray:
        bos, eos = self.stoi["<bos>"], self.stoi["<eos>"]
        ids = []
        for p in preds:
            ids.append(bos); ids += [self.stoi[t] for t in serialize(p)]; ids.append(eos)
        return np.array(ids, dtype=np.int64)

    def train(self, max_size: int = 2, steps: int = 700, seed: int = 0, log=lambda *_: None):
        torch.manual_seed(seed)
        preds = enumerate_predicates(self.palette, max_size)
        data = torch.from_numpy(self._stream(preds))
        cfg = Config(arm="baseline", vocab_size=len(self.itos), d_model=64, n_layers=2,
                     n_heads=4, ffn_hidden=128, seq_len=self.seq_len)
        m = TinyLM(cfg); m.train()
        opt = torch.optim.AdamW(m.parameters(), lr=1e-3, betas=(0.9, 0.95), weight_decay=0.1)
        sl, N = self.seq_len, len(data)
        g = torch.Generator().manual_seed(seed)
        for step in range(steps):
            ix = torch.randint(0, N - sl - 1, (64,), generator=g)
            x = torch.stack([data[i:i + sl] for i in ix])
            y = torch.stack([data[i + 1:i + 1 + sl] for i in ix])
            _, loss = m(x, y)
            opt.zero_grad(set_to_none=True); loss.backward()
            torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0); opt.step()
            if step % 200 == 0:
                log(f"  fluent step {step} loss {loss.item():.3f}")
        m.eval(); self.model = m
        return self

    # ---- proposal: sample from <bos>, decode, keep the well-typed ones -------------------------
    def _decode(self, row) -> List[str]:
        bos, eos = self.stoi["<bos>"], self.stoi["<eos>"]
        out = []
        for t in row:
            if t == bos: continue
            if t == eos: break
            out.append(self.itos[t])
        return out

    def sample(self, n: int, temperature: float = 1.0) -> List[Predicate]:
        assert self.model is not None, "train() first"
        seed = torch.full((n, 1), self.stoi["<bos>"], dtype=torch.long)
        with torch.no_grad():
            gen = self.model.generate(seed, max_new_tokens=self.seq_len, temperature=temperature, top_k=0)
        preds, seen = [], set()
        for row in gen.tolist():
            toks = self._decode(row[1:])
            if toks and is_valid(toks):
                p = parse(toks); key = str(p)
                if key not in seen:
                    seen.add(key); preds.append(p)
        return preds

    def propose(self, seeds: Dict[Predicate, float], role, k: int, rng, oversample: int = 6) -> List[Predicate]:
        """Same interface as EnumerationProposer. Oversample and filter by the kernel's type-check
        (free), then keep k. Seeds bias nothing here yet -- conditional seeding is the next wire
        (design note: train on (verified term -> generalizations) pairs)."""
        cand = self.sample(k * oversample, temperature=1.0)
        rng.shuffle(cand)
        return cand[:k]

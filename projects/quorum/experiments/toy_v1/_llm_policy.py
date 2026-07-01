"""Real LLM backend: single batched forward pass + logit projection.

Imported only when the ``llm`` extra is installed. Unit tests use
``MockPolicy`` from ``toy_v1.policy``; this module is exercised by the
``smoke`` test and by the CLI in ``toy_v1.main``.

I3 + I4 in code:

- ``step`` makes ONE call to ``self.model(**enc)``. The batch dimension
  is the population dimension.
- ``step`` never calls ``self.model.generate``. The action is read out as
  a logit projection onto the action-vocab token IDs at the last position
  of each sequence (single-pass classification, SALSA-style).
"""

from __future__ import annotations

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from toy_v1.actions import LABELS


class LLMPolicy:
    """Wrap an HF causal LM as a single-pass action policy."""

    def __init__(self, model_name: str) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tok = AutoTokenizer.from_pretrained(model_name)
        # Decoder-only LMs need LEFT padding so the last position is real
        # for every sequence in the batch.
        self.tok.padding_side = "left"
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)
        self.model.eval()
        # Resolve the action labels to single token IDs. Most BPE tokenizers
        # emit a leading space for the first generated token, so we encode
        # ``" S"`` rather than ``"S"``. The asserts guard I4: the readout is
        # one token per action.
        self.action_token_ids: list[int] = []
        for label in LABELS:
            ids = self.tok.encode(" " + label, add_special_tokens=False)
            if len(ids) != 1:
                raise RuntimeError(
                    f"Action {label!r} tokenizes to {ids} (not a single token). "
                    f"Pick a tokenizer where action labels are single tokens."
                )
            self.action_token_ids.append(ids[0])
        # Instrumented counters (mirror MockPolicy for symmetry in tests).
        self.forward_call_count = 0
        self.generate_call_count = 0  # always 0; we never call .generate()

    @torch.no_grad()
    def step(self, prompts: list[str], rng: np.random.Generator) -> list[str]:
        enc = self.tok(prompts, padding=True, return_tensors="pt").to(self.device)
        # >>> ONE forward pass for the entire population (I3). <<<
        out = self.model(**enc)
        self.forward_call_count += 1
        # With LEFT padding, the last position is real for every sequence.
        last_logits = out.logits[:, -1, :]                       # [B, V]
        action_logits = last_logits[:, self.action_token_ids]     # [B, |LABELS|]
        probs = torch.softmax(action_logits, dim=-1).cpu().numpy()
        # Sample with the caller's RNG (I8 — replay determinism).
        actions: list[str] = []
        for p in probs:
            choice = rng.choice(len(LABELS), p=p / p.sum())
            actions.append(LABELS[choice])
        return actions

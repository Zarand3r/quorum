"""Real LLM backend for Slice 0 — vLLM + single batched forward pass.

Imported only when the ``[llm]`` extra is installed. Everywhere else uses
``UniformRandomPolicy`` from ``policy.py``; this module is exercised by the
smoke test in ``tests/integration/test_llm_policy_smoke.py`` (opt-in via
the ``@pytest.mark.llm`` marker) and by ``main.py --policy llm``.

I3 + I4 in code:

- ``step`` calls ``self.model.forward(...)`` ONCE per invocation. The batch
  dimension is the population dimension.
- ``step`` never calls ``self.model.generate(...)``. Actions are read via
  logit projection onto the 5-token action vocab at the last position.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

from slice0.actions import LABELS
from slice0.policy import Observation


class LLMPolicy:
    """Wrap an HF causal LM as a single-pass action policy.

    Uses raw HuggingFace transformers with ``.forward()`` + logit projection.
    vLLM's engine is optimized for generation and doesn't naturally expose a
    "prefill only, return last-token logits" path per batch — so for Slice 0
    we do the batched forward through transformers directly. The vLLM
    upgrade lands at M2 when Tier-2 reflection needs true generation.
    """

    def __init__(
        self,
        model_name: str,
        device: str | None = None,
        dtype: str = "float16",
    ) -> None:
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name = model_name
        torch_dtype = getattr(torch, dtype)

        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.tok.padding_side = "left"  # last position is real for every seq
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token

        # Use plain .to(device) rather than device_map=, which now requires
        # the accelerate package. For a single-model inference case we don't
        # need the sharding machinery; the extra dependency isn't worth it.
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=torch_dtype,
        ).to(self.device)
        self.model.eval()

        # Resolve each single-letter label to a single token id (with a leading
        # space, matching the tokenizer's post-"Answer:" continuation).
        self.action_token_ids: list[int] = []
        for label in LABELS:
            ids = self.tok.encode(" " + label, add_special_tokens=False)
            if len(ids) != 1:
                # Try the letter alone as a fallback for tokenizers that
                # don't use the leading-space convention.
                ids2 = self.tok.encode(label, add_special_tokens=False)
                if len(ids2) == 1:
                    self.action_token_ids.append(ids2[0])
                    continue
                raise RuntimeError(
                    f"Action {label!r} tokenizes to {ids} (space) or {ids2} "
                    f"(no space) — not a single token. Pick a tokenizer where "
                    f"all of {LABELS} are single tokens."
                )
            self.action_token_ids.append(ids[0])

        # Instrumented counters — mirror UniformRandomPolicy.
        self.forward_call_count = 0
        self.generate_call_count = 0  # stays 0 by construction

    @torch.no_grad()
    def step(
        self,
        prompts: list[str],
        rng: np.random.Generator,
        observations: list[Observation] | None = None,  # ignored; LLM reads prompt
    ) -> list[str]:
        enc = self.tok(prompts, padding=True, return_tensors="pt").to(self.device)
        # >>> ONE forward pass for the entire population (I3, I4). <<<
        out = self.model(**enc, use_cache=False)
        self.forward_call_count += 1
        last_logits = out.logits[:, -1, :]                            # [B, V]
        action_logits = last_logits[:, self.action_token_ids]         # [B, |LABELS|]
        probs = F.softmax(action_logits.float(), dim=-1).cpu().numpy()
        # Sample with the caller's RNG (I8).
        actions: list[str] = []
        for p in probs:
            p_sum = p.sum()
            p = p / p_sum if p_sum > 0 else np.ones_like(p) / len(LABELS)
            choice = rng.choice(len(LABELS), p=p)
            actions.append(LABELS[choice])
        return actions

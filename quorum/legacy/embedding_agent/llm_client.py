"""
LEGACY — OpenAI LLM client used by the pre-refinement sentiment pipeline.

This module is reusable by the refined event-extraction stage in PLAN.md
section 4.4; promote pieces of it out of ``legacy/`` when wiring Slice 0.
Open issues to address on promotion:
- I4: persist per-call cost to a cost-meter table instead of logging only.
- m12 in the review: use ``response_format={"type": "json_object"}`` and
  pydantic schemas instead of regex JSON extraction.
"""

import time
import logging
from collections import deque
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import openai
from openai import OpenAI

from ...config.settings import APIConfig


logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Structured response from LLM."""
    content: str
    model: str
    tokens_used: int
    cost_estimate: float
    timestamp: datetime
    success: bool = True
    error_message: Optional[str] = None


class RateLimiter:
    """Sliding-window rate limiter for API calls."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: deque = deque()

    def wait_if_needed(self) -> None:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=1)
        while self.requests and self.requests[0] < window_start:
            self.requests.popleft()

        if len(self.requests) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.requests[0]).total_seconds()
            if sleep_time > 0:
                logger.info("Rate limiting: sleeping for %.1f seconds", sleep_time)
                time.sleep(sleep_time)

        self.requests.append(datetime.now(timezone.utc))


# Per-1K-token cost estimates. Update when the LLM provider changes pricing.
# I4 (PLAN.md): the per-call cost computed here must be persisted to a
# cost-meter table when storage lands; for now we only log.
DEFAULT_TOKEN_COSTS: Dict[str, Dict[str, float]] = {
    'gpt-4':         {'input': 0.03,  'output': 0.06},
    'gpt-4-turbo':   {'input': 0.01,  'output': 0.03},
    'gpt-3.5-turbo': {'input': 0.001, 'output': 0.002},
}


class LLMClient:
    """Client for interacting with OpenAI's LLM API."""

    def __init__(self, config: APIConfig):
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
        self.rate_limiter = RateLimiter(config.requests_per_minute)
        self.token_costs = DEFAULT_TOKEN_COSTS

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        costs = self.token_costs.get(model, self.token_costs['gpt-4'])
        return (input_tokens / 1000) * costs['input'] + (output_tokens / 1000) * costs['output']

    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: int = 30,
    ) -> LLMResponse:
        # Use ``is None`` so callers passing 0 or "" don't get silently overridden.
        if model is None:
            model = self.config.openai_model
        if max_tokens is None:
            max_tokens = self.config.openai_max_tokens
        if temperature is None:
            temperature = self.config.openai_temperature

        self.rate_limiter.wait_if_needed()
        now_utc = datetime.now(timezone.utc)

        try:
            logger.info("Making LLM request to %s", model)
            start_time = time.monotonic()

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )

            elapsed = time.monotonic() - start_time
            content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            cost_estimate = self._estimate_cost(model, input_tokens, output_tokens)

            logger.info(
                "LLM request completed in %.2fs. Tokens: %d, Cost: $%.4f",
                elapsed, total_tokens, cost_estimate,
            )

            return LLMResponse(
                content=content,
                model=model,
                tokens_used=total_tokens,
                cost_estimate=cost_estimate,
                timestamp=now_utc,
                success=True,
            )

        except (openai.RateLimitError, openai.APITimeoutError, openai.APIError) as e:
            error_code = type(e).__name__
            logger.error("OpenAI %s: %s", error_code, e)
            return LLMResponse(
                content="",
                model=model,
                tokens_used=0,
                cost_estimate=0.0,
                timestamp=now_utc,
                success=False,
                error_message=f"{error_code}: {e}",
            )

    def test_connection(self) -> bool:
        try:
            response = self.generate_completion(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return response.success
        except Exception as e:  # noqa: BLE001 — connection probe is one place catch-all is OK
            logger.error("Connection test failed: %s", e)
            return False

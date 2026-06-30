"""
LEGACY — converts pre-refinement LLM market analysis into the 10-dimension
sentiment vector.

Refactored to drop the silent neutral-default fallback: on failure the
``SentimentEmbedding`` now carries empty dicts (not ``{dim: 0.0}`` for every
dimension), so a caller that ignores ``success`` cannot get a zero vector
that looks valid. See review M1 — PLAN.md I5 / constitution "No silent
fallback".
"""

import logging
import json
import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .llm_client import LLMClient
from .market_fetcher import MarketContext
from ...config.settings import AppConfig


logger = logging.getLogger(__name__)


@dataclass
class SentimentEmbedding:
    """Structured sentiment embedding with metadata.

    On failure, ``embeddings`` and ``confidence_scores`` are empty dicts —
    never ``{dim: 0.0}`` per the M1 fix. Callers must check ``success``
    before reading values.
    """
    date: datetime
    embeddings: Dict[str, float]
    confidence_scores: Dict[str, float]
    raw_analysis: str
    model_version: str
    success: bool = True
    error_message: Optional[str] = None


# Dimension descriptions used to prompt the LLM. Kept here rather than in
# settings.py because they are tightly coupled to the prompt format.
DIMENSION_DESCRIPTIONS: Dict[str, str] = {
    'tech_earnings_momentum':       'Technology sector earnings trends and momentum (positive = strong tech earnings, negative = weak tech earnings)',
    'AI_optimism':                  'Market sentiment around AI/ML developments and adoption (positive = AI optimism, negative = AI skepticism)',
    'interest_rate_expectations':   'Market expectations for interest rate changes (positive = rising rates expected, negative = falling rates expected)',
    'tariff_risk':                  'Concerns about trade tensions and tariff impacts (positive = low tariff risk, negative = high tariff risk)',
    'retail_investor_sentiment':    'Retail/individual investor mood and activity (positive = bullish retail sentiment, negative = bearish retail sentiment)',
    'institutional_caution':        'Large institutional investor risk appetite (positive = aggressive positioning, negative = defensive positioning)',
    'valuation_concerns':           'Market concerns about asset valuations (positive = valuations reasonable, negative = overvaluation concerns)',
    'macro_stability':              'Overall macroeconomic stability and predictability (positive = stable macro environment, negative = macro uncertainty)',
    'market_liquidity':             'Market liquidity conditions and ease of trading (positive = high liquidity, negative = liquidity concerns)',
    'crowded_trades_risk':          'Risk of overcrowded positions unwinding (positive = low crowding risk, negative = high crowding risk)',
}


def _failure(
    date: datetime,
    model: str,
    reason: str,
) -> SentimentEmbedding:
    """Construct a failure SentimentEmbedding with empty dicts (no neutral defaults)."""
    return SentimentEmbedding(
        date=date,
        embeddings={},
        confidence_scores={},
        raw_analysis="",
        model_version=model,
        success=False,
        error_message=reason,
    )


class EmbeddingParser:
    """Converts a MarketContext into a structured SentimentEmbedding."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.llm_client = LLMClient(config.api)
        self.embedding_dimensions = config.market.embedding_dimensions

    def _create_embedding_extraction_prompt(self, market_context: MarketContext) -> str:
        prompt = (
            "You are a quantitative financial analyst specializing in sentiment "
            "analysis. Based on the comprehensive market analysis provided, "
            "extract sentiment scores for specific market dimensions.\n\n"
            "**MARKET ANALYSIS TO ANALYZE:**\n"
            f"{market_context.market_sentiment_raw}\n\n"
            "**MARKET DATA CONTEXT:**\n"
        )

        for symbol, data in market_context.market_data.items():
            if 'error' in data:
                continue
            prompt += (
                f"- {symbol}: {data.get('change_percent', 0):+.2f}% "
                f"(Volume: {data.get('volume', 0):,})\n"
            )

        prompt += (
            f"\n**NEWS SUMMARY:**\n{market_context.news_summary}\n\n"
            "**EMBEDDING DIMENSIONS TO SCORE:**\n\n"
            "For each dimension below, provide a sentiment score from -1.0 to +1.0 "
            "(-1.0 strongly negative, 0.0 neutral, +1.0 strongly positive).\n\n"
        )

        for dim, desc in DIMENSION_DESCRIPTIONS.items():
            prompt += f"**{dim}**: {desc}\n"

        # OUTPUT_FORMAT block produced from the configured dimensions, so the
        # schema is always in sync.
        empty_block = ",\n    ".join(f'"{d}": 0.0' for d in self.embedding_dimensions)
        prompt += (
            "\n**OUTPUT FORMAT:**\n"
            "Respond with a JSON object containing the keys "
            "``embeddings`` (sentiment, in [-1.0, 1.0]), "
            "``confidence_scores`` (in [0.0, 1.0]), and "
            "``reasoning`` (short text per dimension).\n\n"
            "```json\n"
            "{\n"
            f'  "embeddings": {{\n    {empty_block}\n  }},\n'
            f'  "confidence_scores": {{\n    {empty_block}\n  }},\n'
            f'  "reasoning": {{\n    {empty_block}\n  }}\n'
            "}\n```\n\n"
            "Return ONLY the JSON object, no additional text.\n"
        )
        return prompt

    def _parse_llm_embedding_response(
        self,
        response_content: str,
    ) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, str]]:
        """Parse the JSON in the LLM response.

        TODO (review m12): use ``response_format={"type": "json_object"}`` on
        the API call + a pydantic schema instead of regex extraction.
        """
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in LLM response")
            json_str = json_match.group(0)

        parsed = json.loads(json_str)

        embeddings_raw = parsed.get('embeddings', {})
        confidence_raw = parsed.get('confidence_scores', {})
        reasoning = parsed.get('reasoning', {})

        clean_embeddings: Dict[str, float] = {}
        clean_confidence: Dict[str, float] = {}
        for dim in self.embedding_dimensions:
            if dim in embeddings_raw:
                value = max(-1.0, min(1.0, float(embeddings_raw[dim])))
                clean_embeddings[dim] = value
            else:
                # Missing dimension is a schema violation, not a neutral default.
                raise ValueError(f"Missing embedding dimension in response: {dim}")

            if dim in confidence_raw:
                clean_confidence[dim] = max(0.0, min(1.0, float(confidence_raw[dim])))
            else:
                raise ValueError(f"Missing confidence score in response: {dim}")

        return clean_embeddings, clean_confidence, reasoning

    def extract_embeddings(self, market_context: MarketContext) -> SentimentEmbedding:
        model = self.config.api.openai_model
        now_utc = market_context.date if isinstance(market_context.date, datetime) else datetime.now(timezone.utc)

        if not market_context.success:
            return _failure(now_utc, model, f"Market context failed: {market_context.error_message}")

        logger.info("Extracting sentiment embeddings for %s", now_utc.isoformat())

        try:
            prompt = self._create_embedding_extraction_prompt(market_context)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a quantitative financial analyst who converts "
                        "market analysis into precise numerical sentiment scores. "
                        "You always respond with valid JSON in the exact format requested."
                    ),
                },
                {"role": "user", "content": prompt},
            ]
            llm_response = self.llm_client.generate_completion(
                messages=messages,
                temperature=0.1,
            )

            if not llm_response.success:
                return _failure(now_utc, model, f"LLM request failed: {llm_response.error_message}")

            embeddings, confidence_scores, _reasoning = self._parse_llm_embedding_response(
                llm_response.content
            )
            logger.info("Successfully extracted %d sentiment dimensions", len(embeddings))

            return SentimentEmbedding(
                date=now_utc,
                embeddings=embeddings,
                confidence_scores=confidence_scores,
                raw_analysis=llm_response.content,
                model_version=model,
                success=True,
            )

        except (ValueError, json.JSONDecodeError) as e:
            logger.error("Embedding parse failure: %s", e)
            return _failure(now_utc, model, f"schema_invalid: {e}")
        except Exception as e:  # noqa: BLE001 — surface as failure rather than crash the cron
            logger.exception("Unexpected error extracting embeddings")
            return _failure(now_utc, model, f"unexpected_error: {e}")

    def validate_embedding(self, embedding: SentimentEmbedding) -> bool:
        if not embedding.success:
            return False

        for dim in self.embedding_dimensions:
            value = embedding.embeddings.get(dim)
            confidence = embedding.confidence_scores.get(dim)
            if value is None:
                logger.error("Missing embedding dimension: %s", dim)
                return False
            if confidence is None:
                logger.error("Missing confidence score for dimension: %s", dim)
                return False
            if not isinstance(value, (int, float)) or not -1.0 <= value <= 1.0:
                logger.error("Embedding value invalid for %s: %r", dim, value)
                return False
            if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
                logger.error("Confidence score invalid for %s: %r", dim, confidence)
                return False

        return True

    def get_embedding_summary(self, embedding: SentimentEmbedding) -> str:
        if not embedding.success:
            return f"Embedding extraction failed: {embedding.error_message}"

        summary = (
            f"Sentiment Embedding for {embedding.date.isoformat()}\n"
            f"Model: {embedding.model_version}\n\n"
        )
        sorted_dims = sorted(
            embedding.embeddings.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )
        for dim, value in sorted_dims:
            confidence = embedding.confidence_scores.get(dim, 0.0)
            label = "positive" if value > 0 else "negative" if value < 0 else "neutral"
            summary += f"  {dim}: {value:+.2f} ({label}, confidence: {confidence:.2f})\n"
        return summary

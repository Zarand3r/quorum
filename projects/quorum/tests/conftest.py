"""Shared pytest fixtures.

Scoped to the legacy embedding pipeline (the new ``quorum.scoring`` invariant
tests are pure and need no fixtures).
"""

from datetime import datetime, timezone

import pytest

from quorum.config.settings import (
    AppConfig,
    APIConfig,
    DatabaseConfig,
    MarketConfig,
)
from quorum.legacy.embedding_agent.llm_client import LLMResponse
from quorum.legacy.embedding_agent.market_fetcher import MarketContext
from quorum.legacy.embedding_agent.embedding_parser import SentimentEmbedding


@pytest.fixture
def mock_api_config() -> APIConfig:
    return APIConfig(
        openai_api_key="test-api-key",
        openai_model="gpt-4",
        openai_max_tokens=2000,
        openai_temperature=0.3,
        requests_per_minute=60,
    )


@pytest.fixture
def mock_app_config(mock_api_config: APIConfig) -> AppConfig:
    return AppConfig(
        api=mock_api_config,
        database=DatabaseConfig(),
        market=MarketConfig(),
        log_level="DEBUG",
        log_file="test.log",
        daily_run_time="09:00",
    )


@pytest.fixture
def sample_market_data() -> dict:
    return {
        'SPY': {
            'current_price': 450.25,
            'previous_price': 448.10,
            'change': 2.15,
            'change_percent': 0.48,
            'volume': 85_000_000,
        }
    }


@pytest.fixture
def sample_llm_response() -> LLMResponse:
    return LLMResponse(
        content="Market analysis shows mixed sentiment with tech optimism...",
        model="gpt-4",
        tokens_used=1500,
        cost_estimate=0.045,
        timestamp=datetime.now(timezone.utc),
        success=True,
    )


@pytest.fixture
def sample_market_context(sample_market_data) -> MarketContext:
    return MarketContext(
        date=datetime.now(timezone.utc),
        market_data=sample_market_data,
        news_summary="Tech stocks show strength amid AI optimism.",
        key_events=["Tech earnings exceed expectations"],
        market_sentiment_raw="Overall market sentiment is cautiously optimistic...",
        data_sources=["yfinance"],
        success=True,
    )


@pytest.fixture
def sample_sentiment_embedding() -> SentimentEmbedding:
    embeddings = {
        'tech_earnings_momentum':     0.75,
        'AI_optimism':                0.85,
        'interest_rate_expectations': 0.45,
        'tariff_risk':               -0.25,
        'retail_investor_sentiment':  0.65,
        'institutional_caution':     -0.35,
        'valuation_concerns':        -0.55,
        'macro_stability':            0.35,
        'market_liquidity':           0.25,
        'crowded_trades_risk':       -0.45,
    }
    confidence_scores = {dim: 0.8 for dim in embeddings}
    return SentimentEmbedding(
        date=datetime.now(timezone.utc),
        embeddings=embeddings,
        confidence_scores=confidence_scores,
        raw_analysis='{"embeddings": {...}}',
        model_version="gpt-4",
        success=True,
    )


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Ensure tests run with deterministic env vars regardless of host shell."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

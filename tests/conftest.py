"""
Simplified pytest configuration and shared fixtures.
"""

import pytest
import os
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

from pelosi.config.settings import AppConfig, APIConfig, DatabaseConfig, MarketConfig
from pelosi.embedding_agent.llm_client import LLMResponse
from pelosi.embedding_agent.market_fetcher import MarketContext
from pelosi.embedding_agent.embedding_parser import SentimentEmbedding


@pytest.fixture
def mock_api_config():
    """Mock API configuration for testing."""
    return APIConfig(
        openai_api_key="test-api-key",
        openai_model="gpt-4",
        openai_max_tokens=2000,
        openai_temperature=0.3,
        requests_per_minute=60
    )


@pytest.fixture
def mock_app_config(mock_api_config):
    """Mock complete application configuration."""
    return AppConfig(
        api=mock_api_config,
        database=DatabaseConfig(),
        market=MarketConfig(),
        log_level="DEBUG",
        log_file="test.log",
        daily_run_time="09:00"
    )


@pytest.fixture
def sample_market_data():
    """Sample market data for testing."""
    return {
        'SPY': {
            'current_price': 450.25,
            'previous_price': 448.10,
            'change': 2.15,
            'change_percent': 0.48,
            'volume': 85000000,
            'high_52w': 475.30,
            'low_52w': 380.50,
            'market_cap': 0,
            'pe_ratio': 22.5,
            'avg_volume': 80000000
        }
    }


@pytest.fixture
def sample_llm_response():
    """Sample LLM response for testing."""
    return LLMResponse(
        content="Market analysis shows mixed sentiment with tech optimism...",
        model="gpt-4",
        tokens_used=1500,
        cost_estimate=0.045,
        timestamp=datetime.now(),
        success=True
    )


@pytest.fixture
def sample_market_context(sample_market_data):
    """Sample market context for testing."""
    return MarketContext(
        date=datetime.now(),
        market_data=sample_market_data,
        news_summary="Tech stocks show strength amid AI optimism.",
        key_events=["Tech earnings exceed expectations"],
        market_sentiment_raw="Overall market sentiment is cautiously optimistic...",
        data_sources=["yfinance", "financial_news"],
        success=True
    )


@pytest.fixture
def sample_sentiment_embedding():
    """Sample sentiment embedding for testing."""
    embeddings = {
        'tech_earnings_momentum': 0.75,
        'AI_optimism': 0.85,
        'interest_rate_expectations': 0.45,
        'tariff_risk': -0.25,
        'retail_investor_sentiment': 0.65,
        'institutional_caution': -0.35,
        'valuation_concerns': -0.55,
        'macro_stability': 0.35,
        'market_liquidity': 0.25,
        'crowded_trades_risk': -0.45
    }
    confidence_scores = {dim: 0.8 for dim in embeddings.keys()}
    
    return SentimentEmbedding(
        date=datetime.now(),
        embeddings=embeddings,
        confidence_scores=confidence_scores,
        raw_analysis='{"embeddings": {...}}',
        model_version="gpt-4",
        success=True
    )


# Environment setup for tests
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


# Async test utilities
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close() 
"""Integration tests for the legacy market-fetch pipeline.

These exercise multiple components together with mocked external services
(OpenAI, yfinance) — no live network or LLM calls.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from quorum.legacy.embedding_agent.embedding_parser import EmbeddingParser
from quorum.legacy.embedding_agent.market_fetcher import MarketContextFetcher


@pytest.mark.integration
class TestPipelineIntegration:
    @pytest.mark.asyncio
    @patch('quorum.legacy.embedding_agent.market_fetcher.MarketDataCollector')
    @patch('quorum.legacy.embedding_agent.llm_client.OpenAI')
    async def test_basic_pipeline(
        self,
        mock_openai_class,
        mock_collector_class,
        mock_app_config,
        sample_market_data,
    ):
        # First LLM call: market analysis.
        analysis_response = Mock()
        analysis_response.choices = [Mock()]
        analysis_response.choices[0].message.content = "Market shows positive sentiment"
        analysis_response.usage.prompt_tokens = 100
        analysis_response.usage.completion_tokens = 50
        analysis_response.usage.total_tokens = 150

        # Second LLM call: embedding extraction (full 10-dim JSON).
        embedding_response = Mock()
        embedding_response.choices = [Mock()]
        embedding_response.choices[0].message.content = '''```json
{
  "embeddings": {
    "tech_earnings_momentum": 0.5,
    "AI_optimism": 0.7,
    "interest_rate_expectations": 0.3,
    "tariff_risk": -0.2,
    "retail_investor_sentiment": 0.6,
    "institutional_caution": -0.3,
    "valuation_concerns": -0.4,
    "macro_stability": 0.4,
    "market_liquidity": 0.3,
    "crowded_trades_risk": -0.3
  },
  "confidence_scores": {
    "tech_earnings_momentum": 0.8,
    "AI_optimism": 0.9,
    "interest_rate_expectations": 0.7,
    "tariff_risk": 0.6,
    "retail_investor_sentiment": 0.8,
    "institutional_caution": 0.7,
    "valuation_concerns": 0.8,
    "macro_stability": 0.6,
    "market_liquidity": 0.7,
    "crowded_trades_risk": 0.8
  },
  "reasoning": {
    "tech_earnings_momentum": "x",
    "AI_optimism": "x",
    "interest_rate_expectations": "x",
    "tariff_risk": "x",
    "retail_investor_sentiment": "x",
    "institutional_caution": "x",
    "valuation_concerns": "x",
    "macro_stability": "x",
    "market_liquidity": "x",
    "crowded_trades_risk": "x"
  }
}
```'''
        embedding_response.usage.prompt_tokens = 200
        embedding_response.usage.completion_tokens = 100
        embedding_response.usage.total_tokens = 300

        mock_openai_client = Mock()
        mock_openai_class.return_value = mock_openai_client
        mock_openai_client.chat.completions.create.side_effect = [
            analysis_response,
            embedding_response,
        ]

        # Mock the data collector (synchronous after M3/M4 cleanup).
        mock_collector = Mock()
        mock_collector.get_market_data.return_value = sample_market_data
        mock_collector.get_financial_news.return_value = []
        mock_collector.get_economic_indicators.return_value = {}
        mock_collector_class.return_value = mock_collector

        market_fetcher = MarketContextFetcher(mock_app_config)
        embedding_parser = EmbeddingParser(mock_app_config)

        market_context = await market_fetcher.fetch_market_context()
        assert market_context.success is True

        sentiment_embedding = embedding_parser.extract_embeddings(market_context)
        assert sentiment_embedding.success is True
        assert len(sentiment_embedding.embeddings) == 10

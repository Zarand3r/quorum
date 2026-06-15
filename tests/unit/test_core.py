"""Unit tests for the legacy LLM market-fetch components."""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from quorum.legacy.embedding_agent.embedding_parser import EmbeddingParser
from quorum.legacy.embedding_agent.llm_client import LLMClient
from quorum.legacy.embedding_agent.market_fetcher import MarketContextFetcher


@pytest.mark.unit
class TestLLMClient:
    def test_llm_client_creation(self, mock_app_config):
        with patch('quorum.legacy.embedding_agent.llm_client.OpenAI'):
            client = LLMClient(mock_app_config.api)
            assert client.config == mock_app_config.api

    @patch('quorum.legacy.embedding_agent.llm_client.OpenAI')
    def test_successful_completion(self, mock_openai_class, mock_app_config):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_client.chat.completions.create.return_value = mock_response

        llm_client = LLMClient(mock_app_config.api)
        response = llm_client.generate_completion([{"role": "user", "content": "test"}])

        assert response.success is True
        assert response.content == "Test response"
        assert response.tokens_used == 150


@pytest.mark.unit
class TestMarketFetcher:
    def test_market_fetcher_creation(self, mock_app_config):
        with patch('quorum.legacy.embedding_agent.market_fetcher.LLMClient'):
            fetcher = MarketContextFetcher(mock_app_config)
            assert fetcher.config == mock_app_config

    @patch('yfinance.Ticker')
    def test_market_data_collection(self, mock_ticker_class, mock_app_config):
        mock_ticker = Mock()
        mock_ticker.history.return_value = pd.DataFrame({
            'Close': [450.0, 451.0],
            'Volume': [1_000_000, 1_100_000],
        })
        mock_ticker_class.return_value = mock_ticker

        with patch('quorum.legacy.embedding_agent.market_fetcher.LLMClient'):
            fetcher = MarketContextFetcher(mock_app_config)
            data = fetcher.data_collector.get_market_data(['SPY'])

            assert 'SPY' in data
            assert 'current_price' in data['SPY']
            assert data['SPY']['current_price'] == 451.0


@pytest.mark.unit
class TestEmbeddingParser:
    def test_embedding_parser_creation(self, mock_app_config):
        with patch('quorum.legacy.embedding_agent.embedding_parser.LLMClient'):
            parser = EmbeddingParser(mock_app_config)
            assert parser.config == mock_app_config

    def test_embedding_validation(self, mock_app_config, sample_sentiment_embedding):
        with patch('quorum.legacy.embedding_agent.embedding_parser.LLMClient'):
            parser = EmbeddingParser(mock_app_config)

            assert parser.validate_embedding(sample_sentiment_embedding) is True

            # After the M1 fix, a failed embedding carries empty dicts;
            # validate_embedding rejects on the `success` flag first.
            sample_sentiment_embedding.success = False
            assert parser.validate_embedding(sample_sentiment_embedding) is False

    def test_failure_has_empty_dicts_not_zero_vector(self, mock_app_config):
        """Review M1 / PLAN.md I5: failure paths must not return a zero vector
        that looks valid. They return empty dicts so a caller who ignores
        `success` gets a fail-fast KeyError, not silent neutral data."""
        from quorum.legacy.embedding_agent.embedding_parser import _failure

        result = _failure(
            date=__import__('datetime').datetime(2026, 6, 1, tzinfo=__import__('datetime').timezone.utc),
            model="gpt-4",
            reason="test",
        )
        assert result.success is False
        assert result.embeddings == {}
        assert result.confidence_scores == {}

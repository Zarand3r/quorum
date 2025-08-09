"""
Core functionality tests for the LLM Market Fetch system.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from pelosi.config.settings import AppConfig
from pelosi.embedding_agent.llm_client import LLMClient, LLMResponse
from pelosi.embedding_agent.market_fetcher import MarketContextFetcher
from pelosi.embedding_agent.embedding_parser import EmbeddingParser


@pytest.mark.unit
class TestLLMClient:
    """Test the LLM client functionality."""
    
    def test_llm_client_creation(self, mock_app_config):
        """Test LLM client can be created."""
        with patch('pelosi.embedding_agent.llm_client.OpenAI'):
            client = LLMClient(mock_app_config.api)
            assert client.config == mock_app_config.api
    
    @patch('pelosi.embedding_agent.llm_client.OpenAI')
    def test_successful_completion(self, mock_openai_class, mock_app_config):
        """Test successful LLM completion."""
        # Mock OpenAI response
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test
        llm_client = LLMClient(mock_app_config.api)
        messages = [{"role": "user", "content": "test"}]
        response = llm_client.generate_completion(messages)
        
        assert response.success is True
        assert response.content == "Test response"
        assert response.tokens_used == 150


@pytest.mark.unit  
class TestMarketFetcher:
    """Test the market context fetcher."""
    
    def test_market_fetcher_creation(self, mock_app_config):
        """Test market fetcher can be created."""
        with patch('pelosi.embedding_agent.market_fetcher.LLMClient'):
            fetcher = MarketContextFetcher(mock_app_config)
            assert fetcher.config == mock_app_config
    
    @patch('yfinance.Ticker')
    def test_market_data_collection(self, mock_ticker_class, mock_app_config):
        """Test basic market data collection."""
        # Mock yfinance ticker
        mock_ticker = Mock()
        import pandas as pd
        mock_history = pd.DataFrame({
            'Close': [450.0, 451.0],
            'Volume': [1000000, 1100000]
        })
        mock_ticker.history.return_value = mock_history
        mock_ticker.info = {'trailingPE': 20.0, 'marketCap': 1000000000}
        mock_ticker_class.return_value = mock_ticker
        
        # Test
        with patch('pelosi.embedding_agent.market_fetcher.LLMClient'):
            fetcher = MarketContextFetcher(mock_app_config)
            data = fetcher.data_collector.get_market_data(['SPY'])
            
            assert 'SPY' in data
            assert 'current_price' in data['SPY']


@pytest.mark.unit
class TestEmbeddingParser:
    """Test the embedding parser."""
    
    def test_embedding_parser_creation(self, mock_app_config):
        """Test embedding parser can be created."""
        with patch('pelosi.embedding_agent.embedding_parser.LLMClient'):
            parser = EmbeddingParser(mock_app_config)
            assert parser.config == mock_app_config
    
    def test_embedding_validation(self, mock_app_config, sample_sentiment_embedding):
        """Test embedding validation."""
        with patch('pelosi.embedding_agent.embedding_parser.LLMClient'):
            parser = EmbeddingParser(mock_app_config)
            
            # Test valid embedding
            is_valid = parser.validate_embedding(sample_sentiment_embedding)
            assert is_valid is True
            
            # Test invalid embedding
            sample_sentiment_embedding.success = False
            is_valid = parser.validate_embedding(sample_sentiment_embedding)
            assert is_valid is False


@pytest.mark.integration
class TestPipelineIntegration:
    """Test basic pipeline integration."""
    
    @pytest.mark.asyncio
    @patch('pelosi.embedding_agent.market_fetcher.MarketDataCollector')
    @patch('pelosi.embedding_agent.llm_client.OpenAI')
    async def test_basic_pipeline(self, mock_openai_class, mock_collector_class, 
                                 mock_app_config, sample_market_data):
        """Test that the basic pipeline components work together."""
        
        # Mock OpenAI
        mock_openai_client = Mock()
        mock_openai_class.return_value = mock_openai_client
        
        # Mock market analysis response
        analysis_response = Mock()
        analysis_response.choices = [Mock()]
        analysis_response.choices[0].message.content = "Market shows positive sentiment"
        analysis_response.usage.prompt_tokens = 100
        analysis_response.usage.completion_tokens = 50
        analysis_response.usage.total_tokens = 150
        
        # Mock embedding response
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
  }
}
```'''
        embedding_response.usage.prompt_tokens = 200
        embedding_response.usage.completion_tokens = 100
        embedding_response.usage.total_tokens = 300
        
        mock_openai_client.chat.completions.create.side_effect = [
            analysis_response, embedding_response
        ]
        
        # Mock data collector
        mock_collector = Mock()  # Use regular Mock for sync methods
        mock_collector.get_market_data.return_value = sample_market_data
        mock_collector.get_financial_news = AsyncMock(return_value=[])
        mock_collector.get_economic_indicators = AsyncMock(return_value={})
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.__aexit__ = AsyncMock(return_value=None)
        mock_collector_class.return_value = mock_collector
        
        # Test pipeline
        market_fetcher = MarketContextFetcher(mock_app_config)
        embedding_parser = EmbeddingParser(mock_app_config)
        
        # Fetch context
        market_context = await market_fetcher.fetch_market_context()
        assert market_context.success is True
        
        # Extract embeddings
        sentiment_embedding = embedding_parser.extract_embeddings(market_context)
        assert sentiment_embedding.success is True
        assert len(sentiment_embedding.embeddings) == 10 
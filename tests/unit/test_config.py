"""
Unit tests for the configuration system.
"""

import pytest
import os
from unittest.mock import patch

from pelosi.config.settings import APIConfig, DatabaseConfig, MarketConfig, AppConfig


class TestAPIConfig:
    """Test cases for APIConfig."""
    
    def test_api_config_creation(self):
        """Test basic APIConfig creation."""
        config = APIConfig(openai_api_key="test-key")
        
        assert config.openai_api_key == "test-key"
        assert config.openai_model == "gpt-4"
        assert config.openai_max_tokens == 2000
        assert config.openai_temperature == 0.3
        assert config.requests_per_minute == 60
    
    def test_api_config_from_env(self, monkeypatch):
        """Test APIConfig creation from environment variables."""
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-3.5-turbo")
        monkeypatch.setenv("OPENAI_MAX_TOKENS", "1500")
        monkeypatch.setenv("OPENAI_TEMPERATURE", "0.7")
        monkeypatch.setenv("REQUESTS_PER_MINUTE", "30")
        
        config = APIConfig.from_env()
        
        assert config.openai_api_key == "env-key"
        assert config.openai_model == "gpt-3.5-turbo"
        assert config.openai_max_tokens == 1500
        assert config.openai_temperature == 0.7
        assert config.requests_per_minute == 30
    
    def test_api_config_defaults_when_env_missing(self):
        """Test APIConfig uses defaults when environment variables are missing."""
        config = APIConfig.from_env()
        
        assert config.openai_model == "gpt-4"
        assert config.openai_max_tokens == 2000
        assert config.openai_temperature == 0.3


class TestDatabaseConfig:
    """Test cases for DatabaseConfig."""
    
    def test_database_config_creation(self):
        """Test basic DatabaseConfig creation."""
        config = DatabaseConfig()
        
        assert config.database_url == "sqlite:///pelosi_market_data.db"
        assert config.redis_url == "redis://localhost:6379/0"
    
    def test_database_config_from_env(self, monkeypatch):
        """Test DatabaseConfig creation from environment variables."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
        
        config = DatabaseConfig.from_env()
        
        assert config.database_url == "postgresql://user:pass@localhost/test"
        assert config.redis_url == "redis://localhost:6379/1"


class TestMarketConfig:
    """Test cases for MarketConfig."""
    
    def test_market_config_creation(self):
        """Test basic MarketConfig creation."""
        config = MarketConfig()
        
        assert config.target_symbols == ['SPY', 'QQQ', 'IWM', 'DIA']
        assert len(config.news_sources) == 6
        assert config.lookback_days == 30
        assert config.prediction_horizon_days == 5
        assert len(config.embedding_dimensions) == 10
    
    def test_market_config_custom_symbols(self):
        """Test MarketConfig with custom symbols."""
        config = MarketConfig(target_symbols=['AAPL', 'GOOGL', 'MSFT'])
        
        assert config.target_symbols == ['AAPL', 'GOOGL', 'MSFT']
    
    def test_market_config_from_env(self, monkeypatch):
        """Test MarketConfig creation from environment variables."""
        monkeypatch.setenv("TARGET_SYMBOLS", "AAPL,GOOGL,MSFT,TSLA")
        monkeypatch.setenv("LOOKBACK_DAYS", "60")
        monkeypatch.setenv("PREDICTION_HORIZON_DAYS", "10")
        
        config = MarketConfig.from_env()
        
        assert config.target_symbols == ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
        assert config.lookback_days == 60
        assert config.prediction_horizon_days == 10
    
    def test_embedding_dimensions_default(self):
        """Test that all expected embedding dimensions are present."""
        config = MarketConfig()
        
        expected_dimensions = [
            'tech_earnings_momentum',
            'AI_optimism', 
            'interest_rate_expectations',
            'tariff_risk',
            'retail_investor_sentiment',
            'institutional_caution',
            'valuation_concerns',
            'macro_stability',
            'market_liquidity',
            'crowded_trades_risk'
        ]
        
        assert config.embedding_dimensions == expected_dimensions


class TestAppConfig:
    """Test cases for AppConfig."""
    
    def test_app_config_load(self, monkeypatch):
        """Test complete AppConfig loading."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("LOG_LEVEL", "INFO")
        monkeypatch.setenv("DAILY_RUN_TIME", "08:30")
        
        config = AppConfig.load()
        
        assert isinstance(config.api, APIConfig)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.market, MarketConfig)
        assert config.log_level == "INFO"
        assert config.daily_run_time == "08:30"
    
    def test_app_config_defaults(self, monkeypatch):
        """Test AppConfig default values."""
        # Temporarily unset environment variables to test defaults
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        monkeypatch.delenv("LOG_FILE", raising=False)
        monkeypatch.delenv("DAILY_RUN_TIME", raising=False)
        
        config = AppConfig.load()
        
        assert config.log_level == "INFO"
        assert config.log_file == "pelosi.log"
        assert config.daily_run_time == "09:00"
    
    @patch('pelosi.config.settings.APIConfig.from_env')
    @patch('pelosi.config.settings.DatabaseConfig.from_env')
    @patch('pelosi.config.settings.MarketConfig.from_env')
    def test_app_config_component_loading(self, mock_market, mock_db, mock_api):
        """Test that AppConfig properly loads all components."""
        mock_api.return_value = APIConfig(openai_api_key="test")
        mock_db.return_value = DatabaseConfig()
        mock_market.return_value = MarketConfig()
        
        config = AppConfig.load()
        
        mock_api.assert_called_once()
        mock_db.assert_called_once()
        mock_market.assert_called_once()
        
        assert isinstance(config.api, APIConfig)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.market, MarketConfig) 
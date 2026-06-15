"""Unit tests for ``quorum.config.settings``."""

from unittest.mock import patch

from quorum.config.settings import (
    APIConfig,
    AppConfig,
    DatabaseConfig,
    LEGACY_EMBEDDING_DIMENSIONS,
    MarketConfig,
)


class TestAPIConfig:
    def test_api_config_creation(self):
        config = APIConfig(openai_api_key="test-key")
        assert config.openai_api_key == "test-key"
        assert config.openai_model == "gpt-4"
        assert config.openai_max_tokens == 2000
        assert config.openai_temperature == 0.3
        assert config.requests_per_minute == 60

    def test_api_config_from_env(self, monkeypatch):
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
        config = APIConfig.from_env()
        assert config.openai_model == "gpt-4"
        assert config.openai_max_tokens == 2000
        assert config.openai_temperature == 0.3


class TestDatabaseConfig:
    def test_database_config_creation(self):
        config = DatabaseConfig()
        # PLAN.md §8: v0 storage is a single DuckDB file.
        assert config.database_url.startswith("duckdb")
        assert "quorum" in config.database_url
        assert config.redis_url == "redis://localhost:6379/0"

    def test_database_config_from_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")

        config = DatabaseConfig.from_env()

        assert config.database_url == "postgresql://user:pass@localhost/test"
        assert config.redis_url == "redis://localhost:6379/1"


class TestMarketConfig:
    def test_market_config_creation(self):
        config = MarketConfig()
        assert config.target_symbols == ['SPY', 'QQQ', 'IWM', 'DIA']
        assert len(config.news_sources) == 6
        assert config.lookback_days == 30
        assert config.prediction_horizon_days == 5
        assert config.embedding_dimensions == LEGACY_EMBEDDING_DIMENSIONS

    def test_market_config_custom_symbols(self):
        config = MarketConfig(target_symbols=['AAPL', 'GOOGL', 'MSFT'])
        assert config.target_symbols == ['AAPL', 'GOOGL', 'MSFT']

    def test_market_config_from_env(self, monkeypatch):
        monkeypatch.setenv("TARGET_SYMBOLS", "AAPL,GOOGL,MSFT,TSLA")
        monkeypatch.setenv("LOOKBACK_DAYS", "60")
        monkeypatch.setenv("PREDICTION_HORIZON_DAYS", "10")

        config = MarketConfig.from_env()

        assert config.target_symbols == ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
        assert config.lookback_days == 60
        assert config.prediction_horizon_days == 10


class TestAppConfig:
    def test_app_config_load(self, monkeypatch):
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
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        monkeypatch.delenv("LOG_FILE", raising=False)
        monkeypatch.delenv("DAILY_RUN_TIME", raising=False)

        config = AppConfig.load()

        assert config.log_level == "INFO"
        assert config.log_file == "quorum.log"
        assert config.daily_run_time == "09:00"

    @patch('quorum.config.settings.APIConfig.from_env')
    @patch('quorum.config.settings.DatabaseConfig.from_env')
    @patch('quorum.config.settings.MarketConfig.from_env')
    def test_app_config_component_loading(self, mock_market, mock_db, mock_api):
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

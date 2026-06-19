"""
Configuration for quorum.

This module is shared by ``quorum.legacy`` (the pre-refinement sentiment
pipeline) and will be shared by the refined news-impact estimator once it
lands. Some fields (``MarketConfig.embedding_dimensions``,
``DatabaseConfig.redis_url``) are scoped to the legacy pipeline; they will be
trimmed when the legacy code retires.

Discipline (PLAN.md, ``docs/constitution.md``):
- No module-import-time I/O: ``AppConfig.load()`` must be called explicitly
  (review M7 — removed the eager ``config = AppConfig.load()`` global).
"""

import os
from typing import List
from dataclasses import dataclass, field


# 10-dimension sentiment list used by the LEGACY embedding pipeline only.
# The refined PLAN.md does not use this shape.
LEGACY_EMBEDDING_DIMENSIONS: List[str] = [
    'tech_earnings_momentum',
    'AI_optimism',
    'interest_rate_expectations',
    'tariff_risk',
    'retail_investor_sentiment',
    'institutional_caution',
    'valuation_concerns',
    'macro_stability',
    'market_liquidity',
    'crowded_trades_risk',
]


@dataclass
class APIConfig:
    """LLM / market data API configuration."""
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.3

    alpha_vantage_key: str = ""
    finnhub_key: str = ""

    requests_per_minute: int = 60

    @classmethod
    def from_env(cls) -> "APIConfig":
        return cls(
            openai_api_key=os.getenv('OPENAI_API_KEY', ''),
            openai_model=os.getenv('OPENAI_MODEL', 'gpt-4'),
            openai_max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '2000')),
            openai_temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.3')),
            alpha_vantage_key=os.getenv('ALPHA_VANTAGE_API_KEY', ''),
            finnhub_key=os.getenv('FINNHUB_API_KEY', ''),
            requests_per_minute=int(os.getenv('REQUESTS_PER_MINUTE', '60')),
        )


@dataclass
class DatabaseConfig:
    """Storage configuration.

    ``database_url`` defaults to a DuckDB file for the refined Slice 0
    pipeline (PLAN.md §8). ``redis_url`` is legacy and will be removed when
    the legacy pipeline retires.
    """
    database_url: str = "duckdb:///./data/quorum.duckdb"
    redis_url: str = "redis://localhost:6379/0"

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        return cls(
            database_url=os.getenv('DATABASE_URL', 'duckdb:///./data/quorum.duckdb'),
            redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        )


@dataclass
class MarketConfig:
    """Market data and analysis configuration."""
    target_symbols: List[str] = field(default_factory=lambda: ['SPY', 'QQQ', 'IWM', 'DIA'])
    news_sources: List[str] = field(default_factory=lambda: [
        'reuters', 'bloomberg', 'cnbc', 'marketwatch', 'financial_times', 'wsj',
    ])
    lookback_days: int = 30
    prediction_horizon_days: int = 5
    embedding_dimensions: List[str] = field(default_factory=lambda: list(LEGACY_EMBEDDING_DIMENSIONS))

    @classmethod
    def from_env(cls) -> "MarketConfig":
        config = cls()
        if os.getenv('TARGET_SYMBOLS'):
            config.target_symbols = os.getenv('TARGET_SYMBOLS').split(',')
        if os.getenv('LOOKBACK_DAYS'):
            config.lookback_days = int(os.getenv('LOOKBACK_DAYS'))
        if os.getenv('PREDICTION_HORIZON_DAYS'):
            config.prediction_horizon_days = int(os.getenv('PREDICTION_HORIZON_DAYS'))
        return config


@dataclass
class AppConfig:
    """Top-level application configuration."""
    api: APIConfig
    database: DatabaseConfig
    market: MarketConfig

    log_level: str = "INFO"
    log_file: str = "quorum.log"
    daily_run_time: str = "09:00"  # UTC HH:MM for the daily cron tick (legacy).

    @classmethod
    def load(cls) -> "AppConfig":
        return cls(
            api=APIConfig.from_env(),
            database=DatabaseConfig.from_env(),
            market=MarketConfig.from_env(),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file=os.getenv('LOG_FILE', 'quorum.log'),
            daily_run_time=os.getenv('DAILY_RUN_TIME', '09:00'),
        )

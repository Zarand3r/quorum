"""
Configuration settings for the market sentiment forecasting service.
"""

import os
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class APIConfig:
    """API configuration settings."""
    openai_api_key: str
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.3
    
    # Market data APIs
    alpha_vantage_key: str = ""
    finnhub_key: str = ""
    
    # Rate limiting
    requests_per_minute: int = 60
    
    @classmethod
    def from_env(cls) -> 'APIConfig':
        """Load configuration from environment variables."""
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
    """Database configuration settings."""
    database_url: str = "sqlite:///pelosi_market_data.db"
    redis_url: str = "redis://localhost:6379/0"
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Load database configuration from environment variables."""
        return cls(
            database_url=os.getenv('DATABASE_URL', 'sqlite:///pelosi_market_data.db'),
            redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        )


@dataclass
class MarketConfig:
    """Market data and analysis configuration."""
    # Target indices/stocks to track
    target_symbols: List[str] = None
    
    # News sources and data providers
    news_sources: List[str] = None
    
    # Analysis timeframes
    lookback_days: int = 30
    prediction_horizon_days: int = 5
    
    # Sentiment embedding dimensions
    embedding_dimensions: List[str] = None
    
    def __post_init__(self):
        if self.target_symbols is None:
            self.target_symbols = ['SPY', 'QQQ', 'IWM', 'DIA']
            
        if self.news_sources is None:
            self.news_sources = [
                'reuters', 'bloomberg', 'cnbc', 'marketwatch', 
                'financial_times', 'wsj'
            ]
            
        if self.embedding_dimensions is None:
            self.embedding_dimensions = [
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
    
    @classmethod
    def from_env(cls) -> 'MarketConfig':
        """Load market configuration from environment variables."""
        config = cls()
        
        # Override with environment variables if present
        if os.getenv('TARGET_SYMBOLS'):
            config.target_symbols = os.getenv('TARGET_SYMBOLS').split(',')
            
        if os.getenv('LOOKBACK_DAYS'):
            config.lookback_days = int(os.getenv('LOOKBACK_DAYS'))
            
        if os.getenv('PREDICTION_HORIZON_DAYS'):
            config.prediction_horizon_days = int(os.getenv('PREDICTION_HORIZON_DAYS'))
            
        return config


@dataclass
class AppConfig:
    """Main application configuration."""
    api: APIConfig
    database: DatabaseConfig
    market: MarketConfig
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "pelosi.log"
    
    # Scheduler
    daily_run_time: str = "09:00"  # UTC time for daily runs
    
    @classmethod
    def load(cls) -> 'AppConfig':
        """Load complete application configuration."""
        return cls(
            api=APIConfig.from_env(),
            database=DatabaseConfig.from_env(),
            market=MarketConfig.from_env(),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file=os.getenv('LOG_FILE', 'pelosi.log'),
            daily_run_time=os.getenv('DAILY_RUN_TIME', '09:00'),
        )


# Global configuration instance
config = AppConfig.load() 
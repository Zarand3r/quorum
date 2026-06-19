"""
LEGACY — pre-refinement LLM sentiment-embedding extraction.

Preserved for reference. Build new functionality under ``market/``, not here.
See ``market/legacy/main.py`` for the rationale.
"""

from .market_fetcher import MarketContextFetcher
from .llm_client import LLMClient
from .embedding_parser import EmbeddingParser

__all__ = ['MarketContextFetcher', 'LLMClient', 'EmbeddingParser']

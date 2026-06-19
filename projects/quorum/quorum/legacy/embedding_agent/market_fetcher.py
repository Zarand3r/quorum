"""
LEGACY — market context fetcher used by the pre-refinement sentiment pipeline.

Refactored to remove the mock-news and mock-economic-indicator code paths that
silently injected hardcoded data into the LLM prompt (see review M3, M4 — a
violation of PLAN.md I5 / constitution "No silent fallback"). The fetcher now
only ships *real* yfinance data; the news and indicator paths return empty
collections with a logged warning, so the LLM prompt no longer contains
hallucinated inputs.

Build new functionality under ``quorum/``, not here.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import re

import yfinance as yf

from .llm_client import LLMClient, LLMResponse
from ...config.settings import AppConfig


logger = logging.getLogger(__name__)


@dataclass
class MarketContext:
    """Structured market context data."""
    date: datetime
    market_data: Dict[str, Any]
    news_summary: str
    key_events: List[str]
    market_sentiment_raw: str
    data_sources: List[str] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None


class MarketDataCollector:
    """Collects market data from various sources.

    Synchronous only after the M3/M4 cleanup — the only data source still
    wired is ``yfinance``, which is synchronous.
    """

    def __init__(self, config: AppConfig):
        self.config = config

    def get_market_data(self, symbols: List[str], period: str = "5d") -> Dict[str, Any]:
        """Fetch market data for given symbols using yfinance.

        Each symbol returns a dict on success, or ``{"error": "..."}`` on
        failure. Callers must check for the ``error`` key — there is no
        neutral fallback (PLAN.md I5).
        """
        market_data: Dict[str, Any] = {}

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
                # NOTE: ``ticker.info`` does an extra HTTP round-trip per symbol
                # and is unreliable; skip it for the v0 hot path (review m3).

                if hist.empty:
                    logger.warning("No market data available for %s", symbol)
                    market_data[symbol] = {'error': 'no_data'}
                    continue

                latest = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else latest
                market_data[symbol] = {
                    'current_price': float(latest['Close']),
                    'previous_price': float(prev['Close']),
                    'change': float(latest['Close'] - prev['Close']),
                    'change_percent': float((latest['Close'] - prev['Close']) / prev['Close'] * 100),
                    'volume': int(latest['Volume']),
                }
                logger.info("Retrieved market data for %s", symbol)

            except Exception as e:  # noqa: BLE001 — yfinance raises arbitrary network errors
                logger.error("Error fetching market data for %s: %s", symbol, e)
                market_data[symbol] = {'error': str(e)}

        return market_data

    def get_financial_news(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recent financial news.

        Pre-refinement, this returned hardcoded mock articles that were then
        injected into the LLM prompt as if real (review M3 — I5 violation).
        Removed in the cleanup. Until PLAN.md section 19 decides on a real
        news source, this returns an empty list with a visible warning.
        """
        logger.warning(
            "quorum.legacy.market_fetcher.get_financial_news: no news source is wired; "
            "returning []. Resolve PLAN.md §19 question 1 before relying on this path."
        )
        return []

    def get_economic_indicators(self) -> Dict[str, Any]:
        """Fetch key economic indicators.

        Pre-refinement, this returned zeros for VIX/DXY/etc. that the LLM then
        analyzed as if real (review M4 — I5 violation). Removed in the cleanup.
        Returns an empty dict with a visible warning.
        """
        logger.warning(
            "quorum.legacy.market_fetcher.get_economic_indicators: no provider is wired; "
            "returning {}. Wire a real source (FRED / Polygon) before relying on this path."
        )
        return {}


class MarketContextFetcher:
    """Orchestrates yfinance data + LLM analysis into a MarketContext."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.llm_client = LLMClient(config.api)
        self.data_collector = MarketDataCollector(config)

    def _create_market_analysis_prompt(
        self,
        market_data: Dict[str, Any],
        news_articles: List[Dict[str, Any]],
        economic_indicators: Dict[str, Any],
    ) -> str:
        prompt = (
            "You are a financial market analyst. Analyze the current market "
            "conditions based on the following data and provide a comprehensive "
            "market context summary.\n\n**MARKET DATA:**\n"
        )

        for symbol, data in market_data.items():
            if 'error' in data:
                continue
            prompt += (
                f"\n{symbol}:\n"
                f"- Current Price: ${data.get('current_price', 0):.2f}\n"
                f"- Change: {data.get('change_percent', 0):+.2f}%\n"
                f"- Volume: {data.get('volume', 0):,}\n"
            )

        if economic_indicators:
            prompt += "\n**ECONOMIC INDICATORS:**\n"
            for key, value in economic_indicators.items():
                prompt += f"- {key}: {value}\n"
        else:
            prompt += "\n**ECONOMIC INDICATORS:** (none available — do not infer)\n"

        if news_articles:
            prompt += "\n**RECENT NEWS:**\n"
            for i, article in enumerate(news_articles[:10], 1):
                prompt += f"{i}. {article['title']}\n   Summary: {article['summary']}\n\n"
        else:
            prompt += "\n**RECENT NEWS:** (none available — do not infer news)\n"

        prompt += (
            "\n**ANALYSIS REQUIREMENTS:**\n"
            "Provide a structured analysis covering market sentiment, key drivers, "
            "sector outlook, risk factors, technical outlook, and notable events. "
            "Base your analysis only on data explicitly provided above. Do not "
            "invent news, economic indicators, or events that are not present.\n"
        )
        return prompt

    async def fetch_market_context(self, date: Optional[datetime] = None) -> MarketContext:
        """Fetch comprehensive market context for the given date (UTC).

        Async signature is preserved for existing callers (tests, ``main``)
        even though every inner call is now synchronous after the M3/M4
        cleanup. A future news/indicator source can become async without
        another signature change.
        """
        if date is None:
            date = datetime.now(timezone.utc)

        logger.info("Fetching market context for %s", date.isoformat())

        try:
            market_data = self.data_collector.get_market_data(
                symbols=self.config.market.target_symbols,
                period="5d",
            )
            news_articles = self.data_collector.get_financial_news(limit=20)
            economic_indicators = self.data_collector.get_economic_indicators()

            analysis_prompt = self._create_market_analysis_prompt(
                market_data, news_articles, economic_indicators,
            )

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert financial market analyst with deep "
                        "knowledge of market dynamics, technical analysis, and "
                        "macroeconomic factors."
                    ),
                },
                {"role": "user", "content": analysis_prompt},
            ]

            logger.info("Requesting LLM market analysis...")
            llm_response = self.llm_client.generate_completion(messages=messages)

            if not llm_response.success:
                return MarketContext(
                    date=date,
                    market_data={},
                    news_summary="",
                    key_events=[],
                    market_sentiment_raw="",
                    data_sources=[],
                    success=False,
                    error_message=f"LLM analysis failed: {llm_response.error_message}",
                )

            return MarketContext(
                date=date,
                market_data=market_data,
                news_summary=self._create_news_summary(news_articles),
                key_events=self._extract_key_events(llm_response.content),
                market_sentiment_raw=llm_response.content,
                data_sources=["yfinance"],
                success=True,
            )

        except Exception as e:  # noqa: BLE001 — network/yfinance raise arbitrary errors
            logger.exception("Error fetching market context")
            return MarketContext(
                date=date,
                market_data={},
                news_summary="",
                key_events=[],
                market_sentiment_raw="",
                data_sources=[],
                success=False,
                error_message=str(e),
            )

    def _extract_key_events(self, analysis_text: str) -> List[str]:
        key_events: List[str] = []
        for raw_line in analysis_text.split('\n'):
            line = raw_line.strip()
            if (line.startswith('•') or line.startswith('-')
                    or line.startswith('*') or re.match(r'^\d+\.', line)):
                clean = re.sub(r'^[•\-\*\d\.]\s*', '', line)
                if len(clean) > 10:
                    key_events.append(clean)

        if not key_events:
            for sentence in analysis_text.split('.'):
                sentence = sentence.strip()
                if any(k in sentence.lower() for k in
                       ('significant', 'important', 'major', 'key', 'notable', 'critical')):
                    if len(sentence) > 20:
                        key_events.append(sentence)

        return key_events[:10]

    def _create_news_summary(self, news_articles: List[Dict[str, Any]]) -> str:
        if not news_articles:
            return "No news articles available."
        return "\n".join(
            f"• {a.get('title', 'Untitled')}: {a.get('summary', '')}"
            for a in news_articles[:5]
        )

    async def test_data_sources(self) -> Dict[str, bool]:
        """Test connectivity to wired data sources."""
        results: Dict[str, bool] = {
            'llm': self.llm_client.test_connection(),
        }

        try:
            test_data = self.data_collector.get_market_data(['SPY'], period='1d')
            results['market_data'] = 'SPY' in test_data and 'error' not in test_data['SPY']
        except Exception:  # noqa: BLE001
            results['market_data'] = False

        return results

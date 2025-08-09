"""
Market Context Fetcher - LLM Market Fetch Logic

This module implements the core LLM Market Fetch functionality that:
1. Gathers market context from multiple sources
2. Uses LLM to analyze and synthesize market information
3. Prepares structured context for sentiment embedding extraction
"""

import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re

import yfinance as yf
from bs4 import BeautifulSoup

from .llm_client import LLMClient, LLMResponse
from ..config.settings import AppConfig


logger = logging.getLogger(__name__)


@dataclass
class MarketContext:
    """Structured market context data."""
    date: datetime
    market_data: Dict[str, Any]  # Price data, volumes, etc.
    news_summary: str            # LLM-synthesized news summary
    key_events: List[str]        # Important events/announcements
    market_sentiment_raw: str    # Raw LLM analysis
    data_sources: List[str]      # Sources used for context
    success: bool = True
    error_message: Optional[str] = None


class MarketDataCollector:
    """Collects market data from various sources."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def get_market_data(self, symbols: List[str], period: str = "5d") -> Dict[str, Any]:
        """
        Fetch market data for given symbols using yfinance.
        
        Args:
            symbols: List of ticker symbols
            period: Data period (1d, 5d, 1mo, etc.)
            
        Returns:
            Dictionary with market data for each symbol
        """
        market_data = {}
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
                info = ticker.info
                
                if not hist.empty:
                    latest = hist.iloc[-1]
                    prev = hist.iloc[-2] if len(hist) > 1 else latest
                    
                    market_data[symbol] = {
                        'current_price': float(latest['Close']),
                        'previous_price': float(prev['Close']),
                        'change': float(latest['Close'] - prev['Close']),
                        'change_percent': float((latest['Close'] - prev['Close']) / prev['Close'] * 100),
                        'volume': int(latest['Volume']),
                        'high_52w': info.get('fiftyTwoWeekHigh', 0),
                        'low_52w': info.get('fiftyTwoWeekLow', 0),
                        'market_cap': info.get('marketCap', 0),
                        'pe_ratio': info.get('trailingPE', 0),
                        'avg_volume': info.get('averageVolume', 0),
                    }
                    
                    logger.info(f"Retrieved market data for {symbol}")
                else:
                    logger.warning(f"No market data available for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error fetching market data for {symbol}: {e}")
                market_data[symbol] = {'error': str(e)}
        
        return market_data
    
    async def get_financial_news(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch recent financial news from various sources.
        
        Args:
            limit: Maximum number of articles to fetch
            
        Returns:
            List of news articles with title, summary, source, date
        """
        news_articles = []
        
        # For now, we'll use a simple approach with financial news APIs
        # In production, you'd want to integrate with proper news APIs
        
        try:
            # Example: Fetch from financial news sources
            # This is a simplified implementation - you'd want to use proper APIs
            news_sources = [
                "https://finance.yahoo.com/news/",
                "https://www.marketwatch.com/latest-news",
            ]
            
            for source_url in news_sources[:2]:  # Limit to avoid overwhelming requests
                try:
                    async with self.session.get(source_url) as response:
                        if response.status == 200:
                            # This is a simplified example - proper implementation would
                            # use structured APIs rather than web scraping
                            logger.info(f"Successfully connected to {source_url}")
                            
                            # For demonstration, we'll create mock news data
                            # In production, parse actual news content
                            mock_articles = [
                                {
                                    'title': 'Market Analysis: Tech Stocks Show Strong Momentum',
                                    'summary': 'Technology sector continues to outperform amid AI optimism',
                                    'source': 'Financial News',
                                    'date': datetime.now().isoformat(),
                                    'url': source_url
                                }
                            ]
                            news_articles.extend(mock_articles)
                            
                except Exception as e:
                    logger.warning(f"Could not fetch news from {source_url}: {e}")
            
            logger.info(f"Collected {len(news_articles)} news articles")
            
        except Exception as e:
            logger.error(f"Error in news collection: {e}")
        
        return news_articles[:limit]
    
    async def get_economic_indicators(self) -> Dict[str, Any]:
        """
        Fetch key economic indicators.
        
        Returns:
            Dictionary with economic indicators
        """
        indicators = {}
        
        try:
            # Fetch key economic data
            # This would typically use APIs like FRED, Alpha Vantage, etc.
            
            # For now, we'll return mock data structure
            # In production, integrate with actual economic data APIs
            indicators = {
                'vix': 0.0,  # Volatility Index
                'dxy': 0.0,  # Dollar Index
                'treasury_10y': 0.0,  # 10-year Treasury yield
                'oil_price': 0.0,  # Crude oil price
                'gold_price': 0.0,  # Gold price
                'crypto_fear_greed': 0,  # Crypto Fear & Greed Index
            }
            
            logger.info("Economic indicators collected (mock data)")
            
        except Exception as e:
            logger.error(f"Error fetching economic indicators: {e}")
        
        return indicators


class MarketContextFetcher:
    """
    Main class for LLM Market Fetch logic.
    
    Orchestrates the collection of market data, news, and economic indicators,
    then uses LLM to synthesize this information into structured market context.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.llm_client = LLMClient(config.api)
        self.data_collector = MarketDataCollector(config)
    
    def _create_market_analysis_prompt(
        self, 
        market_data: Dict[str, Any], 
        news_articles: List[Dict[str, Any]],
        economic_indicators: Dict[str, Any]
    ) -> str:
        """
        Create a comprehensive prompt for LLM market analysis.
        
        Args:
            market_data: Current market data for tracked symbols
            news_articles: Recent financial news articles
            economic_indicators: Key economic indicators
            
        Returns:
            Formatted prompt string for LLM analysis
        """
        prompt = f"""You are a financial market analyst. Analyze the current market conditions based on the following data and provide a comprehensive market context summary.

**MARKET DATA:**
"""
        
        # Add market data to prompt
        for symbol, data in market_data.items():
            if 'error' not in data:
                prompt += f"""
{symbol}:
- Current Price: ${data.get('current_price', 0):.2f}
- Change: {data.get('change_percent', 0):+.2f}%
- Volume: {data.get('volume', 0):,}
- 52W High/Low: ${data.get('high_52w', 0):.2f} / ${data.get('low_52w', 0):.2f}
- P/E Ratio: {data.get('pe_ratio', 0):.1f}
"""
        
        prompt += f"""
**ECONOMIC INDICATORS:**
- VIX (Volatility): {economic_indicators.get('vix', 'N/A')}
- Dollar Index (DXY): {economic_indicators.get('dxy', 'N/A')}
- 10Y Treasury Yield: {economic_indicators.get('treasury_10y', 'N/A')}%
- Oil Price: ${economic_indicators.get('oil_price', 'N/A')}
- Gold Price: ${economic_indicators.get('gold_price', 'N/A')}

**RECENT NEWS:**
"""
        
        # Add news articles to prompt
        for i, article in enumerate(news_articles[:10], 1):  # Limit to top 10
            prompt += f"{i}. {article['title']}\n   Summary: {article['summary']}\n\n"
        
        prompt += """
**ANALYSIS REQUIREMENTS:**

Please provide a comprehensive analysis covering:

1. **Market Sentiment Overview**: Current overall market mood and direction
2. **Key Drivers**: Main factors influencing market movements today
3. **Sector Analysis**: Which sectors are showing strength/weakness and why
4. **Risk Factors**: Current risks and concerns in the market
5. **Technical Outlook**: Brief technical perspective on major indices
6. **Notable Events**: Any significant events or announcements affecting markets

**Important**: Focus on actionable insights and be specific about the factors driving current market sentiment. Consider both fundamental and technical factors.

Provide your analysis in a clear, structured format that captures the current market context comprehensively.
"""
        
        return prompt
    
    async def fetch_market_context(self, date: Optional[datetime] = None) -> MarketContext:
        """
        Fetch comprehensive market context for the given date.
        
        Args:
            date: Target date for analysis (defaults to today)
            
        Returns:
            MarketContext object with all gathered information
        """
        if date is None:
            date = datetime.now()
        
        logger.info(f"Fetching market context for {date.strftime('%Y-%m-%d')}")
        
        try:
            # Collect data from multiple sources
            async with self.data_collector as collector:
                # Gather market data
                market_data = collector.get_market_data(
                    symbols=self.config.market.target_symbols,
                    period="5d"
                )
                
                # Gather news articles
                news_articles = await collector.get_financial_news(limit=20)
                
                # Gather economic indicators
                economic_indicators = await collector.get_economic_indicators()
            
            # Create LLM analysis prompt
            analysis_prompt = self._create_market_analysis_prompt(
                market_data, news_articles, economic_indicators
            )
            
            # Get LLM analysis
            messages = [
                {"role": "system", "content": "You are an expert financial market analyst with deep knowledge of market dynamics, technical analysis, and macroeconomic factors."},
                {"role": "user", "content": analysis_prompt}
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
                    error_message=f"LLM analysis failed: {llm_response.error_message}"
                )
            
            # Extract key events from the analysis
            key_events = self._extract_key_events(llm_response.content)
            
            # Create news summary
            news_summary = self._create_news_summary(news_articles)
            
            return MarketContext(
                date=date,
                market_data=market_data,
                news_summary=news_summary,
                key_events=key_events,
                market_sentiment_raw=llm_response.content,
                data_sources=["yfinance", "financial_news", "economic_indicators"],
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error fetching market context: {e}")
            return MarketContext(
                date=date,
                market_data={},
                news_summary="",
                key_events=[],
                market_sentiment_raw="",
                data_sources=[],
                success=False,
                error_message=str(e)
            )
    
    def _extract_key_events(self, analysis_text: str) -> List[str]:
        """Extract key events from LLM analysis."""
        key_events = []
        
        try:
            # Look for bullet points or numbered lists in the analysis
            lines = analysis_text.split('\n')
            for line in lines:
                line = line.strip()
                if (line.startswith('•') or line.startswith('-') or 
                    line.startswith('*') or re.match(r'^\d+\.', line)):
                    # Clean up the line and add to key events
                    clean_line = re.sub(r'^[•\-\*\d\.]\s*', '', line)
                    if len(clean_line) > 10:  # Ignore very short items
                        key_events.append(clean_line)
            
            # If no bullet points found, try to extract sentences with strong indicators
            if not key_events:
                sentences = analysis_text.split('.')
                for sentence in sentences:
                    sentence = sentence.strip()
                    if any(keyword in sentence.lower() for keyword in 
                           ['significant', 'important', 'major', 'key', 'notable', 'critical']):
                        if len(sentence) > 20:
                            key_events.append(sentence)
            
        except Exception as e:
            logger.warning(f"Error extracting key events: {e}")
        
        return key_events[:10]  # Limit to top 10 events
    
    def _create_news_summary(self, news_articles: List[Dict[str, Any]]) -> str:
        """Create a concise summary of news articles."""
        if not news_articles:
            return "No recent news articles available."
        
        summaries = []
        for article in news_articles[:5]:  # Top 5 articles
            title = article.get('title', 'Untitled')
            summary = article.get('summary', 'No summary available')
            summaries.append(f"• {title}: {summary}")
        
        return "\n".join(summaries)
    
    async def test_data_sources(self) -> Dict[str, bool]:
        """
        Test connectivity to various data sources.
        
        Returns:
            Dictionary indicating which data sources are available
        """
        results = {}
        
        # Test LLM connection
        results['llm'] = self.llm_client.test_connection()
        
        # Test market data
        try:
            test_data = self.data_collector.get_market_data(['SPY'], period='1d')
            results['market_data'] = 'SPY' in test_data and 'error' not in test_data['SPY']
        except Exception:
            results['market_data'] = False
        
        # Test news sources
        try:
            async with self.data_collector as collector:
                news = await collector.get_financial_news(limit=1)
                results['news'] = len(news) > 0
        except Exception:
            results['news'] = False
        
        return results 
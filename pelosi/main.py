#!/usr/bin/env python3
"""
Simple entry point for the Pelosi Market Sentiment Forecasting Service.

Focuses on the core LLM Market Fetch functionality.
"""

import asyncio
import logging
import sys
from datetime import datetime

from .config.settings import AppConfig
from .embedding_agent.market_fetcher import MarketContextFetcher
from .embedding_agent.embedding_parser import EmbeddingParser


def setup_logging():
    """Setup simple logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


async def run_market_analysis():
    """Run the complete market sentiment analysis pipeline."""
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = AppConfig.load()
        logger.info("Configuration loaded successfully")
        
        # Initialize components
        market_fetcher = MarketContextFetcher(config)
        embedding_parser = EmbeddingParser(config)
        
        # Test connectivity
        logger.info("Testing data source connectivity...")
        connectivity = await market_fetcher.test_data_sources()
        
        if not connectivity.get('llm', False):
            logger.error("LLM not available. Please check your OPENAI_API_KEY.")
            return False
        
        logger.info("✅ All data sources connected")
        
        # Fetch market context
        logger.info("Fetching market context...")
        market_context = await market_fetcher.fetch_market_context()
        
        if not market_context.success:
            logger.error(f"Market context fetch failed: {market_context.error_message}")
            return False
        
        logger.info(f"✅ Market context retrieved for {len(market_context.market_data)} symbols")
        
        # Extract sentiment embeddings
        logger.info("Extracting sentiment embeddings...")
        sentiment_embedding = embedding_parser.extract_embeddings(market_context)
        
        if not sentiment_embedding.success:
            logger.error(f"Sentiment embedding extraction failed: {sentiment_embedding.error_message}")
            return False
        
        logger.info("✅ Sentiment embeddings extracted successfully")
        
        # Display results
        print("\n" + "="*60)
        print("🎯 MARKET SENTIMENT ANALYSIS RESULTS")
        print("="*60)
        print(f"Date: {sentiment_embedding.date.strftime('%Y-%m-%d %H:%M')}")
        print(f"Model: {sentiment_embedding.model_version}")
        print()
        
        # Show top sentiments
        sorted_embeddings = sorted(
            sentiment_embedding.embeddings.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        print("📊 Top Market Sentiments:")
        for i, (dim, value) in enumerate(sorted_embeddings[:5], 1):
            confidence = sentiment_embedding.confidence_scores.get(dim, 0.0)
            sentiment_type = "🟢 Bullish" if value > 0.1 else "🔴 Bearish" if value < -0.1 else "🟡 Neutral"
            print(f"  {i}. {dim.replace('_', ' ').title()}: {value:+.2f} {sentiment_type} (confidence: {confidence:.1%})")
        
        print("\n" + "="*60)
        logger.info("🎉 Analysis completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return False


def main():
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("🚀 Pelosi Market Sentiment Analysis")
    print("Running LLM Market Fetch pipeline...")
    print()
    
    try:
        success = asyncio.run(run_market_analysis())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Analysis cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 
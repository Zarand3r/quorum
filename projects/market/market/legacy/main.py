#!/usr/bin/env python3
"""
LEGACY — pre-refinement sentiment-embedding entry point.

This is the original 10-dimension sentiment-vector pipeline from before the
project was refined to the news-impact market state estimator described in
PLAN.md. It is preserved for reference; it is NOT on the path for Slice 0 or
any milestone M1-M6. Do not extend it; build new functionality under
``market/`` (not ``market/legacy/``).

Why kept: the JSON-extraction and rate-limiting plumbing in
``market.legacy.embedding_agent`` is reusable for the event-extraction stage
of PLAN.md section 4.4 once the new pipeline lands.
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone

from ..config.settings import AppConfig
from .embedding_agent.market_fetcher import MarketContextFetcher
from .embedding_agent.embedding_parser import EmbeddingParser


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


async def run_market_analysis():
    logger = logging.getLogger(__name__)

    try:
        config = AppConfig.load()
        logger.info("Configuration loaded successfully")

        market_fetcher = MarketContextFetcher(config)
        embedding_parser = EmbeddingParser(config)

        logger.info("Testing data source connectivity...")
        connectivity = await market_fetcher.test_data_sources()

        if not connectivity.get('llm', False):
            logger.error("LLM not available. Please check your OPENAI_API_KEY.")
            return False

        logger.info("Fetching market context...")
        market_context = await market_fetcher.fetch_market_context()

        if not market_context.success:
            logger.error(f"Market context fetch failed: {market_context.error_message}")
            return False

        logger.info(f"Market context retrieved for {len(market_context.market_data)} symbols")

        logger.info("Extracting sentiment embeddings...")
        sentiment_embedding = embedding_parser.extract_embeddings(market_context)

        if not sentiment_embedding.success:
            logger.error(f"Sentiment embedding extraction failed: {sentiment_embedding.error_message}")
            return False

        logger.info("Sentiment embeddings extracted successfully")

        print("\n" + "=" * 60)
        print("MARKET SENTIMENT ANALYSIS RESULTS (LEGACY PIPELINE)")
        print("=" * 60)
        print(f"Date (UTC): {sentiment_embedding.date.strftime('%Y-%m-%d %H:%M:%S%z')}")
        print(f"Model: {sentiment_embedding.model_version}")
        print()

        sorted_embeddings = sorted(
            sentiment_embedding.embeddings.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )

        print("Top market sentiments:")
        for i, (dim, value) in enumerate(sorted_embeddings[:5], 1):
            confidence = sentiment_embedding.confidence_scores.get(dim, 0.0)
            sentiment_type = "bullish" if value > 0.1 else "bearish" if value < -0.1 else "neutral"
            print(f"  {i}. {dim.replace('_', ' ').title()}: {value:+.2f} {sentiment_type} (confidence: {confidence:.1%})")

        print("\n" + "=" * 60)
        logger.info("Analysis completed at %s", datetime.now(timezone.utc).isoformat())
        return True

    except Exception as e:
        logger.exception("Analysis failed: %s", e)
        return False


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    print("market.legacy.main — LEGACY market sentiment analysis")
    print("(For the refined pipeline, see PLAN.md Slice 0.)")
    print()

    try:
        success = asyncio.run(run_market_analysis())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Analysis cancelled by user")
        sys.exit(130)


if __name__ == '__main__':
    main()

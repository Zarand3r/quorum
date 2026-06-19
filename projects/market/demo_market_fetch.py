#!/usr/bin/env python3
"""
LEGACY demo — pre-refinement 10-dimension sentiment-vector pipeline.

This script demos the original (pre-refinement) ``market.legacy`` pipeline,
kept for reference. It is NOT a demo of Slice 0 of the refined PLAN.md.

For the refined direction, see ``PLAN.md`` §12.1 (Slice 0) and
``docs/ELVES_SETUP.md``.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone


def print_banner():
    print("=" * 60)
    print("QUORUM — LEGACY market sentiment demo")
    print("  (Pre-refinement pipeline; see PLAN.md for the new direction.)")
    print("=" * 60)
    print()


def check_requirements() -> bool:
    if not os.getenv('OPENAI_API_KEY'):
        print("Missing required environment variable: OPENAI_API_KEY")
        print("  export OPENAI_API_KEY='your-openai-api-key'")
        return False
    return True


async def run_demo():
    try:
        from market.config.settings import AppConfig
        from market.legacy.embedding_agent.market_fetcher import MarketContextFetcher
        from market.legacy.embedding_agent.embedding_parser import EmbeddingParser
    except ImportError as e:
        print(f"Import error: {e}")
        print("  Run `uv sync --extra dev` from this directory first.")
        return

    config = AppConfig.load()
    print(f"OpenAI model: {config.api.openai_model}")
    print(f"Target symbols: {', '.join(config.market.target_symbols)}")
    print(f"Embedding dimensions: {len(config.market.embedding_dimensions)}")
    print()

    market_fetcher = MarketContextFetcher(config)
    embedding_parser = EmbeddingParser(config)

    connectivity = await market_fetcher.test_data_sources()
    for source, status in connectivity.items():
        print(f"  {source}: {'available' if status else 'unavailable'}")
    print()

    if not connectivity.get('llm', False):
        print("LLM not available — cannot proceed.")
        return

    print(f"Fetching market context at {datetime.now(timezone.utc).isoformat()} ...")
    market_context = await market_fetcher.fetch_market_context()
    if not market_context.success:
        print(f"Failed: {market_context.error_message}")
        return

    print(f"Market context retrieved for {len(market_context.market_data)} symbols.\n")
    for symbol, data in market_context.market_data.items():
        if 'error' in data:
            print(f"  {symbol}: ERROR — {data['error']}")
            continue
        price = data.get('current_price', 0.0)
        change = data.get('change_percent', 0.0)
        volume = data.get('volume', 0)
        print(f"  {symbol}: ${price:.2f} ({change:+.2f}%) vol={volume:,}")
    print()

    print("Extracting sentiment embeddings...")
    sentiment_embedding = embedding_parser.extract_embeddings(market_context)
    if not sentiment_embedding.success:
        print(f"Failed: {sentiment_embedding.error_message}")
        return

    print("Extracted embeddings:\n")
    print(embedding_parser.get_embedding_summary(sentiment_embedding))


def main():
    print_banner()
    if not check_requirements():
        sys.exit(1)
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()

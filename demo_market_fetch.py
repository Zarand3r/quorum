#!/usr/bin/env python3
"""
Demo script for LLM Market Fetch functionality.

This script demonstrates the complete market sentiment analysis pipeline
without requiring complex setup.
"""

import os
import sys
import asyncio
from datetime import datetime

# Ensure we can import the pelosi package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_banner():
    """Print demo banner."""
    print("=" * 60)
    print("🚀 PELOSI MARKET SENTIMENT FORECASTING SERVICE")
    print("   LLM Market Fetch Demo")
    print("=" * 60)
    print()

def check_requirements():
    """Check if required environment variables are set."""
    missing = []
    
    if not os.getenv('OPENAI_API_KEY'):
        missing.append('OPENAI_API_KEY')
    
    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print()
        print("Please set the required variables:")
        print("   export OPENAI_API_KEY='your-openai-api-key'")
        print()
        return False
    
    return True

async def run_demo():
    """Run the market fetch demo."""
    try:
        from pelosi.config.settings import AppConfig
        from pelosi.embedding_agent.market_fetcher import MarketContextFetcher
        from pelosi.embedding_agent.embedding_parser import EmbeddingParser
        
        print("📋 Loading Configuration...")
        config = AppConfig.load()
        print(f"   ✅ OpenAI Model: {config.api.openai_model}")
        print(f"   ✅ Target Symbols: {', '.join(config.market.target_symbols)}")
        print(f"   ✅ Embedding Dimensions: {len(config.market.embedding_dimensions)}")
        print()
        
        print("🔧 Initializing Components...")
        market_fetcher = MarketContextFetcher(config)
        embedding_parser = EmbeddingParser(config)
        print("   ✅ Market Context Fetcher initialized")
        print("   ✅ Embedding Parser initialized")
        print()
        
        print("🌐 Testing Data Source Connectivity...")
        connectivity = await market_fetcher.test_data_sources()
        for source, status in connectivity.items():
            icon = "✅" if status else "❌"
            print(f"   {icon} {source.upper()}: {'Available' if status else 'Unavailable'}")
        print()
        
        if not connectivity.get('llm', False):
            print("⚠️  LLM not available - cannot proceed with full demo")
            return
        
        print("📊 Fetching Real-Time Market Context...")
        print("   This may take 30-60 seconds...")
        
        market_context = await market_fetcher.fetch_market_context()
        
        if not market_context.success:
            print(f"   ❌ Failed: {market_context.error_message}")
            return
        
        print("   ✅ Market context retrieved successfully!")
        print(f"   📅 Analysis Date: {market_context.date.strftime('%Y-%m-%d %H:%M')}")
        print(f"   📈 Symbols Analyzed: {len(market_context.market_data)}")
        print()
        
        print("💰 Market Data Summary:")
        for symbol, data in market_context.market_data.items():
            if 'error' not in data:
                price = data.get('current_price', 0)
                change = data.get('change_percent', 0)
                volume = data.get('volume', 0)
                trend = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                print(f"   {trend} {symbol}: ${price:.2f} ({change:+.2f}%) | Vol: {volume:,}")
        print()
        
        if market_context.key_events:
            print("🔥 Key Market Events Identified:")
            for i, event in enumerate(market_context.key_events[:3], 1):
                print(f"   {i}. {event}")
            print()
        
        print("🧠 Extracting Sentiment Embeddings...")
        print("   Using LLM to quantify market sentiment...")
        
        sentiment_embedding = embedding_parser.extract_embeddings(market_context)
        
        if not sentiment_embedding.success:
            print(f"   ❌ Failed: {sentiment_embedding.error_message}")
            return
        
        print("   ✅ Sentiment embeddings extracted!")
        print()
        
        print("📊 SENTIMENT ANALYSIS RESULTS")
        print("-" * 40)
        print(f"Model: {sentiment_embedding.model_version}")
        print(f"Date: {sentiment_embedding.date.strftime('%Y-%m-%d')}")
        print()
        
        # Show most significant sentiments
        sorted_sentiments = sorted(
            sentiment_embedding.embeddings.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        print("🎯 Most Significant Market Sentiments:")
        for i, (dimension, value) in enumerate(sorted_sentiments[:5], 1):
            confidence = sentiment_embedding.confidence_scores.get(dimension, 0.0)
            
            if value > 0.2:
                sentiment_icon = "🟢"
                sentiment_label = "BULLISH"
            elif value < -0.2:
                sentiment_icon = "🔴"
                sentiment_label = "BEARISH"
            else:
                sentiment_icon = "🟡"
                sentiment_label = "NEUTRAL"
            
            print(f"   {i}. {sentiment_icon} {dimension.replace('_', ' ').title()}")
            print(f"      Score: {value:+.2f} ({sentiment_label}) | Confidence: {confidence:.1%}")
        print()
        
        print("📈 Complete Embedding Vector:")
        print("   (Values range from -1.0 to +1.0)")
        for dim, value in sentiment_embedding.embeddings.items():
            bar_length = int(abs(value) * 10)
            bar_char = "█" if value > 0 else "▓"
            bar = bar_char * bar_length
            bar = bar.ljust(10)
            sign = "+" if value >= 0 else ""
            print(f"   {dim:25} {sign}{value:5.2f} |{bar}|")
        print()
        
        # Validation
        is_valid = embedding_parser.validate_embedding(sentiment_embedding)
        print(f"✅ Embedding Validation: {'PASSED' if is_valid else 'FAILED'}")
        print()
        
        print("🎉 DEMO COMPLETED SUCCESSFULLY!")
        print()
        print("💡 What happened:")
        print("   1. Fetched real-time market data for major indices")
        print("   2. Gathered recent financial news (simulated)")
        print("   3. Used GPT-4 to analyze market conditions")
        print("   4. Extracted quantified sentiment embeddings")
        print("   5. Validated the results")
        print()
        print("🚀 Next Steps:")
        print("   - These embeddings can be used for time series forecasting")
        print("   - Historical embeddings enable trend analysis")
        print("   - Predictions can be compared against actual outcomes")
        print("   - LLM can analyze prediction errors for improvement")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("   Make sure you've installed dependencies with: poetry install")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main entry point for the demo."""
    print_banner()
    
    if not check_requirements():
        return
    
    print("🚀 Starting LLM Market Fetch Demo...")
    print()
    
    # Run the async demo
    asyncio.run(run_demo())

if __name__ == "__main__":
    main() 
# Pelosi - Usage Guide

Simple guide for using the LLM Market Fetch functionality.

## 🚀 Quick Start

### 1. Set up Environment
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### 2. Install Dependencies
```bash
poetry install
```

### 3. Run the System
```bash
# Main demo
python demo_market_fetch.py

# Or use the CLI
python -m pelosi.main
```

## 🛠️ What It Does

The system:

1. **Fetches Market Data**: Gets real-time prices for major indices (SPY, QQQ, IWM, DIA)
2. **Analyzes with LLM**: Uses GPT-4 to analyze market conditions
3. **Extracts Embeddings**: Converts analysis into 10 sentiment scores:
   - `tech_earnings_momentum`
   - `AI_optimism`
   - `interest_rate_expectations`
   - `tariff_risk`
   - `retail_investor_sentiment`
   - `institutional_caution`
   - `valuation_concerns`
   - `macro_stability`
   - `market_liquidity`
   - `crowded_trades_risk`

## 📊 Example Output

```
🎯 MARKET SENTIMENT ANALYSIS RESULTS
============================================================
Date: 2024-01-15 14:30
Model: gpt-4

📊 Top Market Sentiments:
  1. AI Optimism: +0.85 🟢 Bullish (confidence: 90%)
  2. Valuation Concerns: -0.65 🔴 Bearish (confidence: 75%)
  3. Tech Earnings Momentum: +0.72 🟢 Bullish (confidence: 85%)
```

## 🧪 Running Tests

```bash
# All tests
poetry run pytest

# Just the core tests
poetry run pytest tests/unit/test_core.py -v

# Interactive test runner
python run_tests.py
```

## 🔍 Troubleshooting

### Common Issues

1. **"OpenAI API error"**
   - Check your API key: `export OPENAI_API_KEY='your-key'`
   - Verify you have API credits

2. **"No market data"**
   - Check internet connection
   - Try during market hours for better data

3. **Import errors**
   - Run from project root directory
   - Ensure `poetry install` completed successfully

## 💰 API Costs

Typical cost per analysis: **$0.07-0.20**
- Market analysis: ~$0.05-0.15
- Embedding extraction: ~$0.02-0.05

Monthly cost for daily analysis: **~$2-6** 
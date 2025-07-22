# 📈 Market Sentiment Forecasting Service
A daily-updating time series forecasting pipeline that uses LLM-based analysis to extract structured sentiment embeddings from financial news and stock context, predicts market movements using self-implemented forecasting models, and retroactively analyzes prediction errors to adapt its prompting strategy over time.

## 🚀 Project Overview
This service is designed to:
1. Gather market context daily using an LLM (e.g., ChatGPT) via API.
2. Extract vector embeddings representing the market sentiment for key features like AI optimism, tech earnings momentum, retail investor mood, etc.
3. Forecast future market sentiment or stock movement using a self-implemented multivariate time series model (e.g., LSTM or Transformer).
4. Compare predictions to actual outcomes (e.g., S&P 500, QQQ returns).
5. Conduct retrospective error analysis via LLM, prompting it to explain discrepancies and propose additional features or factors that could improve the model's next prompt and embedding generation.


## Example Embedding
{
  "tech_earnings_momentum": +0.8,
  "AI_optimism": +0.9,
  "interest_rate_expectations": +0.6,
  "tariff_risk": -0.2,
  "retail_investor_sentiment": +0.7,
  "institutional_caution": -0.4,
  "valuation_concerns": -0.5,
  "macro_stability": +0.3,
  "market_liquidity": +0.4,
  "crowded_trades_risk": -0.6
}
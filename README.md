# 📈 Market Sentiment Forecasting Service

A daily-updating time series forecasting pipeline that uses LLM-based analysis to extract structured sentiment embeddings from financial news and stock context, predicts market movements using self-implemented forecasting models, and retroactively analyzes prediction errors to adapt its prompting strategy over time.

## 🚀 Project Overview

This service is designed to:

1. **Gather market context daily** using an LLM (e.g., ChatGPT) via API
2. **Extract vector embeddings** representing market sentiment for key features like AI optimism, tech earnings momentum, retail investor mood, etc.
3. **Forecast future market sentiment** using self-implemented multivariate time series models (LSTM, Transformer, VAR)
4. **Compare predictions to actual outcomes** (e.g., S&P 500, QQQ returns)
5. **Conduct retrospective error analysis** via LLM to explain discrepancies and propose additional features for improved future predictions

## 🧠 Architecture

```
             ┌────────────┐
             │ Scheduler  │────────────┐
             └────┬───────┘            │
                  ▼                    ▼
        ┌─────────────────┐   ┌─────────────────┐
        │ LLM Market Fetch│   │ Market Data API │
        │ (news context)  │   │ (e.g., Yahoo)   │
        └──────┬──────────┘   └──────┬──────────┘
               ▼                     ▼
     ┌──────────────────────────────┐
     │ LLM Sentiment Embedding Gen  │  ← GPT prompt-to-vector
     └──────────┬───────────────────┘
                ▼
       ┌────────────────────┐
       │ Forecasting Module │  ← Self-implemented (LSTM, VAR, etc.)
       └────────┬───────────┘
                ▼
        ┌─────────────────────┐
        │ Prediction Storage  │ ← Lightweight DB (SQLite, Redis)
        └────────┬────────────┘
                 ▼
       ┌────────────────────┐
       │ Retrospective Eval │ ← Compares predicted vs actual
       └────┬───────────────┘
            ▼
  ┌────────────────────────────┐
  │ LLM Error Attribution Agent│ ← GPT explains why prediction failed
  └────────────────────────────┘
```

## 🧩 Components

### `embedding_agent/`
- Prompts LLM for market news and context
- Converts unstructured market information into structured sentiment vector embeddings
- Manages prompt engineering and response parsing

### `forecasting/`
- Implements multivariate time series models:
  - **LSTM**: Long Short-Term Memory networks for sequential patterns
  - **TCN**: Temporal Convolutional Networks for parallel processing
  - **Transformer**: Attention-based models for long-range dependencies
  - **Classical models**: VAR, ARIMA for baseline comparisons

### `retrospective/`
- Compares predictions to actual stock/index movements
- Calculates prediction accuracy metrics (MAE, RMSE, directional accuracy)
- Prompts LLM with discrepancies and context to explain prediction failures
- Generates insights for model improvement

### `storage/`
- Manages SQLite or Redis storage of:
  - Daily sentiment embeddings
  - Model predictions and confidence intervals
  - Actual market outcomes
  - LLM-generated error explanations and improvement suggestions

## 📊 Example Sentiment Embedding

```json
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
```

Each dimension is scaled from **-1** (strongly negative) to **+1** (strongly positive), representing key market sentiment factors used in financial modeling.

## 🛠️ Technical Stack

- **Python 3.10+**: Core implementation language
- **Flask**: Web API for service endpoints
- **OpenAI API**: LLM integration for context analysis and error attribution
- **SQLAlchemy**: Database ORM for prediction and embedding storage
- **PyTorch/TensorFlow**: Deep learning frameworks for time series models
- **pandas/numpy**: Data manipulation and numerical computations
- **yfinance/Alpha Vantage**: Market data APIs

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key
- Market data API access (optional: Yahoo Finance is free)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pelosi.git
cd pelosi

# Install dependencies using Poetry
poetry install

# Activate the virtual environment
poetry shell
```

### Configuration

```bash
# Set environment variables
export OPENAI_API_KEY="your-openai-api-key"
export MARKET_DATA_API_KEY="your-market-data-api-key"  # Optional
```

### Usage

```bash
# Run daily sentiment extraction and prediction
python -m pelosi.main --mode daily

# Run retrospective analysis on past predictions
python -m pelosi.main --mode retrospective --days 30

# Start the web API service
python -m pelosi.api
```

## 📈 Model Performance Tracking

The service tracks multiple performance metrics:

- **Directional Accuracy**: Percentage of correct up/down predictions
- **Mean Absolute Error (MAE)**: Average prediction error magnitude
- **Root Mean Square Error (RMSE)**: Penalizes larger prediction errors
- **Sharpe Ratio**: Risk-adjusted returns of prediction-based trading strategy

## 🔄 Continuous Improvement Loop

1. **Daily Execution**: Extract sentiment → Generate prediction → Store results
2. **Weekly Retrospective**: Compare predictions to actual outcomes
3. **LLM Error Analysis**: Identify missing factors or biased assumptions
4. **Prompt Refinement**: Update embedding extraction prompts based on insights
5. **Model Retraining**: Incorporate new features and retrain forecasting models

## 🧪 Testing

The project includes a comprehensive test suite with **62.78% coverage** across all core components.

### Test Structure

```
tests/
├── __init__.py
├── conftest.py                # Shared fixtures and test configuration
├── test_basic.py             # Basic functionality and import tests
└── unit/
    ├── __init__.py
    ├── test_config.py        # Configuration system tests
    ├── test_core.py          # Core component integration tests
    └── test_llm_client.py    # LLM client and rate limiting tests
```

### Running Tests

#### Basic Test Commands

```bash
# Activate virtual environment
source ~/virtualenvs/Pelosi/bin/activate

# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/unit/test_config.py -v

# Run tests by marker
python -m pytest -m unit        # Unit tests only
python -m pytest -m integration # Integration tests only
```

#### Using the Custom Test Runner

```bash
# Run all tests
python run_tests.py

# Run only unit tests
python run_tests.py --unit

# Run only integration tests  
python run_tests.py --integration

# Run with coverage report
python run_tests.py --coverage
```

#### Coverage Reports

```bash
# Generate coverage report
python -m pytest --cov=pelosi --cov-report=term-missing

# Generate HTML coverage report
python -m pytest --cov=pelosi --cov-report=html

# View HTML report (opens in browser)
open htmlcov/index.html
```

### Test Categories

#### 🔧 **Unit Tests** (`@pytest.mark.unit`)
- **Configuration Tests**: Environment loading, defaults, validation
- **LLM Client Tests**: API integration, rate limiting, error handling
- **Core Component Tests**: Market fetcher, embedding parser creation and basic functionality

#### 🔗 **Integration Tests** (`@pytest.mark.integration`)
- **Pipeline Tests**: End-to-end data flow from market fetching to embedding extraction
- **Component Interaction**: Testing how different modules work together

### Test Coverage Breakdown

| Component | Coverage | Description |
|-----------|----------|-------------|
| `pelosi/config/` | **100%** | Configuration system fully tested |
| `pelosi/embedding_agent/llm_client.py` | **89%** | LLM client with comprehensive error handling tests |
| `pelosi/embedding_agent/embedding_parser.py` | **66%** | Core parsing logic and validation |
| `pelosi/embedding_agent/market_fetcher.py` | **59%** | Market data collection and processing |
| `pelosi/main.py` | **0%** | CLI interface (not unit tested) |
| **Overall** | **62.78%** | Strong coverage of business logic |

### Test Features

- **Comprehensive Mocking**: External APIs (OpenAI, yfinance) are mocked for reliable testing
- **Async Testing**: Full support for async/await patterns with `pytest-asyncio`
- **Fixture Management**: Shared test data and configurations in `conftest.py`
- **Error Scenario Testing**: Network failures, API errors, malformed data handling
- **Rate Limiting Tests**: LLM client rate limiting and backoff strategies

### Adding New Tests

#### Creating Unit Tests
```python
# tests/unit/test_new_feature.py
import pytest
from pelosi.new_module import NewFeature

@pytest.mark.unit
class TestNewFeature:
    def test_basic_functionality(self):
        feature = NewFeature()
        assert feature.process() is not None
```

#### Creating Integration Tests
```python
# tests/integration/test_new_integration.py
import pytest
from pelosi.integration_module import IntegrationFeature

@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_flow(mock_app_config):
    feature = IntegrationFeature(mock_app_config)
    result = await feature.run_pipeline()
    assert result.success is True
```

### Test Configuration

The test suite is configured via `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --cov=pelosi
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=50
markers =
    unit: marks tests as unit tests
    integration: marks tests as integration tests
    slow: marks tests as slow tests that may take longer to run
    api: marks tests as requiring API access
```

### Continuous Integration

Tests are designed to run in CI/CD environments:
- No external API dependencies (all mocked)
- Deterministic test data
- Proper async handling
- Coverage reporting integration

## 🗂️ Project Structure

```
pelosi/
├── embedding_agent/
│   ├── __init__.py
│   ├── llm_client.py          # OpenAI API integration
│   ├── market_fetcher.py      # Market data collection and LLM analysis
│   └── embedding_parser.py    # LLM response parsing to structured embeddings
├── forecasting/
│   ├── __init__.py
│   ├── models/
│   │   ├── lstm.py           # LSTM implementation
│   │   ├── transformer.py    # Transformer model
│   │   └── classical.py      # VAR, ARIMA models
│   ├── trainer.py            # Model training pipeline
│   └── predictor.py          # Inference engine
├── retrospective/
│   ├── __init__.py
│   ├── evaluator.py          # Performance metrics
│   └── error_analyzer.py     # LLM-based error attribution
├── storage/
│   ├── __init__.py
│   ├── database.py           # SQLAlchemy models
│   └── cache.py              # Redis integration
├── api/
│   ├── __init__.py
│   └── app.py                # Flask API endpoints
├── config/
│   ├── __init__.py
│   └── settings.py           # Configuration management
├── main.py                   # CLI entry point
└── __init__.py
tests/
├── __init__.py
├── conftest.py              # Shared test fixtures
├── test_basic.py           # Basic functionality tests
└── unit/
    ├── __init__.py
    ├── test_config.py      # Configuration tests (100% coverage)
    ├── test_core.py        # Core component tests
    └── test_llm_client.py  # LLM client tests (89% coverage)
scripts/
├── demo_market_fetch.py    # Main demonstration script
└── run_tests.py           # Custom test runner
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## ⚠️ Disclaimer

This project is for educational and research purposes only. The predictions generated by this system should not be used as the sole basis for financial decisions. Always consult with qualified financial advisors and conduct your own research before making investment decisions.

## 🙋‍♂️ Support

For questions, issues, or contributions, please:
- Open an issue on GitHub
- Contact the maintainer at [your-email@example.com]
- Join our discussion forum [link-to-forum]
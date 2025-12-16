# TradingAgents: Multi-Agents LLM Financial Trading Framework

[![arXiv](https://img.shields.io/badge/arXiv-2412.20138-B31B1B?logo=arxiv)](https://arxiv.org/abs/2412.20138)
[![Discord](https://img.shields.io/badge/Discord-TradingResearch-7289da?logo=discord&logoColor=white&color=7289da)](https://discord.com/invite/hk9PGKShPK)
[![X Follow](https://img.shields.io/badge/X-TauricResearch-white?logo=x&logoColor=white)](https://x.com/TauricResearch)

TradingAgents is a multi-agent trading framework that mirrors the dynamics of real-world trading firms. By deploying specialized LLM-powered agents—from fundamental analysts, sentiment experts, and technical analysts, to traders and risk management teams—the platform collaboratively evaluates market conditions and informs trading decisions.

> **Disclaimer:** TradingAgents framework is designed for research purposes. Trading performance may vary based on many factors. [It is not intended as financial, investment, or trading advice.](https://tauric.ai/disclaimer/)

## Architecture

The framework decomposes complex trading tasks into specialized roles:

### Analyst Team
- **Fundamentals Analyst**: Evaluates company financials and performance metrics
- **Sentiment Analyst**: Analyzes social media and public sentiment
- **News Analyst**: Monitors global news and macroeconomic indicators
- **Technical Analyst**: Utilizes technical indicators (MACD, RSI, etc.)

### Researcher Team
- **Bull Researcher**: Advocates for bullish positions with supporting evidence
- **Bear Researcher**: Advocates for bearish positions and identifies risks
- Researchers engage in structured debates to balance gains against risks

### Trader Agent
- Composes reports from analysts and researchers
- Makes informed trading decisions on timing and magnitude

### Risk Management & Portfolio Manager
- **Risk Team**: Evaluates portfolio risk, volatility, and liquidity
- **Portfolio Manager**: Approves/rejects transaction proposals

## Installation

```bash
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents

# Create virtual environment
conda create -n tradingagents python=3.13
conda activate tradingagents

# Install dependencies
pip install -r requirements.txt
```

### Required APIs

```bash
export OPENAI_API_KEY=$YOUR_OPENAI_API_KEY
export ALPHA_VANTAGE_API_KEY=$YOUR_ALPHA_VANTAGE_API_KEY
```

Or create a `.env` file (see `.env.example`):
```bash
cp .env.example .env
```

**Note:** Free Alpha Vantage API available at [alphavantage.co](https://www.alphavantage.co/support/#api-key). TradingAgents requests have increased rate limits (60/min, no daily limit).

## Usage

### CLI

```bash
python -m cli.main
```

### Python API

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

ta = TradingAgentsGraph(debug=True, config=DEFAULT_CONFIG.copy())
_, decision = ta.propagate("NVDA", "2024-05-10")
print(decision)
```

### Custom Configuration

```python
config = DEFAULT_CONFIG.copy()
config["deep_think_llm"] = "gpt-4o"
config["quick_think_llm"] = "gpt-4o-mini"
config["max_debate_rounds"] = 2

config["data_vendors"] = {
    "core_stock_apis": "yfinance",
    "technical_indicators": "yfinance",
    "fundamental_data": "alpha_vantage",
    "news_data": "alpha_vantage",
}

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NVDA", "2024-05-10")
```

## New Analysis Modules

Enhanced analysis capabilities using **FREE data sources only**:

| Module | Description | Data Source |
|--------|-------------|-------------|
| **Backtesting** | Historical validation with Sharpe, Sortino, max drawdown | yfinance |
| **Risk Calculator** | VaR, CVaR, beta, volatility analysis | yfinance |
| **Position Sizer** | Kelly criterion, fixed fractional, volatility-based | Local |
| **Market Context** | Regime detection, sector ranking, peer comparison | yfinance |
| **SEC Filings** | 10-K, 10-Q, 8-K analysis | SEC EDGAR |
| **Confidence Scorer** | Multi-factor confidence calculation | Local |

### Example: Enhanced Analysis

```python
from tradingagents.analysis import IntegratedAnalyzer
from tradingagents.backtesting import BacktestEngine
from tradingagents.risk import RiskCalculator, PositionSizer

# Risk analysis
calculator = RiskCalculator()
metrics = calculator.calculate_risk_metrics("NVDA")

# Position sizing
sizer = PositionSizer(portfolio_value=100000)
positions = sizer.calculate_optimal_position(price, stop_loss_pct=0.05)

# Backtesting
engine = BacktestEngine(lookback_months=3)
result = engine.run_backtest("AAPL", recommendations)
```

See `examples/enhanced_analysis_example.py` for full usage.

## Contributing

We welcome contributions! Whether it's fixing bugs, improving documentation, or suggesting features. Join our community at [Tauric Research](https://tauric.ai/).

## Citation

```bibtex
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework},
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138},
}
```

# TradingAgents: Multi-Agents LLM Financial Trading Framework


TradingAgents is a multi-agent trading framework that mirrors the dynamics of real-world trading firms. By deploying specialized LLM-powered agents—from fundamental analysts, sentiment experts, and technical analysts, to traders and risk management teams—the platform collaboratively evaluates market conditions and informs trading decisions.

> **Disclaimer:** TradingAgents framework is designed for research purposes. Trading performance may vary based on many factors. It is not intended as financial, investment, or trading advice.

## Architecture

```
                              +------------------+
                              |   User Input     |
                              |  (Ticker, Date)  |
                              +--------+---------+
                                       |
                                       v
            +----------------------------------------------------------+
            |                    ANALYST TEAM                          |
            |  +-------------+  +-------------+  +------------------+  |
            |  | Fundamentals|  |  Sentiment  |  |    Technical     |  |
            |  |   Analyst   |  |   Analyst   |  |     Analyst      |  |
            |  +------+------+  +------+------+  +--------+---------+  |
            |         |                |                  |            |
            |  +------+------+         |                  |            |
            |  |    News     |         |                  |            |
            |  |   Analyst   |         |                  |            |
            |  +------+------+         |                  |            |
            +---------|----------------|------------------|------------+
                      |                |                  |
                      v                v                  v
            +----------------------------------------------------------+
            |                   RESEARCHER TEAM                        |
            |        +----------------+    +----------------+          |
            |        | Bull Researcher|<-->| Bear Researcher|          |
            |        | (Pro Growth)   |    | (Risk Focused) |          |
            |        +-------+--------+    +--------+-------+          |
            |                |     DEBATE      |                       |
            |                +--------+--------+                       |
            +-------------------------|--------------------------------+
                                      |
                                      v
            +----------------------------------------------------------+
            |                    TRADER AGENT                          |
            |     Synthesizes all reports, makes trading decision      |
            |              (BUY / SELL / HOLD + sizing)                |
            +-------------------------|--------------------------------+
                                      |
                                      v
            +----------------------------------------------------------+
            |                 RISK MANAGEMENT TEAM                     |
            |  +----------------+  +----------------+  +------------+  |
            |  | Aggressive Risk|  | Conservative  |  |  Neutral   |  |
            |  |    Analyst     |  | Risk Analyst  |  |  Analyst   |  |
            |  +-------+--------+  +-------+-------+  +-----+------+  |
            |          |     RISK DEBATE       |            |         |
            |          +-----------+-----------+------------+         |
            +----------------------|-----------------------------------+
                                   |
                                   v
            +----------------------------------------------------------+
            |                 PORTFOLIO MANAGER                        |
            |         Final approval/rejection of trade proposal       |
            |              Returns: Decision + Reasoning               |
            +----------------------------------------------------------+
```

### Agent Roles

| Team | Agent | Responsibility |
|------|-------|----------------|
| **Analysts** | Fundamentals | Evaluates company financials, earnings, balance sheets |
| | Sentiment | Analyzes social media and public sentiment |
| | News | Monitors global news and macroeconomic indicators |
| | Technical | Utilizes technical indicators (MACD, RSI, Bollinger) |
| **Researchers** | Bull | Advocates for bullish positions with evidence |
| | Bear | Identifies risks and bearish factors |
| **Trading** | Trader | Synthesizes reports, proposes trades |
| **Risk** | Risk Team | Evaluates portfolio risk, volatility, liquidity |
| | Portfolio Mgr | Final trade approval/rejection |

## Installation

### Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager that handles virtual environments automatically.

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (creates .venv automatically)
uv sync

# Run commands with uv
uv run python -m cli.main
uv run python api/main.py
```

## Environment Setup

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then configure your API keys:

```env
# Required: At least one LLM provider
OPENAI_API_KEY=sk-your-openai-key          # For GPT models
ANTHROPIC_API_KEY=sk-ant-your-key          # For Claude models
DEEPSEEK_API_KEY=your-deepseek-key         # For DeepSeek models (budget option)

# Required: Market data
ALPHA_VANTAGE_API_KEY=your-av-key          # Free at alphavantage.co

# Optional: Memory/learning features (requires OpenAI for embeddings)
USE_MEMORY=true                             # Set false to disable

# Optional: Redis caching
REDIS_HOST=localhost
REDIS_PORT=6379

# Optional: Debug mode
DEBUG_LOGGING=false
```

**Getting API Keys:**
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/
- **DeepSeek**: https://platform.deepseek.com/
- **Alpha Vantage**: https://www.alphavantage.co/support/#api-key (FREE)

## Usage

### CLI (Interactive Mode)

```bash
# Start interactive trading agent
uv run python -m cli.main

# Or with activated venv
source .venv/bin/activate
python -m cli.main

# The CLI will prompt for:
# - Stock ticker (e.g., NVDA, AAPL)
# - Analysis date
# - LLM provider preference
```

### Web UI (Frontend + Backend)

Start both servers to use the web interface:

```bash
# Terminal 1: Start the FastAPI backend server
./start-backend.sh
# Or manually:
uv run python api/main.py

# Terminal 2: Start the React frontend
./start-frontend.sh
# Or manually:
cd frontend && npm install && npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8001
- API Docs (Swagger): http://localhost:8001/docs

### Run Analysis Examples

```bash
# Run all enhanced analysis examples (backtesting, risk, SEC filings)
uv run python examples/enhanced_analysis_example.py

# Quick risk analysis for a stock
uv run python -c "
from backend.analysis import RiskCalculator
calc = RiskCalculator()
print(calc.generate_risk_report('NVDA'))
"

# Market context analysis
uv run python -c "
from backend.agents.analysts.market_context_analyst import MarketContextAnalyst
analyst = MarketContextAnalyst()
print(analyst.generate_report('AAPL'))
"

# SEC filings analysis
uv run python -c "
from backend.dataflows.sec_edgar import SECEdgarClient
client = SECEdgarClient()
print(client.generate_report('MSFT'))
"

# Backtest historical recommendations
uv run python -c "
from backend.backtesting import BacktestEngine
engine = BacktestEngine(lookback_months=3)
recs = [{'date': '2024-10-01', 'decision': 'BUY'}, {'date': '2024-11-01', 'decision': 'HOLD'}]
result = engine.run_backtest('AAPL', recs)
print(engine.generate_report(result))
"
```

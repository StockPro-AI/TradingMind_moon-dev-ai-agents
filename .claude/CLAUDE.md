# TradingMind - Claude Code Project Guide

## Project Overview

TradingMind is a multi-agent LLM financial trading framework that simulates real-world trading firm dynamics. It deploys specialized LLM-powered agents that collaborate through debates to evaluate market conditions and inform trading decisions.

## Architecture

```
User Input (Ticker, Date)
    ↓
ANALYST TEAM (4 specialized agents)
    ├─ Market Analyst (technical indicators: MACD, RSI, Bollinger)
    ├─ Social Media Analyst (sentiment analysis)
    ├─ News Analyst (global news, insider info)
    └─ Fundamentals Analyst (financials, balance sheets)
    ↓
RESEARCHER TEAM (Bull/Bear debate)
    ├─ Bull Researcher (pro-growth arguments)
    └─ Bear Researcher (risk-focused arguments)
    ↓
TRADER AGENT (synthesizes reports, proposes trade)
    ↓
RISK MANAGEMENT TEAM (3-way risk debate)
    ├─ Aggressive Risk Analyst
    ├─ Conservative Risk Analyst
    └─ Neutral Risk Analyst
    ↓
PORTFOLIO MANAGER (final approval/rejection)
    ↓
Final Decision: BUY / SELL / HOLD
```

## Key Directories

```
backend/
├── agents/           # All agent implementations
│   ├── analysts/     # Market, News, Social, Fundamentals analysts
│   ├── researchers/  # Bull and Bear researchers
│   ├── trader/       # Trader agent
│   ├── managers/     # Research and Risk managers
│   ├── risk_debate/  # Aggressive, Conservative, Neutral debaters
│   └── utils/        # Agent utilities, tools, memory, states
├── graph/            # LangGraph workflow orchestration
│   ├── trading_graph.py  # Main TradingMindGraph class
│   ├── setup.py          # Graph node/edge configuration
│   └── conditional_logic.py  # Routing logic
├── dataflows/        # Data vendor integrations
│   ├── interface.py      # Vendor routing (route_to_vendor)
│   ├── y_finance.py      # yfinance integration
│   ├── alpha_vantage.py  # Alpha Vantage APIs
│   └── config.py         # Data vendor configuration
├── analysis/         # Analysis modules
│   ├── integrated_analyzer.py
│   ├── risk_calculator.py
│   └── position_sizer.py
└── default_config.py # Default configuration

api/                  # FastAPI backend server
cli/                  # Interactive CLI interface
frontend/             # React web UI
```

## Tech Stack

- **Agent Framework**: LangChain + LangGraph
- **LLM Providers**: OpenAI (GPT-4o), Anthropic (Claude), DeepSeek, Google
- **Data Sources**: yfinance, Alpha Vantage, Finnhub, SEC EDGAR
- **Vector DB**: ChromaDB (for agent memory/learning)
- **API Server**: FastAPI + Uvicorn
- **Frontend**: React + Vite + Tailwind

## Configuration

Key configuration in `backend/default_config.py`:

```python
DEFAULT_CONFIG = {
    "llm_provider": "openai",  # openai, anthropic, deepseek, google
    "deep_think_llm": "gpt-4o",
    "quick_think_llm": "gpt-4o-mini",
    "use_memory": True,  # ChromaDB learning system
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "data_vendors": {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "alpha_vantage",
        "news_data": "alpha_vantage",
    },
}
```

## Common Tasks

### Running Analysis
```bash
# CLI mode
uv run python -m cli.main

# API server
uv run python api/main.py

# Direct script
uv run python main.py
```

### Adding a New Agent
1. Create agent file in `backend/agents/<category>/`
2. Follow pattern: `create_<agent_name>(llm, memory=None)` function
3. Agent returns a node function that takes `state` and returns updated state
4. Register in `backend/agents/__init__.py`
5. Add to graph in `backend/graph/setup.py`

### Adding a New Data Vendor
1. Create vendor file in `backend/dataflows/`
2. Implement required functions (get_stock_data, get_indicators, etc.)
3. Register in `backend/dataflows/interface.py` VENDOR_METHODS dict
4. Add to VENDOR_LIST and configure in default_config.py

### Agent State Schema
Key state fields in `backend/agents/utils/agent_states.py`:
- `company_of_interest`: Ticker symbol
- `trade_date`: Analysis date
- `messages`: LangGraph message history
- `market_report`, `sentiment_report`, `news_report`, `fundamentals_report`
- `investment_debate_state`: Bull/Bear debate history
- `risk_debate_state`: Risk analyst debate history
- `final_trade_decision`: Final BUY/SELL/HOLD decision

## Code Conventions

- Use `@tool` decorator from `langchain_core.tools` for LangChain tools
- Agent nodes return dict with `messages` key and relevant report fields
- Use `route_to_vendor()` for all data fetching (abstraction layer)
- Memory system requires OpenAI API key for embeddings (even with other LLM providers)
- Use logging via `logging.getLogger('backend.<module>')`

## Environment Variables

Required:
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` or `DEEPSEEK_API_KEY`
- `ALPHA_VANTAGE_API_KEY` (for market data)

Optional:
- `USE_MEMORY=true/false` - Enable/disable ChromaDB learning
- `REDIS_HOST`, `REDIS_PORT` - Redis caching for API
- `DEBUG_LOGGING=true/false` - Verbose logging

## Testing

```bash
# Run analysis examples
uv run python examples/enhanced_analysis_example.py

# Quick risk analysis
uv run python -c "from backend.analysis import RiskCalculator; print(RiskCalculator().generate_risk_report('NVDA'))"
```

## Debugging Tips

1. Enable debug logging: Set `DEBUG_LOGGING=true` in `.env`
2. Check API rate limits: Alpha Vantage has 5 calls/min on free tier
3. Memory issues: Set `USE_MEMORY=false` to disable ChromaDB
4. View graph execution: Use `debug=True` in `TradingMindGraph()`

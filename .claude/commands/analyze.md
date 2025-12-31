Run a stock analysis using the TradingMind framework.

## Instructions

Analyze the stock ticker: $ARGUMENTS

1. First, check if the required environment is set up:
   - Verify `.env` file exists with API keys
   - Check that `uv` is available

2. Run the analysis using the CLI:
```bash
cd /Users/chong/moon-dev-ai-agents && uv run python -c "
from backend.graph.trading_graph import TradingMindGraph
from backend.default_config import DEFAULT_CONFIG
from datetime import date

ticker = '$ARGUMENTS' if '$ARGUMENTS' else 'AAPL'
graph = TradingMindGraph(config=DEFAULT_CONFIG, debug=False)
final_state, signal = graph.propagate(ticker, str(date.today()))
print('\\n=== ANALYSIS RESULT ===')
print(f'Ticker: {ticker}')
print(f'Signal: {signal}')
print(f'Decision: {final_state.get(\"final_trade_decision\", \"N/A\")}')
"
```

3. Summarize the results including:
   - The final trading decision (BUY/SELL/HOLD)
   - Key insights from each analyst
   - Risk assessment summary

Run a backtest for a stock ticker using historical data.

## Instructions

Backtest the stock: $ARGUMENTS

1. Run the backtest example:
```bash
cd /Users/chong/moon-dev-ai-agents && uv run python -c "
from backend.backtesting import BacktestEngine
from datetime import datetime, timedelta

ticker = '$ARGUMENTS' if '$ARGUMENTS' else 'AAPL'

# Create backtest engine with 3-month lookback
engine = BacktestEngine(lookback_months=3)

# Sample recommendations for testing
end_date = datetime.now()
start_date = end_date - timedelta(days=90)

# Generate sample trade recommendations
recs = [
    {'date': (start_date + timedelta(days=30)).strftime('%Y-%m-%d'), 'decision': 'BUY'},
    {'date': (start_date + timedelta(days=60)).strftime('%Y-%m-%d'), 'decision': 'HOLD'},
]

print(f'Running backtest for {ticker}...')
result = engine.run_backtest(ticker, recs)
print(engine.generate_report(result))
"
```

2. Analyze the backtest results:
   - Total return vs benchmark
   - Win rate and risk metrics
   - Recommendations for strategy improvement

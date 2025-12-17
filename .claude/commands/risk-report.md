Generate a quick risk analysis report for a stock.

## Instructions

Generate risk report for: $ARGUMENTS

```bash
cd /Users/chong/moon-dev-ai-agents && uv run python -c "
from backend.analysis import RiskCalculator

ticker = '$ARGUMENTS' if '$ARGUMENTS' else 'NVDA'
print(f'Generating risk report for {ticker}...')

calc = RiskCalculator()
report = calc.generate_risk_report(ticker)
print(report)
"
```

Summarize the key risk metrics and provide interpretation of the results.

Verify all API keys and data sources are properly configured.

## Instructions

Check the TradingMind API configuration:

1. Check environment variables:
```bash
cd /Users/chong/moon-dev-ai-agents && uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv()

print('=== API Key Status ===')
keys = {
    'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
    'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
    'DEEPSEEK_API_KEY': os.getenv('DEEPSEEK_API_KEY'),
    'ALPHA_VANTAGE_API_KEY': os.getenv('ALPHA_VANTAGE_API_KEY'),
    'FINNHUB_API_KEY': os.getenv('FINNHUB_API_KEY'),
}

for key, value in keys.items():
    status = 'SET' if value else 'NOT SET'
    masked = value[:8] + '...' if value and len(value) > 8 else value
    print(f'{key}: {status}' + (f' ({masked})' if value else ''))

print('\\n=== Memory Configuration ===')
use_memory = os.getenv('USE_MEMORY', 'true').lower() in ('true', '1', 'yes')
print(f'Memory enabled: {use_memory}')

print('\\n=== Redis Configuration ===')
redis_host = os.getenv('REDIS_HOST', 'not configured')
redis_port = os.getenv('REDIS_PORT', 'not configured')
print(f'Redis: {redis_host}:{redis_port}')
"
```

2. Test data vendor connectivity:
```bash
cd /Users/chong/moon-dev-ai-agents && uv run python -c "
import yfinance as yf
print('\\n=== Data Vendor Tests ===')

# Test yfinance
try:
    ticker = yf.Ticker('AAPL')
    info = ticker.info
    print(f'yfinance: OK (AAPL price: \${info.get(\"regularMarketPrice\", \"N/A\")})')
except Exception as e:
    print(f'yfinance: FAILED ({e})')
"
```

3. Report any missing or invalid configurations

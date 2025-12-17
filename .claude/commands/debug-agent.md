Debug agent state and memory for troubleshooting.

## Instructions

Debug the TradingAgents system:

1. Check ChromaDB memory status:
```bash
cd /Users/chong/moon-dev-ai-agents && uv run python -c "
import chromadb
from chromadb.config import Settings
import os

print('=== ChromaDB Memory Status ===')
try:
    client = chromadb.Client(Settings(allow_reset=True))
    collections = client.list_collections()
    print(f'Collections found: {len(collections)}')
    for col in collections:
        count = col.count()
        print(f'  - {col.name}: {count} memories')
except Exception as e:
    print(f'ChromaDB Error: {e}')
"
```

2. Check recent analysis logs:
```bash
cd /Users/chong/moon-dev-ai-agents && ls -la eval_results/ 2>/dev/null || echo "No eval_results directory found"
```

3. Validate agent imports:
```bash
cd /Users/chong/moon-dev-ai-agents && uv run python -c "
print('=== Agent Import Check ===')
try:
    from backend.agents import (
        create_market_analyst,
        create_news_analyst,
        create_social_media_analyst,
        create_fundamentals_analyst,
        create_bull_researcher,
        create_bear_researcher,
        create_trader,
        create_research_manager,
        create_risk_manager,
    )
    print('All agent imports: OK')
except ImportError as e:
    print(f'Import Error: {e}')

print('\\n=== Graph Import Check ===')
try:
    from backend.graph.trading_graph import TradingAgentsGraph
    print('TradingAgentsGraph import: OK')
except ImportError as e:
    print(f'Import Error: {e}')
"
```

4. Check default configuration:
```bash
cd /Users/chong/moon-dev-ai-agents && uv run python -c "
from backend.default_config import DEFAULT_CONFIG
import json
print('\\n=== Current Configuration ===')
# Print safe subset of config
safe_config = {k: v for k, v in DEFAULT_CONFIG.items() if 'key' not in k.lower()}
print(json.dumps(safe_config, indent=2, default=str))
"
```

5. Summarize any issues found and suggest fixes

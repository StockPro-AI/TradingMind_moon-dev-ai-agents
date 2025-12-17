import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    # Data directory - configurable via environment variable, defaults to ./data
    "data_dir": os.getenv("TRADINGAGENTS_DATA_DIR", os.path.join(os.path.dirname(__file__), "data")),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    # "llm_provider": "anthropic",  # Options: openai, anthropic, google, ollama, openrouter
    # "deep_think_llm": "claude-3-5-sonnet-20241022",  # For deep reasoning tasks
    # "quick_think_llm": "claude-3-5-haiku-20241022",  # For quick tasks
    # "backend_url": "https://api.anthropic.com",  # Not used for Anthropic, but kept for consistency
    "llm_provider": "openai",
    "deep_think_llm": "gpt-4o",
    "quick_think_llm": "gpt-4o-mini",
    "backend_url": "https://api.openai.com/v1",
    # Memory settings
    "use_memory": os.getenv("USE_MEMORY", "true").lower() in ("true", "1", "yes"),  # Set to False to disable memory/learning
    "max_memories": 1000,  # Maximum number of memories per agent
    "memory_ttl_days": 90,  # Days before memories expire
    "min_relevance_score": 0.5,  # Minimum similarity score for memory retrieval
    # Caching settings
    "enable_llm_cache": os.getenv("ENABLE_LLM_CACHE", "true").lower() in ("true", "1", "yes"),
    "llm_cache_ttl": 3600,  # LLM response cache TTL in seconds
    "data_cache_ttl": 1800,  # Data cache TTL in seconds (30 minutes)
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # Options: yfinance, alpha_vantage, local
        "technical_indicators": "yfinance",  # Options: yfinance, alpha_vantage, local
        "fundamental_data": "alpha_vantage", # Options: openai, alpha_vantage, local
        "news_data": "alpha_vantage",        # Options: openai, alpha_vantage, google, local
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
        # Example: "get_news": "openai",               # Override category default
    },
}

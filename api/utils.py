"""
Utility functions for the TradingAgents API.
Extracted to reduce code duplication and improve maintainability.
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional

# Configure module logger
logger = logging.getLogger("tradingagents.api")


def configure_provider(config: Dict[str, Any], provider: str) -> Dict[str, Any]:
    """Configure LLM provider-specific settings.

    Args:
        config: Base configuration dictionary (will be modified)
        provider: Provider name ('openai', 'deepseek', etc.)

    Returns:
        Modified config dict with provider-specific settings
    """
    if provider == "deepseek":
        config["backend_url"] = "https://api.deepseek.com/v1"
        config["deep_think_llm"] = "deepseek-chat"
        config["quick_think_llm"] = "deepseek-chat"
        config["api_key"] = os.getenv("DEEPSEEK_API_KEY")
        config["llm_provider"] = "deepseek"
        # Disable debate rounds for DeepSeek to avoid API compatibility issues
        config["max_debate_rounds"] = 0
        config["max_risk_discuss_rounds"] = 0
        # Skip Research Manager and Trader for DeepSeek due to API compatibility issues
        config["skip_research_manager"] = True
        config["skip_trader"] = True
    elif provider == "openai":
        config["backend_url"] = "https://api.openai.com/v1"
        config["deep_think_llm"] = "gpt-4o"
        config["quick_think_llm"] = "gpt-4o-mini"
        config["api_key"] = os.getenv("OPENAI_API_KEY")
        config["llm_provider"] = "openai"

    return config


def get_selected_analysts(provider: str) -> List[str]:
    """Get the list of analysts to use based on provider.

    Args:
        provider: Provider name

    Returns:
        List of analyst types to use
    """
    if provider == "deepseek":
        # For DeepSeek, only use market and social analysts to avoid API compatibility issues
        return ["market", "social"]
    else:
        # For other providers, use all analysts
        return ["market", "social", "news", "fundamentals"]


def extract_text(value) -> str:
    """Extract string content from various message formats.

    Handles:
    - Plain strings
    - Objects with .content attribute
    - Lists of content blocks (Anthropic format)
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if hasattr(value, 'content'):
        content = value.content
        if isinstance(content, list):
            return '\n'.join([
                item.get('text', '') if isinstance(item, dict) else str(item)
                for item in content
            ])
        return str(content)
    return str(value)


def categorize_by_headers(
    agent_name: str,
    content: str,
    categorized_content: Dict[str, List[Dict[str, str]]]
) -> None:
    """Parse content and organize by markdown headers.

    Modifies categorized_content in-place by adding entries under
    each discovered markdown header category.

    Args:
        agent_name: Name of the agent producing this content
        content: Markdown content to parse
        categorized_content: Dict to populate with categorized entries
    """
    if not content:
        return

    lines = content.split('\n')
    current_category = None
    current_content = []

    for line in lines:
        header_match = re.match(r'^(#{1,3})\s+(.+)$', line.strip())

        if header_match:
            # Save previous category
            if current_category and current_content:
                content_str = '\n'.join(current_content).strip()
                if content_str:
                    if current_category not in categorized_content:
                        categorized_content[current_category] = []
                    categorized_content[current_category].append({
                        "agent": agent_name,
                        "content": content_str
                    })

            # Start new category
            current_category = header_match.group(2).strip()
            current_content = []
        elif current_category:
            current_content.append(line)

    # Save last category
    if current_category and current_content:
        content_str = '\n'.join(current_content).strip()
        if content_str:
            if current_category not in categorized_content:
                categorized_content[current_category] = []
            categorized_content[current_category].append({
                "agent": agent_name,
                "content": content_str
            })


def process_analysis_reports(
    log_data: Dict[str, Any],
    categorized_content: Dict[str, List[Dict[str, str]]]
) -> None:
    """Process all agent reports and categorize their content.

    Args:
        log_data: Raw log data from analysis containing reports
        categorized_content: Dict to populate with categorized entries
    """
    # Analyst Team Reports
    report_mappings = [
        ("market_report", "Market Analyst", "Market Analysis"),
        ("sentiment_report", "Social Analyst", "Sentiment Analysis"),
        ("news_report", "News Analyst", "News Analysis"),
        ("fundamentals_report", "Fundamentals Analyst", "Fundamental Analysis"),
    ]

    for report_key, agent_name, fallback_category in report_mappings:
        if log_data.get(report_key):
            text = extract_text(log_data[report_key])
            categorize_by_headers(agent_name, text, categorized_content)
        else:
            categorized_content[fallback_category] = [{
                "agent": agent_name,
                "content": "Data not available"
            }]

    # Investment debate
    debate_state = log_data.get("investment_debate_state", {})
    if debate_state.get("judge_decision"):
        judge_text = extract_text(debate_state["judge_decision"])
        categorize_by_headers("Research Manager", judge_text, categorized_content)

    # Trader
    if log_data.get("trader_investment_decision"):
        trader_text = extract_text(log_data["trader_investment_decision"])
        categorize_by_headers("Trader", trader_text, categorized_content)

    # Risk debate
    risk_state = log_data.get("risk_debate_state", {})
    if risk_state.get("judge_decision"):
        risk_judge_text = extract_text(risk_state["judge_decision"])
        categorize_by_headers("Risk Manager", risk_judge_text, categorized_content)

    # Final decision
    if log_data.get("final_trade_decision"):
        final_text = extract_text(log_data["final_trade_decision"])
        categorize_by_headers("Portfolio Manager", final_text, categorized_content)

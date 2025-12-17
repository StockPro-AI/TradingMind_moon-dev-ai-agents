"""
Claude-optimized prompting utilities.

This module provides prompt templates and utilities optimized for
Claude's capabilities including:
- XML-structured prompts for better parsing
- System prompt best practices
- Tool use optimization
- Streaming-friendly formatting
"""

from typing import Dict, Any, List, Optional
import json


# Claude-optimized system prompts with XML structure
CLAUDE_SYSTEM_PREFIX = """You are an expert financial analyst AI assistant. You provide clear, actionable insights based on data-driven analysis.

<guidelines>
- Be concise but thorough
- Use specific numbers and data points to support arguments
- Acknowledge uncertainty when appropriate
- Structure your response with clear sections
- End with a clear, actionable recommendation
</guidelines>
"""


def format_analyst_prompt(
    role: str,
    task: str,
    context: Dict[str, str],
    past_memories: Optional[str] = None,
    provider: str = "openai"
) -> str:
    """Format an analyst prompt optimized for the LLM provider.

    Uses XML tags for Claude for better parsing, and standard
    formatting for other providers.

    Args:
        role: The analyst's role (e.g., "Bull Analyst", "News Analyst")
        task: Description of the analysis task
        context: Dictionary of context data (reports, history, etc.)
        past_memories: Optional past memory reflections
        provider: LLM provider ("anthropic", "openai", "deepseek", etc.)

    Returns:
        Formatted prompt string
    """
    if provider == "anthropic":
        return _format_claude_prompt(role, task, context, past_memories)
    else:
        return _format_standard_prompt(role, task, context, past_memories)


def _format_claude_prompt(
    role: str,
    task: str,
    context: Dict[str, str],
    past_memories: Optional[str] = None
) -> str:
    """Format a Claude-optimized prompt with XML structure."""
    prompt_parts = [f"<role>{role}</role>", "", f"<task>{task}</task>", ""]

    # Add context sections with XML tags
    prompt_parts.append("<context>")
    for key, value in context.items():
        if value:
            # Convert key to readable label
            label = key.replace("_", " ").title()
            prompt_parts.append(f"<{key}>")
            prompt_parts.append(f"{value}")
            prompt_parts.append(f"</{key}>")
            prompt_parts.append("")
    prompt_parts.append("</context>")

    # Add past memories if available
    if past_memories:
        prompt_parts.append("")
        prompt_parts.append("<past_lessons>")
        prompt_parts.append(past_memories)
        prompt_parts.append("</past_lessons>")

    # Add output instructions
    prompt_parts.append("")
    prompt_parts.append("<instructions>")
    prompt_parts.append("Analyze the provided context and deliver your assessment.")
    prompt_parts.append("Structure your response with clear sections.")
    prompt_parts.append("End with a definitive recommendation if applicable.")
    prompt_parts.append("</instructions>")

    return "\n".join(prompt_parts)


def _format_standard_prompt(
    role: str,
    task: str,
    context: Dict[str, str],
    past_memories: Optional[str] = None
) -> str:
    """Format a standard prompt for non-Claude providers."""
    prompt_parts = [
        f"**Role**: {role}",
        "",
        f"**Task**: {task}",
        "",
        "**Context**:",
    ]

    for key, value in context.items():
        if value:
            label = key.replace("_", " ").title()
            prompt_parts.append(f"\n### {label}")
            prompt_parts.append(value)

    if past_memories:
        prompt_parts.append("")
        prompt_parts.append("**Past Lessons & Reflections**:")
        prompt_parts.append(past_memories)

    prompt_parts.append("")
    prompt_parts.append("---")
    prompt_parts.append("Analyze the provided context and deliver your assessment with a clear recommendation.")

    return "\n".join(prompt_parts)


def format_debate_prompt(
    debater_role: str,
    position: str,  # "bull", "bear", "risky", "safe", "neutral"
    context: Dict[str, str],
    debate_history: str,
    opponent_argument: str,
    past_memories: Optional[str] = None,
    provider: str = "openai"
) -> str:
    """Format a debate-style prompt for researcher agents.

    Args:
        debater_role: Role name (e.g., "Bull Researcher")
        position: The position being argued
        context: Dictionary of market/company context
        debate_history: Full debate history
        opponent_argument: The last argument from opponent
        past_memories: Past lessons learned
        provider: LLM provider

    Returns:
        Formatted debate prompt
    """
    position_guidelines = {
        "bull": """Focus on:
- Growth potential and market opportunities
- Competitive advantages and moats
- Positive financial indicators and trends
- Counter bearish arguments with specific data""",
        "bear": """Focus on:
- Risk factors and downside scenarios
- Competitive threats and market headwinds
- Financial concerns and red flags
- Challenge bullish assumptions with evidence""",
        "risky": """Focus on:
- High-reward opportunities
- Acceptable risk levels for potential gains
- Market timing and momentum""",
        "safe": """Focus on:
- Capital preservation
- Risk mitigation strategies
- Conservative position sizing""",
        "neutral": """Focus on:
- Balanced risk-reward analysis
- Objective data assessment
- Moderate positioning recommendations""",
    }

    guidelines = position_guidelines.get(position, "Provide balanced analysis.")

    if provider == "anthropic":
        return f"""<role>{debater_role}</role>

<position_guidelines>
{guidelines}
</position_guidelines>

<market_context>
{json.dumps(context, indent=2) if isinstance(context, dict) else context}
</market_context>

<debate_history>
{debate_history}
</debate_history>

<opponent_last_argument>
{opponent_argument}
</opponent_last_argument>

{"<past_lessons>" + past_memories + "</past_lessons>" if past_memories else ""}

<instructions>
Engage directly with the opponent's points. Use specific data and evidence.
Present your argument conversationally, not as a list.
Build on the debate history to strengthen your position.
</instructions>"""
    else:
        return f"""**Role**: {debater_role}

**Position Guidelines**:
{guidelines}

**Market Context**:
{json.dumps(context, indent=2) if isinstance(context, dict) else context}

**Debate History**:
{debate_history}

**Opponent's Last Argument**:
{opponent_argument}

{f"**Past Lessons**: {past_memories}" if past_memories else ""}

---
Engage directly with the opponent's points. Use specific data and evidence.
Present your argument conversationally, not as a list.
"""


def format_tool_response(
    tool_name: str,
    result: Any,
    provider: str = "openai"
) -> str:
    """Format a tool response for optimal LLM processing.

    Args:
        tool_name: Name of the tool that was called
        result: The tool's result
        provider: LLM provider

    Returns:
        Formatted tool response
    """
    if provider == "anthropic":
        return f"""<tool_result name="{tool_name}">
{result}
</tool_result>"""
    else:
        return f"""**{tool_name} Result**:
{result}"""


def get_claude_tool_config() -> Dict[str, Any]:
    """Get Claude-optimized tool configuration.

    Returns configuration for Claude's native tool use that
    improves reliability and reduces hallucination.
    """
    return {
        "tool_choice": {"type": "auto"},
        # Claude works best with clear tool descriptions
        "system": """When using tools:
1. Call one tool at a time unless explicitly asked to batch
2. Wait for tool results before proceeding
3. If a tool fails, explain the error and suggest alternatives
4. Never fabricate tool results""",
    }


def optimize_for_claude(
    messages: List[Dict[str, str]],
    max_context_tokens: int = 150000
) -> List[Dict[str, str]]:
    """Optimize a message list for Claude's context window.

    Claude handles long contexts well but works best when:
    - Important information is at the start or end
    - Context is well-structured with clear sections

    Args:
        messages: List of message dicts
        max_context_tokens: Maximum context size (Claude supports 200K)

    Returns:
        Optimized message list
    """
    # For now, just ensure system message is first
    system_messages = [m for m in messages if m.get("role") == "system"]
    other_messages = [m for m in messages if m.get("role") != "system"]

    return system_messages + other_messages


# Analyst-specific prompt templates
ANALYST_TEMPLATES = {
    "market": {
        "role": "Technical Market Analyst",
        "task": """Analyze the technical market indicators and price action for the company.
Focus on trend analysis, momentum indicators, and key support/resistance levels.
Provide actionable insights for traders.""",
    },
    "news": {
        "role": "News and Macro Analyst",
        "task": """Analyze recent news, global events, and macroeconomic factors affecting the company.
Identify potential catalysts and risks from the news environment.
Assess market sentiment from media coverage.""",
    },
    "social": {
        "role": "Social Media Sentiment Analyst",
        "task": """Analyze social media sentiment and public perception of the company.
Identify trending topics, sentiment shifts, and potential viral factors.
Assess retail investor sentiment and momentum.""",
    },
    "fundamentals": {
        "role": "Fundamental Analyst",
        "task": """Analyze the company's financial health, valuation, and competitive position.
Review balance sheet, income statement, and cash flow metrics.
Assess growth prospects and intrinsic value.""",
    },
}


def get_analyst_template(analyst_type: str) -> Dict[str, str]:
    """Get the prompt template for a specific analyst type."""
    return ANALYST_TEMPLATES.get(analyst_type, {
        "role": f"{analyst_type.title()} Analyst",
        "task": f"Provide analysis as a {analyst_type} analyst.",
    })

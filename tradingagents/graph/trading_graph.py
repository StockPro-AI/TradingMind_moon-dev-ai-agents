# TradingAgents/graph/trading_graph.py

import os
from pathlib import Path
import json
from datetime import date
from typing import Dict, Any, Tuple, List, Optional, TYPE_CHECKING

# Lazy imports for LLM providers - only import what's needed to reduce startup time
# These are imported when the provider is actually used
if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_deepseek import ChatDeepSeek

from langgraph.prebuilt import ToolNode


def _get_openai_llm(**kwargs):
    """Lazy import and create OpenAI LLM instance."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(**kwargs)


def _get_anthropic_llm(**kwargs):
    """Lazy import and create Anthropic LLM instance."""
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(**kwargs)


def _get_google_llm(**kwargs):
    """Lazy import and create Google LLM instance."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(**kwargs)


def _get_deepseek_llm(**kwargs):
    """Lazy import and create DeepSeek LLM instance."""
    from langchain_deepseek import ChatDeepSeek
    return ChatDeepSeek(**kwargs)

from tradingagents.agents import *
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.agents.utils.memory import FinancialSituationMemory
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)
from tradingagents.dataflows.config import set_config

# Import the new abstract tool methods from agent_utils
from tradingagents.agents.utils.agent_utils import (
    get_stock_data,
    get_indicators,
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_news,
    get_insider_sentiment,
    get_insider_transactions,
    get_global_news
)

from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        debug=False,
        config: Dict[str, Any] = None,
        message_callback=None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
            message_callback: Optional callback function to be called with each message (agent_name, content)
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.message_callback = message_callback

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # Initialize LLMs using lazy imports to reduce startup time
        provider = self.config["llm_provider"].lower()

        if provider == "deepseek":
            # Use ChatDeepSeek for DeepSeek provider to avoid parameter incompatibility
            llm_kwargs = {
                "model": self.config["deep_think_llm"],
            }
            if "api_key" in self.config and self.config["api_key"]:
                llm_kwargs["api_key"] = self.config["api_key"]

            # Debug logging
            print(f"🔧 Initializing LLMs with provider: {provider}")
            print(f"🔧 Using ChatDeepSeek for DeepSeek compatibility")
            print(f"🔧 Deep think model: {llm_kwargs['model']}")
            print(f"🔧 API key present: {bool(llm_kwargs.get('api_key'))}")

            self.deep_thinking_llm = _get_deepseek_llm(**llm_kwargs)

            llm_kwargs["model"] = self.config["quick_think_llm"]
            print(f"🔧 Quick think model: {llm_kwargs['model']}")
            self.quick_thinking_llm = _get_deepseek_llm(**llm_kwargs)

        elif provider in ("openai", "ollama", "openrouter"):
            # Use api_key from config if provided, otherwise LangChain will use environment variable
            llm_kwargs = {
                "model": self.config["deep_think_llm"],
                "base_url": self.config["backend_url"]
            }
            if "api_key" in self.config and self.config["api_key"]:
                llm_kwargs["api_key"] = self.config["api_key"]

            # Debug logging
            print(f"🔧 Initializing LLMs with provider: {provider}")
            print(f"🔧 Deep think model: {llm_kwargs['model']}, base_url: {llm_kwargs['base_url']}")
            print(f"🔧 API key present: {bool(llm_kwargs.get('api_key'))}")

            self.deep_thinking_llm = _get_openai_llm(**llm_kwargs)

            llm_kwargs["model"] = self.config["quick_think_llm"]
            print(f"🔧 Quick think model: {llm_kwargs['model']}")
            self.quick_thinking_llm = _get_openai_llm(**llm_kwargs)

        elif provider == "anthropic":
            self.deep_thinking_llm = _get_anthropic_llm(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = _get_anthropic_llm(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])

        elif provider == "google":
            self.deep_thinking_llm = _get_google_llm(model=self.config["deep_think_llm"])
            self.quick_thinking_llm = _get_google_llm(model=self.config["quick_think_llm"])

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        
        # Initialize memories
        self.bull_memory = FinancialSituationMemory("bull_memory", self.config)
        self.bear_memory = FinancialSituationMemory("bear_memory", self.config)
        self.trader_memory = FinancialSituationMemory("trader_memory", self.config)
        self.invest_judge_memory = FinancialSituationMemory("invest_judge_memory", self.config)
        self.risk_manager_memory = FinancialSituationMemory("risk_manager_memory", self.config)

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # Initialize components
        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=self.config.get("max_debate_rounds", 1),
            max_risk_discuss_rounds=self.config.get("max_risk_discuss_rounds", 1)
        )
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.tool_nodes,
            self.bull_memory,
            self.bear_memory,
            self.trader_memory,
            self.invest_judge_memory,
            self.risk_manager_memory,
            self.conditional_logic,
            self.config,
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # Set up the graph
        self.graph = self.graph_setup.setup_graph(selected_analysts)

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Create tool nodes for different data sources using abstract methods."""
        return {
            "market": ToolNode(
                [
                    # Core stock data tools
                    get_stock_data,
                    # Technical indicators
                    get_indicators,
                ]
            ),
            "social": ToolNode(
                [
                    # News tools for social media analysis
                    get_news,
                ]
            ),
            "news": ToolNode(
                [
                    # News and insider information
                    get_news,
                    get_global_news,
                    get_insider_sentiment,
                    get_insider_transactions,
                ]
            ),
            "fundamentals": ToolNode(
                [
                    # Fundamental analysis tools
                    get_fundamentals,
                    get_balance_sheet,
                    get_cashflow,
                    get_income_statement,
                ]
            ),
        }

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date."""

        self.ticker = company_name

        # Initialize state
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date
        )
        args = self.propagator.get_graph_args()

        try:
            if self.debug or self.message_callback:
                # Debug mode or streaming mode with tracing
                trace = []
                for chunk in self.graph.stream(init_agent_state, **args):
                    # Store current state continuously in case of failure
                    self.curr_state = chunk

                    if len(chunk["messages"]) == 0:
                        pass
                    else:
                        last_message = chunk["messages"][-1]

                        if self.debug:
                            last_message.pretty_print()

                        # Call the message callback if provided
                        if self.message_callback:
                            # Pass the entire chunk so the callback can parse it properly
                            self.message_callback(chunk, last_message)

                        trace.append(chunk)

                final_state = trace[-1]
            else:
                # Standard mode without tracing
                final_state = self.graph.invoke(init_agent_state, **args)
                self.curr_state = final_state

            # Log state
            self._log_state(trade_date, final_state)

            # Return decision and processed signal
            return final_state, self.process_signal(final_state["final_trade_decision"])
        except Exception as e:
            # If we have partial state, log it before re-raising
            if hasattr(self, 'curr_state') and self.curr_state:
                # Try to log partial state
                try:
                    self._log_state(trade_date, self.curr_state)
                except (IOError, OSError, KeyError, TypeError) as log_error:
                    # Ignore expected logging errors (file issues, missing keys, type mismatches)
                    print(f"Warning: Failed to log partial state: {type(log_error).__name__}")
            raise

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            "investment_debate_state": {
                "bull_history": final_state["investment_debate_state"]["bull_history"],
                "bear_history": final_state["investment_debate_state"]["bear_history"],
                "history": final_state["investment_debate_state"]["history"],
                "current_response": final_state["investment_debate_state"][
                    "current_response"
                ],
                "judge_decision": final_state["investment_debate_state"][
                    "judge_decision"
                ],
            },
            "trader_investment_decision": final_state["trader_investment_plan"],
            "risk_debate_state": {
                "risky_history": final_state["risk_debate_state"]["risky_history"],
                "safe_history": final_state["risk_debate_state"]["safe_history"],
                "neutral_history": final_state["risk_debate_state"]["neutral_history"],
                "history": final_state["risk_debate_state"]["history"],
                "judge_decision": final_state["risk_debate_state"]["judge_decision"],
            },
            "investment_plan": final_state["investment_plan"],
            "final_trade_decision": final_state["final_trade_decision"],
        }

        # Save to file
        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/full_states_log_{trade_date}.json",
            "w",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns_losses):
        """Reflect on decisions and update memory based on returns."""
        self.reflector.reflect_bull_researcher(
            self.curr_state, returns_losses, self.bull_memory
        )
        self.reflector.reflect_bear_researcher(
            self.curr_state, returns_losses, self.bear_memory
        )
        self.reflector.reflect_trader(
            self.curr_state, returns_losses, self.trader_memory
        )
        self.reflector.reflect_invest_judge(
            self.curr_state, returns_losses, self.invest_judge_memory
        )
        self.reflector.reflect_risk_manager(
            self.curr_state, returns_losses, self.risk_manager_memory
        )

    def process_signal(self, full_signal):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal)

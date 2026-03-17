"""
FastAPI backend for TradingMind
Provides REST API and WebSocket endpoints for real-time trading analysis
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import json
import asyncio
import threading
from pathlib import Path
import sys
import os
import re
from dotenv import load_dotenv
import redis
import hashlib
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Debug logging flag
DEBUG_LOGGING = os.getenv('DEBUG_LOGGING', 'false').lower() == 'true'

def debug_log(message: str):
    """Print debug message only if DEBUG_LOGGING is enabled"""
    if DEBUG_LOGGING:
        print(message)

# Verify critical environment variables
if not os.getenv('ANTHROPIC_API_KEY') and not os.getenv('OPENAI_API_KEY'):
    print("WARNING: No ANTHROPIC_API_KEY or OPENAI_API_KEY found in environment!")
    print(f"Looking for .env at: {env_path}")

# Add parent directory to path to import backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.graph.trading_graph import TradingMindGraph
from backend.default_config import DEFAULT_CONFIG
from api.utils import (
    extract_text,
    categorize_by_headers,
    process_analysis_reports,
    configure_provider,
    get_selected_analysts,
)

app = FastAPI(
    title="TradingMind API",
    description="Multi-Agent LLM Financial Trading Framework API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active trading graphs and WebSocket connections
active_connections: List[WebSocket] = []
trading_graphs: Dict[str, TradingMindGraph] = {}

# Initialize Redis client
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        decode_responses=True,
        socket_connect_timeout=5
    )
    # Test connection
    redis_client.ping()
    print("✅ Redis connected successfully")
except (redis.ConnectionError, redis.TimeoutError) as e:
    print(f"⚠️  Redis connection failed: {e}")
    print("   Caching will be disabled")
    redis_client = None

# Cache TTL (Time To Live) in seconds - 24 hours
CACHE_TTL = 86400


def generate_cache_key(ticker: str, date: str) -> str:
    """Generate a unique cache key based on ticker, date, and config"""
    # Create a hash of the config to include in the key
    return f"analysis:{ticker}:{date}"


def get_cached_result(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached analysis result from Redis"""
    if not redis_client:
        return None

    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            debug_log(f"✅ Cache hit for key: {cache_key}")
            return json.loads(cached_data)
    except Exception as e:
        print(f"⚠️  Redis get error: {e}")

    return None


def set_cached_result(cache_key: str, result: Dict[str, Any], ttl: int = CACHE_TTL):
    """Store analysis result in Redis cache"""
    if not redis_client:
        return

    try:
        redis_client.setex(
            cache_key,
            ttl,
            json.dumps(result)
        )
        debug_log(f"✅ Cached result with key: {cache_key} (TTL: {ttl}s)")
    except Exception as e:
        print(f"⚠️  Redis set error: {e}")


# Request/Response Models
class AnalysisRequest(BaseModel):
    ticker: str
    date: str  # Format: YYYY-MM-DD
    config: Optional[Dict[str, Any]] = None
    compare_providers: Optional[bool] = False  # If True, run with both OpenAI and DeepSeek


class AnalysisResponse(BaseModel):
    ticker: str
    date: str
    decision: str
    status: str
    message: Optional[str] = None


class ComparisonAnalysisResponse(BaseModel):
    ticker: str
    date: str
    openai_result: Optional[Dict[str, Any]] = None
    deepseek_result: Optional[Dict[str, Any]] = None
    status: str
    message: Optional[str] = None


class ConfigRequest(BaseModel):
    llm_provider: Optional[str] = None
    deep_think_llm: Optional[str] = None
    quick_think_llm: Optional[str] = None
    use_memory: Optional[bool] = None
    max_debate_rounds: Optional[int] = None
    max_risk_discuss_rounds: Optional[int] = None


class ConfigResponse(BaseModel):
    config: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    version: str
    config: Dict[str, Any]


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
                # Connection closed or lost - this is expected during disconnects
                debug_log(f"Broadcast to connection failed (expected during disconnect): {type(e).__name__}")


manager = ConnectionManager()


# API Endpoints
@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "config": {
            "llm_provider": DEFAULT_CONFIG["llm_provider"],
            "deep_think_llm": DEFAULT_CONFIG["deep_think_llm"],
            "quick_think_llm": DEFAULT_CONFIG["quick_think_llm"],
            "use_memory": DEFAULT_CONFIG["use_memory"],
        }
    }


@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    """Get current configuration"""
    return {"config": DEFAULT_CONFIG}


@app.post("/api/config", response_model=ConfigResponse)
async def update_config(request: ConfigRequest):
    """Update configuration"""
    config = DEFAULT_CONFIG.copy()

    if request.llm_provider:
        config["llm_provider"] = request.llm_provider
    if request.deep_think_llm:
        config["deep_think_llm"] = request.deep_think_llm
    if request.quick_think_llm:
        config["quick_think_llm"] = request.quick_think_llm
    if request.use_memory is not None:
        config["use_memory"] = request.use_memory
    if request.max_debate_rounds:
        config["max_debate_rounds"] = request.max_debate_rounds
    if request.max_risk_discuss_rounds:
        config["max_risk_discuss_rounds"] = request.max_risk_discuss_rounds

    return {"config": config}


@app.post("/api/analyze")
async def analyze_stock(request: AnalysisRequest):
    """
    Analyze a stock and return complete categorized analysis

    This endpoint:
    1. Runs complete analysis (all phases)
    2. Extracts and categorizes content by markdown headers
    3. Caches results in Redis for 24 hours
    4. Returns categorized content ready for display

    Returns:
        {
            "ticker": str,
            "date": str,
            "decision": str,
            "categorizedContent": {
                "Category Name": [
                    {"agent": "Agent Name", "content": "..."},
                    ...
                ],
                ...
            },
            "status": "success",
            "message": str,
            "cached_at": str (optional)
        }
    """
    try:
        # Use custom config or default
        config = request.config if request.config else DEFAULT_CONFIG.copy()

        # Generate cache key with provider if specified
        provider = config.get('llm_provider', DEFAULT_CONFIG.get('llm_provider', 'openai'))

        # Configure provider-specific settings
        configure_provider(config, provider)

        cache_key = f"analysis:{request.ticker}:{request.date}:{provider}"

        # Check cache first
        cached_result = get_cached_result(cache_key)
        if cached_result:
            debug_log(f"✅ Returning cached result for {request.ticker} on {request.date}")
            return {
                "ticker": request.ticker,
                "date": request.date,
                "decision": cached_result.get("decision", "HOLD"),
                "categorizedContent": cached_result.get("categorizedContent", {}),
                "status": "success",
                "message": f"Analysis loaded from cache (cached at {cached_result.get('cached_at', 'unknown')})",
                "cached_at": cached_result.get("cached_at")
            }

        # No cache found, run complete analysis
        debug_log(f"🔄 Running fresh analysis for {request.ticker} on {request.date}")

        # Initialize trading graph with appropriate analysts based on provider
        selected_analysts = get_selected_analysts(provider)
        debug_log(f"Using analysts: {selected_analysts}")

        ta = TradingMindGraph(debug=False, config=config, selected_analysts=selected_analysts)

        # Run analysis - handle partial failures gracefully
        try:
            final_state, decision = ta.propagate(request.ticker, request.date)
        except Exception as e:
            # If analysis fails for any reason, check if we have partial results
            print(f"⚠️ Analysis failed during execution: {str(e)}")
            # Check if we have any partial state stored
            if hasattr(ta, 'curr_state') and ta.curr_state:
                print("✅ Found partial results, continuing with available data")
                final_state = ta.curr_state
                # Try to get decision from partial state
                if final_state.get("final_trade_decision"):
                    decision = ta.process_signal(final_state["final_trade_decision"])
                else:
                    decision = "HOLD"  # Default decision if not available
            else:
                # No partial state available, re-raise the exception
                print("❌ No partial state available, re-raising exception")
                raise

        # Get log_states_dict which contains all the structured data
        # If we don't have log_data, try to extract from final_state
        log_data = ta.log_states_dict.get(request.date, {})
        if not log_data and final_state:
            # Use final_state directly if log_states_dict is empty
            log_data = final_state

        # DEBUG: Check if log_states_dict has data
        debug_log(f"DEBUG: log_states_dict keys: {list(ta.log_states_dict.keys())}")
        debug_log(f"DEBUG: request.date: {request.date}")
        debug_log(f"DEBUG: log_data keys: {list(log_data.keys()) if log_data else 'EMPTY'}")
        debug_log(f"DEBUG: log_data is empty: {not log_data}")

        # Parse and categorize content from log_states_dict using utility function
        categorized_content = {}
        process_analysis_reports(log_data, categorized_content)
        debug_log(f"DEBUG: Processed {len(categorized_content)} categories")

        # Cache the result
        cached_at = datetime.now().isoformat()
        cache_data = {
            "ticker": request.ticker,
            "date": request.date,
            "decision": decision,
            "categorizedContent": categorized_content,
            "cached_at": cached_at
        }
        set_cached_result(cache_key, cache_data)

        # DEBUG: Check final response
        response_data = {
            "ticker": request.ticker,
            "date": request.date,
            "decision": decision,
            "categorizedContent": categorized_content,
            "status": "success",
            "message": f"Analysis completed for {request.ticker}",
            "cached_at": cached_at
        }
        debug_log(f"DEBUG: Final response - decision: {decision}, categorizedContent has {len(categorized_content)} categories")

        return response_data
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error in analyze_stock: {error_traceback}")

        # Try to return partial results if available
        if 'ta' in locals() and hasattr(ta, 'curr_state') and ta.curr_state:
            print("⚠️ Analysis failed but returning partial results")
            try:
                final_state = ta.curr_state
                decision = ta.process_signal(final_state.get("final_trade_decision")) if final_state.get("final_trade_decision") else "HOLD"

                log_data = ta.log_states_dict.get(request.date, {}) or final_state
                categorized_content = {}

                # Add available data with N/A for missing
                if log_data.get("market_report"):
                    categorized_content["Market Analysis"] = [{"agent": "Market Analyst", "content": str(log_data["market_report"])}]
                else:
                    categorized_content["Market Analysis"] = [{"agent": "Market Analyst", "content": "Data not available"}]

                if log_data.get("sentiment_report"):
                    categorized_content["Sentiment Analysis"] = [{"agent": "Social Analyst", "content": str(log_data["sentiment_report"])}]
                else:
                    categorized_content["Sentiment Analysis"] = [{"agent": "Social Analyst", "content": "Data not available"}]

                if log_data.get("news_report"):
                    categorized_content["News Analysis"] = [{"agent": "News Analyst", "content": str(log_data["news_report"])}]
                else:
                    categorized_content["News Analysis"] = [{"agent": "News Analyst", "content": "Data not available"}]

                if log_data.get("fundamentals_report"):
                    categorized_content["Fundamental Analysis"] = [{"agent": "Fundamentals Analyst", "content": str(log_data["fundamentals_report"])}]
                else:
                    categorized_content["Fundamental Analysis"] = [{"agent": "Fundamentals Analyst", "content": "Data not available"}]

                return {
                    "ticker": request.ticker,
                    "date": request.date,
                    "decision": decision,
                    "categorizedContent": categorized_content,
                    "status": "partial",
                    "message": f"Analysis partially completed with errors: {str(e)}",
                    "cached_at": datetime.now().isoformat()
                }
            except Exception as partial_error:
                print(f"Failed to extract partial results: {partial_error}")

        # If no partial results available, raise the error
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare")
async def compare_analysis(request: AnalysisRequest):
    """
    Run analysis with both OpenAI and DeepSeek providers and return comparison

    This endpoint:
    1. Runs complete analysis with OpenAI configuration
    2. Runs complete analysis with DeepSeek configuration
    3. Returns both results for side-by-side comparison
    4. Caches both results independently

    Returns:
        {
            "ticker": str,
            "date": str,
            "openai_result": {
                "decision": str,
                "categorizedContent": {...},
                "provider": "openai"
            },
            "deepseek_result": {
                "decision": str,
                "categorizedContent": {...},
                "provider": "deepseek"
            },
            "status": "success",
            "message": str
        }
    """
    try:
        ticker = request.ticker
        date = request.date
        base_config = request.config if request.config else DEFAULT_CONFIG.copy()

        # Helper function to run analysis with specific provider
        async def run_with_provider(provider_name: str, llm_config: str):
            config = base_config.copy()
            configure_provider(config, provider_name)

            cache_key = f"analysis:{ticker}:{date}:{provider_name}"

            # Check cache first
            cached_result = get_cached_result(cache_key)
            if cached_result:
                debug_log(f"✅ Cache hit for {provider_name}: {cache_key}")
                return cached_result

            debug_log(f"🔄 Running {provider_name} analysis for {ticker} on {date}")

            # Initialize trading graph with appropriate analysts based on provider
            selected_analysts = get_selected_analysts(provider_name)
            debug_log(f"Using analysts for {provider_name}: {selected_analysts}")

            # Run analysis - handle partial failures gracefully
            ta = TradingMindGraph(debug=False, config=config, selected_analysts=selected_analysts)
            try:
                final_state, decision = ta.propagate(ticker, date)
            except Exception as e:
                # If analysis fails for any reason, check if we have partial results
                debug_log(f"⚠️ {provider_name} analysis failed during execution: {str(e)}")
                # Check if we have any partial state stored
                if hasattr(ta, 'curr_state') and ta.curr_state:
                    debug_log(f"✅ Found partial results for {provider_name}, continuing with available data")
                    final_state = ta.curr_state
                    # Try to get decision from partial state
                    if final_state.get("final_trade_decision"):
                        decision = ta.process_signal(final_state["final_trade_decision"])
                    else:
                        decision = "HOLD"  # Default decision if not available
                else:
                    # No partial state available, re-raise the exception
                    debug_log(f"❌ No partial state available for {provider_name}, re-raising exception")
                    raise

            # Extract and categorize using utility functions
            log_data = ta.log_states_dict.get(date, {})
            if not log_data and final_state:
                log_data = final_state
            categorized_content = {}
            process_analysis_reports(log_data, categorized_content)

            # Prepare result
            result = {
                "decision": decision,
                "categorizedContent": categorized_content,
                "provider": provider_name,
                "cached_at": datetime.now().isoformat()
            }

            # Cache result
            set_cached_result(cache_key, result)

            return result

        # Run both analyses
        openai_result = await run_with_provider("openai", "gpt-4")
        deepseek_result = await run_with_provider("deepseek", "deepseek-chat")

        return {
            "ticker": ticker,
            "date": date,
            "openai_result": openai_result,
            "deepseek_result": deepseek_result,
            "status": "success",
            "message": f"Comparison analysis completed for {ticker}"
        }

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error in compare_analysis: {error_traceback}")

        # Try to return partial results if available
        # Check if we have results from either provider
        partial_response = {
            "ticker": request.ticker,
            "date": request.date,
            "status": "partial",
            "message": f"Comparison analysis partially completed with errors: {str(e)}"
        }

        has_partial_results = False

        # Check if openai_result exists
        if 'openai_result' in locals() and openai_result:
            partial_response["openai_result"] = openai_result
            has_partial_results = True
            print("✅ Returning partial OpenAI results")
        else:
            # Try to extract from OpenAI provider if it failed mid-execution
            partial_response["openai_result"] = {
                "decision": "HOLD",
                "categorizedContent": {"Error": [{"agent": "System", "content": "OpenAI analysis could not be completed"}]},
                "provider": "openai",
                "cached_at": datetime.now().isoformat()
            }

        # Check if deepseek_result exists
        if 'deepseek_result' in locals() and deepseek_result:
            partial_response["deepseek_result"] = deepseek_result
            has_partial_results = True
            print("✅ Returning partial DeepSeek results")
        else:
            # Try to extract from DeepSeek provider if it failed mid-execution
            partial_response["deepseek_result"] = {
                "decision": "HOLD",
                "categorizedContent": {"Error": [{"agent": "System", "content": "DeepSeek analysis could not be completed"}]},
                "provider": "deepseek",
                "cached_at": datetime.now().isoformat()
            }

        # If we have at least one partial result, return it
        if has_partial_results:
            print(f"⚠️ Comparison analysis failed but returning partial results")
            return partial_response

        # If no partial results available, raise the error
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/analyze")
async def websocket_analyze(websocket: WebSocket):
    """
    WebSocket endpoint for real-time analysis updates
    Client sends: {"ticker": "NVDA", "date": "2024-05-10", "config": {...}}
    Server sends: {"type": "update", "agent": "market_analyst", "content": "..."}
    """
    await manager.connect(websocket)

    try:
        # Receive analysis request (only one per connection)
        data = await websocket.receive_json()
        ticker = data.get("ticker")
        analysis_date = data.get("date")
        config = data.get("config", DEFAULT_CONFIG.copy())

        if not ticker or not analysis_date:
            await manager.send_message({
                "type": "error",
                "message": "Missing ticker or date"
            }, websocket)
        else:
            # Generate cache key
            cache_key = generate_cache_key(ticker, analysis_date)

            # Check cache first
            cached_result = get_cached_result(cache_key)

            if cached_result:
                # Send start message
                await manager.send_message({
                    "type": "start",
                    "ticker": ticker,
                    "date": analysis_date,
                    "message": f"Loading cached analysis for {ticker} on {analysis_date}"
                }, websocket)

                # Send cached messages as updates
                for msg in cached_result.get("messages", []):
                    await manager.send_message(msg, websocket)
                    await asyncio.sleep(0.01)  # Small delay for smoother playback

                # Send completion message with cached data
                await manager.send_message({
                    "type": "complete",
                    "ticker": ticker,
                    "date": analysis_date,
                    "decision": cached_result["decision"],
                    "final_state": cached_result["final_state"]
                }, websocket)

                debug_log(f"✅ Served cached result for {ticker} on {analysis_date}")
                return

            # No cache found, proceed with analysis
            # Send start message
            await manager.send_message({
                "type": "start",
                "ticker": ticker,
                "date": analysis_date,
                "message": f"Starting analysis for {ticker} on {analysis_date}"
            }, websocket)

            # Initialize trading graph with debug mode and message callback
            try:
                # Store messages in a queue to be sent asynchronously
                message_queue = []

                # Helper to extract string content (handles various message formats)
                def extract_content_str(value):
                    """Extract string content from various message formats."""
                    if value is None:
                        return ""

                    result = ""

                    if isinstance(value, str):
                        result = value
                    elif hasattr(value, 'content'):
                        content = value.content

                        # If content is a list (Anthropic's format)
                        if isinstance(content, list):
                            text_parts = []
                            for item in content:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    text_parts.append(item.get('text', ''))
                                elif hasattr(item, 'text'):
                                    text_parts.append(item.text)
                            result = '\n'.join(text_parts) if text_parts else str(content)
                        # If content is a string
                        elif isinstance(content, str):
                            result = content
                        else:
                            result = str(content)
                    else:
                        result = str(value)

                    debug_log(f"Result extracted, length: {len(result)}")

                    # Fix: If content has markdown headers but no newlines, add them
                    if result and '\n' not in result and '###' in result:
                        # Add newlines before markdown headers
                        result = result.replace('### ', '\n\n### ')
                        result = result.replace('#### ', '\n\n#### ')
                        result = result.replace('##### ', '\n\n##### ')
                        # Add newlines before common section markers
                        result = result.replace(' --- ', '\n\n---\n\n')
                        # Clean up leading newlines
                        result = result.lstrip('\n')

                    return result

                # Create a synchronous callback that parses chunks like CLI does
                def message_callback(chunk, last_message):
                    """Callback to parse chunk and queue formatted messages"""
                    # Extract message content for logging
                    if hasattr(last_message, "content"):
                        content = extract_content_str(last_message.content)
                    else:
                        content = str(last_message)

                    # Parse chunk data like CLI does
                    # Analyst Team Reports
                    if "market_report" in chunk and chunk["market_report"]:
                        extracted_content = extract_content_str(chunk["market_report"])
                        debug_log(f"📊 Market Analyst - Content length: {len(extracted_content)}")
                        message_queue.append({
                            "type": "update",
                            "agent": "Market Analyst",
                            "content": extracted_content,
                            "timestamp": datetime.now().isoformat()
                        })

                    if "sentiment_report" in chunk and chunk["sentiment_report"]:
                        extracted_content = extract_content_str(chunk["sentiment_report"])
                        debug_log(f"📱 Social Analyst - Content length: {len(extracted_content)}")
                        message_queue.append({
                            "type": "update",
                            "agent": "Social Analyst",
                            "content": extracted_content,
                            "timestamp": datetime.now().isoformat()
                        })

                    if "news_report" in chunk and chunk["news_report"]:
                        message_queue.append({
                            "type": "update",
                            "agent": "News Analyst",
                            "content": extract_content_str(chunk["news_report"]),
                            "timestamp": datetime.now().isoformat()
                        })

                    if "fundamentals_report" in chunk and chunk["fundamentals_report"]:
                        message_queue.append({
                            "type": "update",
                            "agent": "Fundamentals Analyst",
                            "content": extract_content_str(chunk["fundamentals_report"]),
                            "timestamp": datetime.now().isoformat()
                        })

                    # Research Team - Investment Debate
                    if "investment_debate_state" in chunk and chunk["investment_debate_state"]:
                        debate_state = chunk["investment_debate_state"]

                        # Bull Researcher
                        if "bull_history" in debate_state and debate_state["bull_history"]:
                            bull_responses = debate_state["bull_history"].split("\n")
                            latest_bull = bull_responses[-1] if bull_responses else ""
                            if latest_bull:
                                message_queue.append({
                                    "type": "update",
                                    "agent": "Bull Researcher",
                                    "content": latest_bull,
                                    "timestamp": datetime.now().isoformat()
                                })

                        # Bear Researcher
                        if "bear_history" in debate_state and debate_state["bear_history"]:
                            bear_responses = debate_state["bear_history"].split("\n")
                            latest_bear = bear_responses[-1] if bear_responses else ""
                            if latest_bear:
                                message_queue.append({
                                    "type": "update",
                                    "agent": "Bear Researcher",
                                    "content": latest_bear,
                                    "timestamp": datetime.now().isoformat()
                                })

                        # Research Manager Decision
                        if "judge_decision" in debate_state and debate_state["judge_decision"]:
                            message_queue.append({
                                "type": "update",
                                "agent": "Research Manager",
                                "content": extract_content_str(debate_state["judge_decision"]),
                                "timestamp": datetime.now().isoformat()
                            })

                    # Trading Team
                    if "trader_investment_plan" in chunk and chunk["trader_investment_plan"]:
                        message_queue.append({
                            "type": "update",
                            "agent": "Trader",
                            "content": extract_content_str(chunk["trader_investment_plan"]),
                            "timestamp": datetime.now().isoformat()
                        })

                    # Risk Management Team - Risk Debate
                    if "risk_debate_state" in chunk and chunk["risk_debate_state"]:
                        risk_state = chunk["risk_debate_state"]

                        # Risky Analyst
                        if "current_risky_response" in risk_state and risk_state["current_risky_response"]:
                            message_queue.append({
                                "type": "update",
                                "agent": "Risky Analyst",
                                "content": extract_content_str(risk_state["current_risky_response"]),
                                "timestamp": datetime.now().isoformat()
                            })

                        # Safe Analyst
                        if "current_safe_response" in risk_state and risk_state["current_safe_response"]:
                            message_queue.append({
                                "type": "update",
                                "agent": "Safe Analyst",
                                "content": extract_content_str(risk_state["current_safe_response"]),
                                "timestamp": datetime.now().isoformat()
                            })

                        # Neutral Analyst
                        if "current_neutral_response" in risk_state and risk_state["current_neutral_response"]:
                            message_queue.append({
                                "type": "update",
                                "agent": "Neutral Analyst",
                                "content": extract_content_str(risk_state["current_neutral_response"]),
                                "timestamp": datetime.now().isoformat()
                            })

                        # Portfolio Manager (Risk Manager) Decision
                        if "judge_decision" in risk_state and risk_state["judge_decision"]:
                            message_queue.append({
                                "type": "update",
                                "agent": "Risk Manager",
                                "content": extract_content_str(risk_state["judge_decision"]),
                                "timestamp": datetime.now().isoformat()
                            })

                ta = TradingMindGraph(debug=True, config=config, message_callback=message_callback)

                # Send progress update
                await manager.send_message({
                    "type": "progress",
                    "stage": "initialization",
                    "message": "Initialized trading agents"
                }, websocket)

                # Check if connection is still open before starting analysis
                if websocket.client_state.name != "CONNECTED":
                    print(f"WebSocket disconnected before analysis started")
                    return

                # Run the analysis in a background thread while sending queued messages
                debug_log(f"Starting analysis for {ticker} on {analysis_date}")

                # Store result from thread
                result_holder = {"final_state": None, "decision": None, "error": None}

                def run_analysis():
                    """Run analysis in background thread"""
                    try:
                        final_state, decision = ta.propagate(ticker, analysis_date)
                        result_holder["final_state"] = final_state
                        result_holder["decision"] = decision
                    except Exception as e:
                        result_holder["error"] = e

                analysis_thread = threading.Thread(target=run_analysis)
                analysis_thread.start()

                # Send queued messages while analysis is running
                last_sent_index = 0
                while analysis_thread.is_alive():
                    # Send any new messages in the queue
                    if len(message_queue) > last_sent_index:
                        for msg in message_queue[last_sent_index:]:
                            await manager.send_message(msg, websocket)
                        last_sent_index = len(message_queue)

                    # Small delay to prevent busy waiting
                    await asyncio.sleep(0.1)

                # Send any remaining messages after analysis completes
                if len(message_queue) > last_sent_index:
                    for msg in message_queue[last_sent_index:]:
                        await manager.send_message(msg, websocket)

                # Wait for thread to complete
                analysis_thread.join()

                # Check for errors
                if result_holder["error"]:
                    raise result_holder["error"]

                final_state = result_holder["final_state"]
                decision = result_holder["decision"]
                debug_log(f"✅ Analysis complete for {ticker}: {decision}")

                # Helper function to extract content from messages
                def extract_content(value):
                    if value is None:
                        return ""
                    if isinstance(value, str):
                        return value
                    if hasattr(value, 'content'):
                        return str(value.content)
                    return str(value)

                # Send individual team reports as updates so they appear in team panels
                market_report = extract_content(final_state.get("market_report"))
                debug_log(f"Market Report length: {len(market_report)}")
                if market_report:
                    await manager.send_message({
                        "type": "update",
                        "agent": "Market Analyst",
                        "content": market_report,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)

                sentiment_report = extract_content(final_state.get("sentiment_report"))
                if sentiment_report:
                    await manager.send_message({
                        "type": "update",
                        "agent": "Social Analyst",
                        "content": sentiment_report,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)

                news_report = extract_content(final_state.get("news_report"))
                if news_report:
                    await manager.send_message({
                        "type": "update",
                        "agent": "News Analyst",
                        "content": news_report,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)

                fundamentals_report = extract_content(final_state.get("fundamentals_report"))
                if fundamentals_report:
                    await manager.send_message({
                        "type": "update",
                        "agent": "Fundamentals Analyst",
                        "content": fundamentals_report,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)

                investment_plan = extract_content(final_state.get("investment_plan"))
                if investment_plan:
                    await manager.send_message({
                        "type": "update",
                        "agent": "Research Manager",
                        "content": investment_plan,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)

                trader_plan = extract_content(final_state.get("trader_investment_plan"))
                if trader_plan:
                    await manager.send_message({
                        "type": "update",
                        "agent": "Trader",
                        "content": trader_plan,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)

                final_decision = extract_content(final_state.get("final_trade_decision"))
                if final_decision:
                    await manager.send_message({
                        "type": "update",
                        "agent": "Risk Manager",
                        "content": final_decision,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)

                # Prepare final state
                final_state_data = {
                    "market_report": market_report,
                    "fundamentals_report": fundamentals_report,
                    "news_report": news_report,
                    "sentiment_report": sentiment_report,
                    "investment_plan": investment_plan,
                    "trader_investment_plan": trader_plan,
                    "final_trade_decision": final_decision,
                }

                # Send completion message with all data
                await manager.send_message({
                    "type": "complete",
                    "ticker": ticker,
                    "date": analysis_date,
                    "decision": decision,
                    "final_state": final_state_data
                }, websocket)

                # Cache the results for future requests
                cache_data = {
                    "ticker": ticker,
                    "date": analysis_date,
                    "decision": decision,
                    "final_state": final_state_data,
                    "messages": message_queue,  # Store all messages for replay
                    "cached_at": datetime.now().isoformat()
                }
                debug_log(f"Caching result for {ticker} on {analysis_date}")
                set_cached_result(cache_key, cache_data)

            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Analysis error: {error_details}")  # Log to console
                await manager.send_message({
                    "type": "error",
                    "message": f"Analysis failed: {str(e)}",
                    "details": error_details
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def async_stream_graph(graph, init_state, args, websocket):
    """Helper function to stream graph execution asynchronously"""
    for chunk in graph.stream(init_state, **args):
        if len(chunk.get("messages", [])) > 0:
            last_message = chunk["messages"][-1]

            # Determine the agent/stage from the chunk
            agent_name = "unknown"
            content = str(last_message.content) if hasattr(last_message, 'content') else str(last_message)

            # Send update
            await manager.send_message({
                "type": "update",
                "agent": agent_name,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }, websocket)

            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.1)

        yield chunk


@app.get("/api/history/{ticker}")
async def get_history(ticker: str):
    """Get analysis history for a ticker"""
    try:
        history_dir = Path(f"eval_results/{ticker}/TradingAgentsStrategy_logs/")
        if not history_dir.exists():
            return {"ticker": ticker, "history": []}

        history = []
        for file_path in history_dir.glob("full_states_log_*.json"):
            with open(file_path, 'r') as f:
                data = json.load(f)
                history.append(data)

        return {"ticker": ticker, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models")
async def get_available_models():
    """Get list of available LLM models"""
    def fetch_ollama_models() -> List[str]:
        """Try to fetch local Ollama models, fallback to pragmatic defaults."""
        fallback_models = ["llama3.1", "llama3.2", "mistral", "phi3", "qwen2.5"]
        try:
            req = Request("http://localhost:11434/api/tags", method="GET")
            with urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))

            models = []
            for item in data.get("models", []):
                model_name = item.get("model")
                if model_name:
                    models.append(model_name)

            return models or fallback_models
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError, OSError) as e:
            debug_log(f"Ollama model discovery failed, using fallback: {e}")
            return fallback_models

    def fetch_lmstudio_models() -> List[str]:
        """Try to fetch local LM Studio models (OpenAI compatible), fallback to defaults."""
        fallback_models = [
            "local-model",
            "qwen2.5-7b-instruct",
            "llama-3.1-8b-instruct",
            "mistral-7b-instruct-v0.3"
        ]
        try:
            req = Request("http://localhost:1234/v1/models", method="GET")
            with urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))

            models = []
            for item in data.get("data", []):
                model_id = item.get("id")
                if model_id:
                    models.append(model_id)

            return models or fallback_models
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError, OSError) as e:
            debug_log(f"LM Studio model discovery failed, using fallback: {e}")
            return fallback_models

    return {
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-preview", "o1-mini", "o4-mini"],
        "openrouter": [
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.0-flash-001",
            "meta-llama/llama-3.1-70b-instruct"
        ],
        "anthropic": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ],
        "google": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"],
        "mistral": ["mistral-large-latest", "mistral-small-latest", "codestral-latest"],
        "ollama": fetch_ollama_models(),
        "lmstudio": fetch_lmstudio_models()
    }


if __name__ == "__main__":
    import uvicorn
    import signal
    import sys

    def signal_handler(sig, frame):
        print('\n\n🛑 Shutting down gracefully...')
        print('👋 Goodbye!')
        sys.exit(0)

    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("✅ Starting TradingAgents API server...")
    print("📡 Server: http://localhost:8001")
    print("📖 API Docs: http://localhost:8001/docs")
    print("⚠️  Press Ctrl+C to stop\n")

    try:
        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
    except KeyboardInterrupt:
        print('\n\n🛑 Server stopped by user')
        sys.exit(0)

"""
FastAPI backend for TradingAgents
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

# Add parent directory to path to import tradingagents
sys.path.insert(0, str(Path(__file__).parent.parent))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

app = FastAPI(
    title="TradingAgents API",
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
trading_graphs: Dict[str, TradingAgentsGraph] = {}

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


class AnalysisResponse(BaseModel):
    ticker: str
    date: str
    decision: str
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
            except:
                pass


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

        # Generate cache key
        cache_key = generate_cache_key(request.ticker, request.date)

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

        # Initialize trading graph
        ta = TradingAgentsGraph(debug=False, config=config)

        # Run analysis
        final_state, decision = ta.propagate(request.ticker, request.date)

        # Get log_states_dict which contains all the structured data
        log_data = ta.log_states_dict.get(request.date, {})

        # DEBUG: Check if log_states_dict has data
        debug_log(f"DEBUG: log_states_dict keys: {list(ta.log_states_dict.keys())}")
        debug_log(f"DEBUG: request.date: {request.date}")
        debug_log(f"DEBUG: log_data keys: {list(log_data.keys()) if log_data else 'EMPTY'}")
        debug_log(f"DEBUG: log_data is empty: {not log_data}")

        # Parse and categorize content from log_states_dict
        categorized_content = {}

        def extract_text(value):
            """Extract string from various formats"""
            if value is None:
                return ""
            if isinstance(value, str):
                return value
            if hasattr(value, 'content'):
                content = value.content
                if isinstance(content, list):
                    return '\n'.join([item.get('text', '') if isinstance(item, dict) else str(item) for item in content])
                return str(content)
            return str(value)

        def categorize_by_headers(agent_name: str, content: str):
            """Parse content and organize by markdown headers"""
            if not content:
                return

            lines = content.split('\n')
            current_category = None
            current_content = []

            for line in lines:
                # Check if line is a markdown header
                header_match = line.strip().match(r'^(#{1,3})\s+(.+)$') if hasattr(line.strip(), 'match') else None
                if not header_match:
                    import re
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

        # Process each agent's output
        if log_data.get("market_report"):
            market_text = extract_text(log_data["market_report"])
            debug_log(f"DEBUG: Market report extracted, length: {len(market_text)}")
            categorize_by_headers("Market Analyst", market_text)

        if log_data.get("sentiment_report"):
            sentiment_text = extract_text(log_data["sentiment_report"])
            debug_log(f"DEBUG: Sentiment report extracted, length: {len(sentiment_text)}")
            categorize_by_headers("Social Analyst", sentiment_text)

        if log_data.get("news_report"):
            news_text = extract_text(log_data["news_report"])
            debug_log(f"DEBUG: News report extracted, length: {len(news_text)}")
            categorize_by_headers("News Analyst", news_text)

        if log_data.get("fundamentals_report"):
            fundamentals_text = extract_text(log_data["fundamentals_report"])
            debug_log(f"DEBUG: Fundamentals report extracted, length: {len(fundamentals_text)}")
            categorize_by_headers("Fundamentals Analyst", fundamentals_text)

        # Investment debate
        debate_state = log_data.get("investment_debate_state", {})
        if debate_state.get("judge_decision"):
            judge_text = extract_text(debate_state["judge_decision"])
            debug_log(f"DEBUG: Investment judge decision extracted, length: {len(judge_text)}")
            categorize_by_headers("Research Manager", judge_text)

        # Trader
        if log_data.get("trader_investment_decision"):
            trader_text = extract_text(log_data["trader_investment_decision"])
            debug_log(f"DEBUG: Trader decision extracted, length: {len(trader_text)}")
            categorize_by_headers("Trader", trader_text)

        # Risk debate
        risk_state = log_data.get("risk_debate_state", {})
        if risk_state.get("judge_decision"):
            risk_judge_text = extract_text(risk_state["judge_decision"])
            debug_log(f"DEBUG: Risk judge decision extracted, length: {len(risk_judge_text)}")
            categorize_by_headers("Risk Manager", risk_judge_text)

        # Final decision
        if log_data.get("final_trade_decision"):
            final_text = extract_text(log_data["final_trade_decision"])
            debug_log(f"DEBUG: Final decision extracted, length: {len(final_text)}")
            categorize_by_headers("Portfolio Manager", final_text)

        # DEBUG: Check categorization results
        debug_log(f"DEBUG: categorized_content keys: {list(categorized_content.keys())}")
        debug_log(f"DEBUG: categorized_content is empty: {not categorized_content}")
        debug_log(f"DEBUG: Number of categories: {len(categorized_content)}")
        for category, items in categorized_content.items():
            debug_log(f"DEBUG: Category '{category}' has {len(items)} items")

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
        print(f"Error in analyze_stock: {traceback.format_exc()}")
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

                ta = TradingAgentsGraph(debug=True, config=config, message_callback=message_callback)

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
    return {
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-preview", "o1-mini", "o4-mini"],
        "anthropic": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ],
        "google": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"]
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

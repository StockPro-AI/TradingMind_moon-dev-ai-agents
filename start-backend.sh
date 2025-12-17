#!/bin/bash

# TradingAgents Backend Startup Script

set -e

echo "🚀 Starting TradingAgents Backend..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with your API keys:"
    echo "  cp .env.example .env"
    echo "  Then edit .env with your actual keys"
    exit 1
fi

# Check for required API keys
if ! grep -q "ANTHROPIC_API_KEY=" .env && ! grep -q "OPENAI_API_KEY=" .env && ! grep -q "DEEPSEEK_API_KEY=" .env; then
    echo "⚠️  Warning: No LLM API keys found in .env file"
fi

# Check if uv is installed
if command -v uv &> /dev/null; then
    echo "📦 Using uv for dependency management"

    # Sync dependencies if needed
    if [ ! -d ".venv" ]; then
        echo "📦 Installing dependencies..."
        uv sync
    fi

    echo ""
    echo "✅ Starting FastAPI server on http://localhost:8001"
    echo "📖 API Documentation: http://localhost:8001/docs"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo ""

    # Start the server with uv
    uv run python -m api.main
else
    echo "📦 uv not found, using pip"

    # Check if virtual environment exists
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        python -m venv .venv
    fi

    # Activate virtual environment
    source .venv/bin/activate

    # Install dependencies
    pip install -e . --quiet

    echo ""
    echo "✅ Starting FastAPI server on http://localhost:8001"
    echo "📖 API Documentation: http://localhost:8001/docs"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo ""

    # Start the server
    python -m api.main
fi

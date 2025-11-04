#!/bin/bash

# TradingAgents Backend Startup Script

echo "🚀 Starting TradingAgents Backend..."

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated!"
    echo "Activating venv..."
    source venv/bin/activate
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with your API keys:"
    echo "  cp .env.example .env"
    echo "  Then edit .env with your actual keys"
    exit 1
fi

# Check for required API keys
if ! grep -q "ANTHROPIC_API_KEY=" .env && ! grep -q "OPENAI_API_KEY=" .env; then
    echo "⚠️  Warning: No API keys found in .env file"
fi

# Install backend dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing backend dependencies..."
    pip install -r api/requirements.txt
fi

echo "✅ Starting FastAPI server on http://localhost:8001"
echo "📖 API Documentation: http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Trap Ctrl+C and cleanup
trap 'echo ""; echo "🛑 Stopping backend..."; exit 0' INT TERM

# Start the server
python -m api.main

# Cleanup on exit
echo ""
echo "✅ Backend stopped successfully"

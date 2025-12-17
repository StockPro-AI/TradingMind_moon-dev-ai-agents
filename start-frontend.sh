#!/bin/bash

# TradingAgents Frontend Startup Script

set -e

echo "🎨 Starting TradingAgents Frontend..."

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

echo ""
echo "✅ Starting development server on http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the dev server
npm run dev

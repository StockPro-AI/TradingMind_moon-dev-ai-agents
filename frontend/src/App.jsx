import React, { useState, useCallback } from 'react';
import { Activity, Github } from 'lucide-react';
import TickerInput from './components/TickerInput';
import AnalysisResults from './components/AnalysisResults';
import LoadingState from './components/LoadingState';
import ErrorState from './components/ErrorState';
import { analyzeStock } from './api/tradingApi';

function App() {
  const [analysisState, setAnalysisState] = useState('idle'); // idle, loading, success, error
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [currentTicker, setCurrentTicker] = useState('');
  const [loadingStage, setLoadingStage] = useState(0);

  const handleAnalyze = useCallback(async (ticker, date) => {
    setCurrentTicker(ticker);
    setAnalysisState('loading');
    setError(null);
    setResult(null);
    setLoadingStage(0);

    // Simulate loading stages (in reality, you'd use WebSocket for real-time updates)
    const stageInterval = setInterval(() => {
      setLoadingStage((prev) => (prev < 4 ? prev + 1 : prev));
    }, 15000); // Advance stage every 15 seconds

    try {
      const response = await analyzeStock(ticker, date);
      clearInterval(stageInterval);
      setResult(response);
      setAnalysisState('success');
    } catch (err) {
      clearInterval(stageInterval);
      console.error('Analysis failed:', err);
      setError(err);
      setAnalysisState('error');
    }
  }, []);

  const handleNewAnalysis = useCallback(() => {
    setAnalysisState('idle');
    setResult(null);
    setError(null);
    setCurrentTicker('');
  }, []);

  const handleRetry = useCallback(() => {
    if (currentTicker) {
      const today = new Date().toISOString().split('T')[0];
      handleAnalyze(currentTicker, today);
    } else {
      handleNewAnalysis();
    }
  }, [currentTicker, handleAnalyze, handleNewAnalysis]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-900 to-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Activity className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">TradingAgents</h1>
              <p className="text-xs text-gray-400">Multi-Agent AI Trading Analysis</p>
            </div>
          </div>

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 text-gray-400 hover:text-white transition-colors"
          >
            <Github className="h-6 w-6" />
          </a>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Hero Section - Show when idle */}
        {analysisState === 'idle' && (
          <div className="text-center mb-12 pt-8">
            <h2 className="text-4xl font-bold text-white mb-4">
              AI-Powered Stock Analysis
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto mb-8">
              Get comprehensive trading insights from our multi-agent AI system.
              Our analysts debate and collaborate to provide balanced recommendations.
            </p>

            <TickerInput onAnalyze={handleAnalyze} isLoading={false} />

            {/* Features */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 max-w-4xl mx-auto">
              <FeatureCard
                title="Technical Analysis"
                description="MACD, RSI, Bollinger Bands and more technical indicators analyzed"
                icon="📊"
              />
              <FeatureCard
                title="Sentiment Analysis"
                description="Social media and news sentiment to gauge market mood"
                icon="💬"
              />
              <FeatureCard
                title="Risk Assessment"
                description="Multi-perspective risk debate for balanced recommendations"
                icon="⚖️"
              />
            </div>
          </div>
        )}

        {/* Loading State */}
        {analysisState === 'loading' && (
          <LoadingState ticker={currentTicker} currentStage={loadingStage} />
        )}

        {/* Results */}
        {analysisState === 'success' && result && (
          <AnalysisResults result={result} onNewAnalysis={handleNewAnalysis} />
        )}

        {/* Error State */}
        {analysisState === 'error' && (
          <ErrorState error={error} onRetry={handleRetry} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-gray-500 text-sm">
          <p>
            <strong className="text-gray-400">Disclaimer:</strong> TradingAgents is for research purposes only.
            Not financial advice.
          </p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ title, description, icon }) {
  return (
    <div className="p-6 bg-gray-800/50 rounded-xl border border-gray-700 hover:border-gray-600 transition-colors">
      <div className="text-3xl mb-3">{icon}</div>
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      <p className="text-gray-400 text-sm">{description}</p>
    </div>
  );
}

export default App;

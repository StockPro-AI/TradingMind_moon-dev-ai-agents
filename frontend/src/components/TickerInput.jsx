import React, { useState } from 'react';
import { Search, TrendingUp, Loader2 } from 'lucide-react';

const popularTickers = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META'];

export default function TickerInput({ onAnalyze, isLoading }) {
  const [ticker, setTicker] = useState('');
  const [date, setDate] = useState(() => {
    // Default to today's date
    const today = new Date();
    return today.toISOString().split('T')[0];
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (ticker.trim() && !isLoading) {
      onAnalyze(ticker.trim().toUpperCase(), date);
    }
  };

  const handleQuickSelect = (selectedTicker) => {
    setTicker(selectedTicker);
    if (!isLoading) {
      onAnalyze(selectedTicker, date);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Main Input Form */}
      <form onSubmit={handleSubmit} className="mb-6">
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Ticker Input */}
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <TrendingUp className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="Enter ticker (e.g., AAPL)"
              className="block w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg
                         text-white placeholder-gray-400 focus:outline-none focus:ring-2
                         focus:ring-blue-500 focus:border-transparent transition-all"
              disabled={isLoading}
              maxLength={10}
            />
          </div>

          {/* Date Input */}
          <div className="sm:w-44">
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="block w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg
                         text-white focus:outline-none focus:ring-2 focus:ring-blue-500
                         focus:border-transparent transition-all"
              disabled={isLoading}
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!ticker.trim() || isLoading}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700
                       disabled:cursor-not-allowed text-white font-medium rounded-lg
                       transition-all flex items-center justify-center gap-2 min-w-[120px]"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <Search className="h-5 w-5" />
                <span>Analyze</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Quick Select Buttons */}
      <div className="flex flex-wrap gap-2 justify-center">
        <span className="text-gray-400 text-sm mr-2 self-center">Quick:</span>
        {popularTickers.map((t) => (
          <button
            key={t}
            onClick={() => handleQuickSelect(t)}
            disabled={isLoading}
            className={`px-3 py-1.5 text-sm rounded-full transition-all
              ${ticker === t
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white'}
              disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {t}
          </button>
        ))}
      </div>
    </div>
  );
}

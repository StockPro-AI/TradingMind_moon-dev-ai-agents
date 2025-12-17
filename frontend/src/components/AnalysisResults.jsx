import React from 'react';
import { Clock, RefreshCw } from 'lucide-react';
import DecisionBadge from './DecisionBadge';
import CategorySection from './CategorySection';

// Order categories for display
const categoryOrder = [
  'Market Analysis',
  'Sentiment Analysis',
  'News Analysis',
  'Fundamental Analysis',
  'Research Debate',
  'Investment Recommendation',
  'Trading Decision',
  'Risk Assessment',
  'Final Decision',
];

export default function AnalysisResults({ result, onNewAnalysis }) {
  if (!result) return null;

  const { ticker, date, decision, categorizedContent, cached_at, message } = result;

  // Sort categories according to defined order
  const sortedCategories = Object.keys(categorizedContent || {}).sort((a, b) => {
    const indexA = categoryOrder.indexOf(a);
    const indexB = categoryOrder.indexOf(b);
    // If not in order list, put at end
    if (indexA === -1) return 1;
    if (indexB === -1) return -1;
    return indexA - indexB;
  });

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-8">
        <div className="text-center sm:text-left">
          <h1 className="text-3xl font-bold text-white">
            {ticker}
            <span className="text-gray-500 text-lg ml-2">Analysis</span>
          </h1>
          <div className="flex items-center gap-2 text-gray-400 mt-1">
            <Clock className="h-4 w-4" />
            <span>{date}</span>
            {cached_at && (
              <span className="text-xs bg-gray-700 px-2 py-0.5 rounded">
                Cached
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <DecisionBadge decision={decision} />
          <button
            onClick={onNewAnalysis}
            className="p-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            title="New Analysis"
          >
            <RefreshCw className="h-5 w-5 text-gray-400" />
          </button>
        </div>
      </div>

      {/* Message if present */}
      {message && (
        <div className="mb-6 p-4 bg-blue-900/30 border border-blue-700 rounded-lg">
          <p className="text-blue-300 text-sm">{message}</p>
        </div>
      )}

      {/* Analysis Categories */}
      <div className="space-y-2">
        {sortedCategories.map((category) => (
          <CategorySection
            key={category}
            category={category}
            agents={categorizedContent[category]}
          />
        ))}
      </div>

      {/* No content fallback */}
      {sortedCategories.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p>No detailed analysis available.</p>
          <p className="text-sm mt-2">Decision: {decision}</p>
        </div>
      )}
    </div>
  );
}

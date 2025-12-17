import React from 'react';
import { Loader2, Brain, TrendingUp, MessageSquare, FileText, Users } from 'lucide-react';

const loadingStages = [
  { icon: TrendingUp, label: 'Market Analyst', description: 'Analyzing technical indicators...' },
  { icon: MessageSquare, label: 'Sentiment Analyst', description: 'Processing social media data...' },
  { icon: FileText, label: 'News Analyst', description: 'Reviewing latest news...' },
  { icon: Brain, label: 'Fundamentals Analyst', description: 'Evaluating financials...' },
  { icon: Users, label: 'Research Team', description: 'Bull vs Bear debate...' },
];

export default function LoadingState({ ticker, currentStage = 0 }) {
  return (
    <div className="w-full max-w-2xl mx-auto text-center py-12">
      {/* Main Loading Indicator */}
      <div className="mb-8">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-blue-900/50 mb-4">
          <Loader2 className="h-10 w-10 text-blue-400 animate-spin" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Analyzing {ticker}
        </h2>
        <p className="text-gray-400">
          Our AI agents are working on your analysis...
        </p>
      </div>

      {/* Progress Stages */}
      <div className="space-y-3">
        {loadingStages.map((stage, index) => {
          const Icon = stage.icon;
          const isActive = index === currentStage;
          const isComplete = index < currentStage;

          return (
            <div
              key={stage.label}
              className={`flex items-center gap-4 p-4 rounded-lg transition-all
                ${isActive ? 'bg-blue-900/30 border border-blue-700' : 'bg-gray-800/50'}
                ${isComplete ? 'opacity-60' : ''}`}
            >
              <div className={`p-2 rounded-full
                ${isActive ? 'bg-blue-600' : isComplete ? 'bg-green-600' : 'bg-gray-700'}`}>
                {isActive ? (
                  <Loader2 className="h-5 w-5 text-white animate-spin" />
                ) : (
                  <Icon className={`h-5 w-5 ${isComplete ? 'text-white' : 'text-gray-400'}`} />
                )}
              </div>
              <div className="text-left flex-1">
                <p className={`font-medium ${isActive ? 'text-blue-400' : 'text-gray-300'}`}>
                  {stage.label}
                </p>
                <p className="text-sm text-gray-500">{stage.description}</p>
              </div>
              {isComplete && (
                <span className="text-green-400 text-sm">Complete</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Tip */}
      <p className="mt-8 text-sm text-gray-500">
        This may take 1-3 minutes depending on market data availability.
      </p>
    </div>
  );
}

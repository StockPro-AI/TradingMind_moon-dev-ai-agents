import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import AgentCard from './AgentCard';

// Category icons and colors
const categoryConfig = {
  'Market Analysis': {
    icon: '📊',
    color: 'text-blue-400',
    description: 'Technical indicators and price action analysis'
  },
  'Sentiment Analysis': {
    icon: '💬',
    color: 'text-purple-400',
    description: 'Social media and public sentiment'
  },
  'News Analysis': {
    icon: '📰',
    color: 'text-green-400',
    description: 'News events and market impact'
  },
  'Fundamental Analysis': {
    icon: '📈',
    color: 'text-yellow-400',
    description: 'Financial statements and company health'
  },
  'Research Debate': {
    icon: '⚖️',
    color: 'text-orange-400',
    description: 'Bull vs Bear researcher debate'
  },
  'Investment Recommendation': {
    icon: '💡',
    color: 'text-cyan-400',
    description: 'Research manager synthesis'
  },
  'Trading Decision': {
    icon: '🎯',
    color: 'text-pink-400',
    description: 'Trader proposed action'
  },
  'Risk Assessment': {
    icon: '⚠️',
    color: 'text-red-400',
    description: 'Risk team debate and analysis'
  },
  'Final Decision': {
    icon: '✅',
    color: 'text-emerald-400',
    description: 'Portfolio manager final call'
  },
};

export default function CategorySection({ category, agents }) {
  const [isExpanded, setIsExpanded] = useState(true);

  const config = categoryConfig[category] || {
    icon: '📋',
    color: 'text-gray-400',
    description: 'Analysis details'
  };

  if (!agents || agents.length === 0) {
    return null;
  }

  return (
    <div className="mb-6">
      {/* Category Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-3 mb-3 group"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="h-5 w-5 text-gray-500" />
          ) : (
            <ChevronRight className="h-5 w-5 text-gray-500" />
          )}
          <span className="text-xl">{config.icon}</span>
          <h2 className={`text-lg font-semibold ${config.color}`}>{category}</h2>
        </div>
        <div className="flex-1 h-px bg-gray-700 group-hover:bg-gray-600 transition-colors" />
        <span className="text-xs text-gray-500 hidden sm:block">{config.description}</span>
      </button>

      {/* Agent Cards */}
      {isExpanded && (
        <div className="space-y-3 pl-7">
          {agents.map((item, index) => (
            <AgentCard
              key={`${category}-${item.agent}-${index}`}
              agent={item.agent}
              content={item.content}
              isExpanded={agents.length === 1 || category === 'Final Decision'}
            />
          ))}
        </div>
      )}
    </div>
  );
}

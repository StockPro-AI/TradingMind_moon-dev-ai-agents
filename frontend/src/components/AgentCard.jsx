import React, { useState } from 'react';
import { ChevronDown, ChevronUp, User, Bot } from 'lucide-react';

export default function AgentCard({ agent, content, isExpanded: initialExpanded = false }) {
  const [isExpanded, setIsExpanded] = useState(initialExpanded);

  // Determine agent icon and color based on agent name
  const getAgentStyle = (agentName) => {
    const name = agentName.toLowerCase();

    if (name.includes('bull')) {
      return { color: 'text-green-400', bgColor: 'bg-green-900/30', borderColor: 'border-green-700' };
    }
    if (name.includes('bear')) {
      return { color: 'text-red-400', bgColor: 'bg-red-900/30', borderColor: 'border-red-700' };
    }
    if (name.includes('risk') || name.includes('safe') || name.includes('conservative')) {
      return { color: 'text-yellow-400', bgColor: 'bg-yellow-900/30', borderColor: 'border-yellow-700' };
    }
    if (name.includes('trader')) {
      return { color: 'text-purple-400', bgColor: 'bg-purple-900/30', borderColor: 'border-purple-700' };
    }
    if (name.includes('manager') || name.includes('judge')) {
      return { color: 'text-blue-400', bgColor: 'bg-blue-900/30', borderColor: 'border-blue-700' };
    }

    return { color: 'text-gray-400', bgColor: 'bg-gray-800', borderColor: 'border-gray-700' };
  };

  const style = getAgentStyle(agent);

  // Truncate content for preview
  const previewLength = 200;
  const hasMoreContent = content.length > previewLength;
  const previewContent = hasMoreContent ? content.substring(0, previewLength) + '...' : content;

  return (
    <div className={`rounded-lg border ${style.borderColor} ${style.bgColor} overflow-hidden transition-all`}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-full bg-gray-800 ${style.color}`}>
            <Bot className="h-4 w-4" />
          </div>
          <span className={`font-medium ${style.color}`}>{agent}</span>
        </div>
        <div className="flex items-center gap-2">
          {!isExpanded && hasMoreContent && (
            <span className="text-xs text-gray-500">Click to expand</span>
          )}
          {isExpanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </div>
      </button>

      {/* Content */}
      <div className={`px-4 pb-4 ${isExpanded ? '' : 'max-h-32 overflow-hidden'}`}>
        <div className="markdown-content text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
          {isExpanded ? content : previewContent}
        </div>
      </div>
    </div>
  );
}

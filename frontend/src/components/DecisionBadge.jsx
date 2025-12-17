import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export default function DecisionBadge({ decision }) {
  const normalizedDecision = decision?.toUpperCase() || 'HOLD';

  const config = {
    BUY: {
      icon: TrendingUp,
      bgColor: 'bg-green-900/50',
      borderColor: 'border-green-500',
      textColor: 'text-green-400',
      label: 'BUY',
      description: 'Bullish signal - Consider buying'
    },
    SELL: {
      icon: TrendingDown,
      bgColor: 'bg-red-900/50',
      borderColor: 'border-red-500',
      textColor: 'text-red-400',
      label: 'SELL',
      description: 'Bearish signal - Consider selling'
    },
    HOLD: {
      icon: Minus,
      bgColor: 'bg-yellow-900/50',
      borderColor: 'border-yellow-500',
      textColor: 'text-yellow-400',
      label: 'HOLD',
      description: 'Neutral signal - Maintain position'
    }
  };

  const { icon: Icon, bgColor, borderColor, textColor, label, description } =
    config[normalizedDecision] || config.HOLD;

  return (
    <div className={`inline-flex flex-col items-center p-6 rounded-xl border-2 ${bgColor} ${borderColor}`}>
      <Icon className={`h-12 w-12 ${textColor} mb-2`} />
      <span className={`text-3xl font-bold ${textColor}`}>{label}</span>
      <span className="text-sm text-gray-400 mt-1">{description}</span>
    </div>
  );
}

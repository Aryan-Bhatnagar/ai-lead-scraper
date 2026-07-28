import React from 'react';
import { Lightbulb } from 'lucide-react';

export default function RecommendationCard({ recommendation }) {
  const priorityColors = {
    High: 'text-red-600 bg-red-50',
    Medium: 'text-amber-600 bg-amber-50',
    Low: 'text-blue-600 bg-blue-50',
  };

  return (
    <div className="p-3 rounded-lg border border-slate-200 bg-slate-50 flex gap-3">
      <div className="shrink-0 mt-1">
        <Lightbulb className="w-4 h-4 text-primary-500" />
      </div>
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-semibold text-slate-900">{recommendation.service}</span>
          <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${priorityColors[recommendation.priority]}`}>
            {recommendation.priority}
          </span>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed">
          {recommendation.reason}
        </p>
      </div>
    </div>
  );
}

import React from 'react';

const AIPainPointsCard = ({ painPoints }) => {
  if (!painPoints || (Array.isArray(painPoints) && painPoints.length === 0)) return null;

  const pointsList = Array.isArray(painPoints)
    ? painPoints
    : JSON.parse(painPoints || '[]');

  return (
    <div className="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
        Identified Pain Points
      </h3>
      <ul className="space-y-2">
        {pointsList.map((point, idx) => (
          <li key={idx} className="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300">
            <span className="text-amber-500 mt-1">⚠️</span>
            <span>{point}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default AIPainPointsCard;

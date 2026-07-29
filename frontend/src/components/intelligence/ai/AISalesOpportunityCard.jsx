import React from 'react';

const AISalesOpportunityCard = ({ opportunities }) => {
  if (!opportunities || (Array.isArray(opportunities) && opportunities.length === 0)) return null;

  const oppsList = Array.isArray(opportunities)
    ? opportunities
    : JSON.parse(opportunities || '[]');

  return (
    <div className="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
        Sales Opportunities
      </h3>
      <div className="space-y-3">
        {oppsList.map((opp, idx) => (
          <div key={idx} className="p-2 bg-emerald-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800 rounded text-sm text-emerald-800 dark:text-emerald-300">
            {opp}
          </div>
        ))}
      </div>
    </div>
  );
};

export default AISalesOpportunityCard;

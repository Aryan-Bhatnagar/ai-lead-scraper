import React from 'react';

const AICompanySummary = ({ summary }) => {
  if (!summary) return null;
  return (
    <div className="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
        AI Company Summary
      </h3>
      <p className="text-slate-700 dark:text-slate-200 leading-relaxed">
        {summary}
      </p>
    </div>
  );
};

export default AICompanySummary;

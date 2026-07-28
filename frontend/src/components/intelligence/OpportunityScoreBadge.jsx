import React from 'react';

export default function OpportunityScoreBadge({ score }) {
  const getColors = (s) => {
    if (s >= 71) return 'bg-green-100 text-green-700 border-green-200';
    if (s >= 41) return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    return 'bg-red-100 text-red-700 border-red-200';
  };

  // Correcting the logic for the first condition
  const getColorClass = (s) => {
    if (s >= 71) return 'bg-green-100 text-green-700 border-green-200';
    if (s >= 41) return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    return 'bg-red-100 text-red-700 border-red-200';
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-bold border ${getColorClass(score)}`}>
      {score}
    </span>
  );
}

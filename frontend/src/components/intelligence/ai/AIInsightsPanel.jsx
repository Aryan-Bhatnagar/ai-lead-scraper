import React, { useState, useEffect } from 'react';
import AICompanySummary from './AICompanySummary';
import AIServicesCard from './AIServicesCard';
import AIPainPointsCard from './AIPainPointsCard';
import AISalesOpportunityCard from './AISalesOpportunityCard';

const AIInsightsPanel = ({ leadId, initialInsights = null }) => {
  const [insights, setInsights] = useState(initialInsights);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchInsights = async () => {
    try {
      const response = await fetch(`/api/intelligence/${leadId}`);
      const data = await response.json();
      setInsights(data.insights);
      return data.insights;
    } catch (err) {
      setError('Failed to load AI insights');
      return null;
    }
  };

  const generateInsights = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/intelligence/generate/${leadId}`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`Generation failed: ${response.statusText}`);
      }
      const data = await response.json();
      setInsights(data.insights);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!insights) {
      fetchInsights();
    }
  }, [leadId]);

  if (loading) {
    return (
      <div className="p-6 text-center text-slate-500 dark:text-slate-400 animate-pulse">
        Analyzing company website with AI...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg border border-red-200 dark:border-red-800 text-sm">
        {error}
        <button
          onClick={generateInsights}
          className="ml-4 underline font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="p-6 text-center border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-lg">
        <p className="text-slate-500 dark:text-slate-400 mb-4">
          No AI intelligence generated for this prospect.
        </p>
        <button
          onClick={generateInsights}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors text-sm font-medium"
        >
          Generate AI Insights
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">AI Business Intelligence</h2>
        <button
          onClick={generateInsights}
          className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
        >
          Refresh Analysis
        </button>
      </div>

      <AICompanySummary summary={insights.company_summary} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <AIServicesCard services={insights.services_offered} />
        <AIPainPointsCard painPoints={insights.pain_points} />
      </div>

      <AISalesOpportunityCard opportunities={insights.sales_opportunities} />

      <div className="flex justify-end">
        <span className="text-[10px] text-slate-400 uppercase tracking-widest">
          Provider: {insights.llm_provider || 'unknown'}
        </span>
      </div>
    </div>
  );
};

export default AIInsightsPanel;

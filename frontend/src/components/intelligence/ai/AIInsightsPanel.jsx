import React, { useState, useEffect } from 'react';
import AICompanySummary from './AICompanySummary';
import AIServicesCard from './AIServicesCard';
import AIPainPointsCard from './AIPainPointsCard';
import AISalesOpportunityCard from './AISalesOpportunityCard';
import { Database, BrainCircuit, Loader2 } from 'lucide-react';

const AIInsightsPanel = ({ leadId, initialInsights = null }) => {
  const [insights, setInsights] = useState(initialInsights);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [enriching, setEnriching] = useState(false);
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

  const fetchProfile = async () => {
    try {
      const response = await fetch(`/api/enrich/profile/${leadId}`);
      const data = await response.json();
      setProfile(data.profile);
      return data.profile;
    } catch (err) {
      console.error('Failed to fetch profile', err);
      return null;
    }
  };

  const handleEnrichAndGenerate = async () => {
    setLoading(true);
    setEnriching(true);
    setError(null);
    try {
      // Stage 1: Enrich (UEE)
      const enrichResponse = await fetch(`/api/enrich/${leadId}`, { method: 'POST' });

      if (!enrichResponse.ok) {
        const errorData = await enrichResponse.json().catch(() => ({}));
        throw new Error(errorData.description || `Enrichment failed: ${enrichResponse.statusText}`);
      }

      const enrichData = await enrichResponse.json();
      setProfile(enrichData.profile);

      // Stage 2: Generate Intelligence
      setEnriching(false);
      const intelResponse = await fetch(`/api/intelligence/generate/${leadId}`, {
        method: 'POST',
      });

      if (!intelResponse.ok) {
        const errorData = await intelResponse.json().catch(() => ({}));
        throw new Error(errorData.description || `Intelligence generation failed: ${intelResponse.statusText}`);
      }

      const intelData = await intelResponse.json();
      setInsights(intelData.insights);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setEnriching(false);
    }
  };

  useEffect(() => {
    if (!insights) {
      fetchInsights();
    }
    fetchProfile();
  }, [leadId]);

  if (loading) {
    return (
      <div className="p-6 text-center space-y-4">
        <div className="flex justify-center">
          <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        </div>
        <p className="text-slate-500 dark:text-slate-400 animate-pulse text-sm">
          {enriching
            ? "Gathering business data from multiple sources..."
            : "Analyzing business profile with AI..."}
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg border border-red-200 dark:border-red-800 text-sm">
        {error}
        <button
          onClick={handleEnrichAndGenerate}
          className="ml-4 underline font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="p-6 text-center border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-lg space-y-4">
        <div className="flex justify-center gap-4 mb-2">
          <div className={`p-2 rounded-full ${profile ? 'bg-green-100 text-green-600' : 'bg-slate-100 text-slate-400'}`}>
            <Database className="w-5 h-5" />
          </div>
          <div className={`p-2 rounded-full ${profile ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-100 text-slate-400'}`}>
            <BrainCircuit className="w-5 h-5" />
          </div>
        </div>
        <p className="text-slate-500 dark:text-slate-400 mb-4">
          {profile
            ? "Business profile is ready. Now generate AI insights."
            : "No business profile or AI intelligence generated for this prospect."}
        </p>
        <button
          onClick={handleEnrichAndGenerate}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors text-sm font-medium"
        >
          {profile ? "Generate AI Insights" : "Enrich & Generate Insights"}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">AI Business Intelligence</h2>
          {profile && (
            <span className="px-2 py-0.5 bg-green-100 text-green-700 text-[10px] font-bold rounded uppercase">
              Profile Synced
            </span>
          )}
        </div>
        <button
          onClick={handleEnrichAndGenerate}
          className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
        >
          Refresh All
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

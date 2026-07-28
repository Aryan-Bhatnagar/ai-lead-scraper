import React from 'react';
import OpportunityScoreBadge from './OpportunityScoreBadge';
import RecommendationCard from './RecommendationCard';
import ConfidenceBadge from './ConfidenceBadge';
import { Target, AlertCircle, Zap } from 'lucide-react';
import {
  calculateOpportunityScore,
  getRecommendations,
  getIntelligenceInsights,
  calculateConfidence
} from '../../services/opportunityIntelligence';

export default function IntelligencePanel({ prospect }) {
  if (!prospect) return null;

  const score = calculateOpportunityScore(prospect);
  const recommendations = getRecommendations(prospect);
  const { signals, painPoints } = getIntelligenceInsights(prospect);
  const confidence = calculateConfidence(prospect);

  return (
    <div className="bg-slate-50 rounded-xl border border-slate-200 p-6 mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary-500" />
            Opportunity Intelligence
          </h3>
          <p className="text-sm text-slate-500">AI-driven sales potential analysis</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-[10px] uppercase font-bold text-slate-400 mb-1">Opp. Score</div>
            <OpportunityScoreBadge score={score} />
          </div>
          <div className="border-l border-slate-300 pl-3">
            <ConfidenceBadge level={confidence} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recommendations Section */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-2">
            <Target className="w-4 h-4 text-primary-500" />
            Recommended Services
          </div>
          {recommendations.length > 0 ? (
            <div className="space-y-2">
              {recommendations.map((rec, idx) => (
                <RecommendationCard key={idx} recommendation={rec} />
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">No specific recommendations at this time.</p>
          )}
        </div>

        {/* Insights Section */}
        <div className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-2">
              <Zap className="w-4 h-4 text-amber-500" />
              Buying Signals
            </div>
            <div className="flex flex-wrap gap-2">
              {signals.length > 0 ? signals.map((s, i) => (
                <span key={i} className="px-2 py-1 bg-white border border-slate-200 rounded text-[11px] text-slate-600 shadow-sm">
                  {s}
                </span>
              )) : <span className="text-xs text-slate-400 italic">None detected</span>}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-2">
              <AlertCircle className="w-4 h-4 text-red-500" />
              Identified Pain Points
            </div>
            <div className="flex flex-wrap gap-2">
              {painPoints.length > 0 ? painPoints.map((p, i) => (
                <span key={i} className="px-2 py-1 bg-red-50 border border-red-100 rounded text-[11px] text-red-600 shadow-sm">
                  {p}
                </span>
              )) : <span className="text-xs text-slate-400 italic">None detected</span>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

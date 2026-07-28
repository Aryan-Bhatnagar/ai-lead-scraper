/**
 * Opportunity Intelligence Utility
 * Computes sales opportunity metrics based on prospect data on the frontend.
 */

const BILVALEAF_SERVICES = {
  WEB_DEV: 'Website Development',
  DIGITAL_MARKETING: 'Digital Marketing',
  GRAPHIC_DESIGN: 'Graphic Design',
  BPO: 'BPO',
};

const HIGH_VALUE_INDUSTRIES = [
  'Retail', 'Real Estate', 'Healthcare', 'Professional Services',
  'Law', 'Finance', 'E-commerce', 'Beauty', 'Food', 'Technology'
];

/**
 * Calculates the Opportunity Score (0-100)
 * Weights: Data Completeness (30%), Market Alignment (30%), Digital Gap (40%)
 */
export function calculateOpportunityScore(prospect) {
  if (!prospect) return 0;

  // 1. Data Completeness (30%)
  let completeness = 0;
  if (prospect.email) completeness += 25;
  if (prospect.phone) completeness += 25;
  if (prospect.linkedin) completeness += 25;
  if (prospect.quality_score && prospect.quality_score > 70) completeness += 25;

  // 2. Market Alignment (30%)
  let alignment = 0;
  const industry = (prospect.industry || '').toLowerCase();
  if (HIGH_VALUE_INDUSTRIES.some(hi => industry.includes(hi.toLowerCase()))) {
    alignment = 100;
  } else if (industry) {
    alignment = 50; // Some industry present
  }

  // 3. Digital Gap (40%)
  // Higher score if they have GAPS (because that means an opportunity for Bilvaleaf)
  let gap = 0;
  if (!prospect.website) gap += 40;
  else if (!prospect.facebook || !prospect.instagram) gap += 30;
  else if (!prospect.linkedin) gap += 20;

  const score = (completeness * 0.3) + (alignment * 0.3) + (gap * 0.4);
  return Math.round(score);
}

/**
 * Generates recommended Bilvaleaf services based on gaps and industry.
 */
export function getRecommendations(prospect) {
  if (!prospect) return [];

  const recommendations = [];
  const industry = (prospect.industry || '').toLowerCase();
  const desc = (prospect.company_description || '').toLowerCase();

  // Website Development logic
  if (!prospect.website || prospect.data_quality === 'LOW') {
    recommendations.push({
      service: BILVALEAF_SERVICES.WEB_DEV,
      reason: 'Prospect lacks a professional website or has poor web data quality.',
      priority: 'High'
    });
  }

  // Digital Marketing logic
  if (!prospect.facebook || !prospect.instagram) {
    recommendations.push({
      service: BILVALEAF_SERVICES.DIGITAL_MARKETING,
      reason: 'Missing presence on key social growth channels (FB/IG).',
      priority: 'Medium'
    });
  }

  // Graphic Design logic
  const visualIndustries = ['retail', 'beauty', 'food', 'fashion', 'design'];
  if (visualIndustries.some(vi => industry.includes(vi)) || (!prospect.facebook && !prospect.instagram)) {
    recommendations.push({
      service: BILVALEAF_SERVICES.GRAPHIC_DESIGN,
      reason: 'Industry requires strong visual identity and brand assets.',
      priority: 'Medium'
    });
  }

  // BPO logic
  const bpoKeywords = ['enterprise', 'corporate', 'scale', 'global', 'operations', 'management'];
  if (bpoKeywords.some(kw => desc.includes(kw)) || (prospect.company_description?.length > 200)) {
    recommendations.push({
      service: BILVALEAF_SERVICES.BPO,
      reason: 'Company scale and operational complexity suggest a need for BPO services.',
      priority: 'Low'
    });
  }

  return recommendations;
}

/**
 * Identifies specific buying signals and pain points.
 */
export function getIntelligenceInsights(prospect) {
  if (!prospect) return { signals: [], painPoints: [] };

  const signals = [];
  const painPoints = [];

  if (!prospect.website) {
    signals.push('No official website detected');
    painPoints.push('Zero digital discoverability');
  }

  if (prospect.website && (!prospect.facebook && !prospect.instagram)) {
    signals.push('Website exists but no social integration');
    painPoints.push('Fragmented digital presence');
  }

  if (!prospect.email && prospect.phone) {
    signals.push('Phone available but no professional email');
    painPoints.push('Poor lead capture infrastructure');
  }

  const industry = (prospect.industry || '').toLowerCase();
  if (industry.includes('retail') || industry.includes('food')) {
    painPoints.push('High competition requiring visual differentiation');
  }

  return { signals, painPoints };
}

/**
 * Calculates confidence level based on data health.
 */
export function calculateConfidence(prospect) {
  if (!prospect) return 'Low';

  const contactPoints = [prospect.email, prospect.phone, prospect.linkedin].filter(Boolean).length;
  const qScore = prospect.quality_score || 0;

  if (qScore > 80 && contactPoints >= 2) return 'High';
  if (qScore > 50 && contactPoints >= 1) return 'Medium';
  return 'Low';
}

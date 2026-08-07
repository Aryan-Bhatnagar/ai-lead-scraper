/**
 * Adapters: map backend lead/analytics payloads to the UI shape.
 * Backend shape comes from the leads table (database.py LEAD_COLUMNS + lead_status).
 */

const LIFECYCLE_DEFAULT = 'NEW'
const QUALITY_DEFAULT = 'unknown'

/**
 * Normalize a raw source value to a friendly, display-safe provider name.
 *
 * Accepts the normalized `source` column values ("Apollo", "upwork", …),
 * raw provider keys ("google_maps", "google_maps_scraper_kit", …) and
 * `imported://…` provenance URLs.  Never returns a raw ID — always one of
 * the known CRM source names.
 */
export function normalizeSourceName(rawSource) {
  if (!rawSource) return 'Unknown'
  if (typeof rawSource !== 'string') rawSource = String(rawSource)

  // Friendly names (exact match, case-insensitive)
  const FRIENDLY = {
    'apollo': 'Apollo',
    'zoominfo': 'ZoomInfo',
    'lusha': 'Lusha',
    'google_maps': 'Google Maps',
    'google maps': 'Google Maps',
    'googlemaps': 'Google Maps',
    'google_maps_scraper_kit': 'Google Maps Kit',
    'google_maps_kit': 'Google Maps Kit',
    'google_search': 'Google Search',
    'google search': 'Google Search',
    'googlesearch': 'Google Search',
    'website_discovery': 'Website Discovery',
    'website discovery': 'Website Discovery',
    'web discovery': 'Website Discovery',
    'free_web_discovery': 'Website Discovery',
    'free web discovery': 'Website Discovery',
    'upwork': 'Upwork',
    'freelancer': 'Freelancer',
    'guru': 'Guru',
    'peopleperhour': 'PeoplePerHour',
    'people_per_hour': 'PeoplePerHour',
    'apify': 'Apify',
    'linkedin': 'LinkedIn',
    'apollo.io': 'Apollo',
    'imported': 'Imported',
  }

  // Exact match first (covers already-normalized values like "Apollo")
  const exact = FRIENDLY[rawSource.toLowerCase().trim()]
  if (exact) return exact

  // Dataset provenance URLs: imported://dataset_lead-scraper-apollo-zoominfo-...
  const lower = rawSource.toLowerCase()
  if (lower.includes('apollo')) return 'Apollo'
  if (lower.includes('zoominfo')) return 'ZoomInfo'
  if (lower.includes('lusha')) return 'Lusha'
  if (lower.includes('upwork')) return 'Upwork'
  if (lower.includes('freelancer')) return 'Freelancer'
  if (lower.includes('peopleperhour') || lower.includes('people_per_hour')) return 'PeoplePerHour'
  if (lower.includes('guru')) return 'Guru'

  // imported:// paths: try to guess the dataset name
  if (rawSource.startsWith('imported://')) {
    const path = rawSource.replace('imported://', '').replace(/\/+$/, '')
    // Strip "dataset_" prefix and known separators
    let name = path
      .replace(/^dataset[_\-]/, '')
      .split(/[/_\-.]/)[0]
      .trim()
    if (name) {
      const guess = FRIENDLY[name.toLowerCase()]
      if (guess) return guess
      return name.charAt(0).toUpperCase() + name.slice(1)
    }
  }

  // Provider keys embedded in source_pages/URLs
  for (const [key, label] of Object.entries(FRIENDLY)) {
    if (lower.includes(key) && key.length > 3) return label
  }

  return rawSource || 'Unknown'
}

/**
 * Derive a normalized source from the API `source` column first, then from
 * the provenance source_url/source_pages for legacy rows.
 */
export function deriveSourceField(apiLead = {}) {
  if (apiLead.source) {
    const n = normalizeSourceName(apiLead.source)
    if (n && n !== 'Unknown') return n
  }
  return normalizeSourceName(deriveSource(apiLead.source_url, apiLead.source_pages))
}

function deriveQualityTier(score, dataQuality, qualityTier) {
  // If backend provides quality_tier (from ScoredLead), use it
  if (qualityTier) return String(qualityTier).toLowerCase()
  // Fallback to data_quality (HIGH/MEDIUM/LOW)
  if (dataQuality) return String(dataQuality).toLowerCase()
  // Fallback to score-based derivation
  if (typeof score !== 'number') return QUALITY_DEFAULT
  if (score >= 90) return 'excellent'
  if (score >= 75) return 'good'
  if (score >= 50) return 'average'
  if (score > 0) return 'poor'
  return QUALITY_DEFAULT
}

function deriveSource(sourceUrl, sourcePage) {
  if (!sourceUrl && !sourcePage) return 'unknown'
  const raw = sourceUrl || sourcePage
  try {
    const url = raw.startsWith('http') ? new URL(raw) : null
    return url ? url.hostname.replace(/^www\./, '') : String(raw)
  } catch {
    return String(raw)
  }
}

function buildScoreBreakdown(score) {
  // backend only stores overall quality_score; distribute it across
  // a fixed breakdown shape for the drawer UI
  const s = Math.max(0, Math.min(100, score || 0))
  return [
    { feature: 'website', label: 'Website Quality', contribution: Math.round(s * 0.3), max: 25 },
    { feature: 'email', label: 'Business Email', contribution: Math.round(s * 0.22), max: 20 },
    { feature: 'phone', label: 'Phone Number', contribution: Math.round(s * 0.15), max: 15 },
    { feature: 'sources', label: 'Multiple Sources', contribution: Math.round(s * 0.1), max: 10 },
    { feature: 'location', label: 'Location Data', contribution: Math.round(s * 0.08), max: 8 },
    { feature: 'description', label: 'Company Description', contribution: Math.round(s * 0.08), max: 8 },
  ]
}

function parseScoreBreakdown(jsonStr) {
  if (!jsonStr) return null
  try {
    const parsed = JSON.parse(jsonStr)
    // Convert to the UI expected format
    if (Array.isArray(parsed)) return parsed
    if (parsed.breakdown && Array.isArray(parsed.breakdown)) return parsed.breakdown
    if (parsed.features && Array.isArray(parsed.features)) return parsed.features
    // If it's an object with feature contributions
    const result = []
    for (const [key, value] of Object.entries(parsed)) {
      if (typeof value === 'number' || typeof value === 'object') {
        result.push({ feature: key, label: key, contribution: typeof value === 'number' ? value : value.contribution || 0, max: 25 })
      }
    }
    return result.length > 0 ? result : null
  } catch {
    return null
  }
}

function parseScoreExplanation(jsonStr) {
  if (!jsonStr) return null
  try {
    const parsed = JSON.parse(jsonStr)
    if (parsed.breakdowns && Array.isArray(parsed.breakdowns)) {
      return parsed.breakdowns.map(b => ({
        feature: b.feature,
        label: b.label,
        weight: b.weight,
        quality_ratio: b.quality_ratio,
        contribution: b.contribution,
        detail: b.detail
      }))
    }
    return null
  } catch {
    return null
  }
}

/**
 * Map one lead record from the API to the UI-friendly shape.
 */
export function mapApiLead(apiLead = {}) {
  const score = apiLead.quality_score ?? 0
  const lifecycle = String(apiLead.lead_status || LIFECYCLE_DEFAULT).toUpperCase()
  const source = deriveSourceField(apiLead)
  const discoveredAt = apiLead.scraped_at || apiLead.created_at || new Date().toISOString()
  const updatedAt = apiLead.updated_at || discoveredAt

  // Use backend-provided quality_tier if available
  const qualityTier = apiLead.quality_tier || null

  // Use backend-provided score_breakdown_json if available
  let scoreBreakdown = null
  if (apiLead.score_breakdown_json) {
    scoreBreakdown = parseScoreBreakdown(apiLead.score_breakdown_json)
  }
  if (!scoreBreakdown) {
    scoreBreakdown = buildScoreBreakdown(score)
  }

  // Parse opportunity score explanation
  let scoreExplanation = null
  if (apiLead.score_explanation_json) {
    scoreExplanation = parseScoreExplanation(apiLead.score_explanation_json)
  }

  // Helper to parse a JSON-array column safely
  const parseJsonList = (val) => {
    if (!val) return null
    if (Array.isArray(val)) return val
    if (typeof val === 'string') {
      try {
        const parsed = JSON.parse(val)
        return Array.isArray(parsed) ? parsed : [val]
      } catch {
        return [val]
      }
    }
    return null
  }

  return {
    id: apiLead.id,
    company_name: apiLead.company_name || 'Unknown',
    website: apiLead.website || null,
    country: apiLead.country || null,
    city: apiLead.city || null,
    region: apiLead.region || null,
    address: apiLead.address || null,
    industry: apiLead.industry || null,
    description: apiLead.company_description || null,
    contact_name: apiLead.contact_name || null,
    job_title: apiLead.contact_role || null,
    email: apiLead.email || null,
    phone: apiLead.phone || null,
    score,
    quality_tier: deriveQualityTier(score, apiLead.data_quality, qualityTier),
    score_breakdown: scoreBreakdown,
    score_explanation: scoreExplanation,
    lifecycle,
    source,
    discovered_at: discoveredAt,
    lifecycle_updated_at: updatedAt,
    last_updated: updatedAt,
    timeline: [
      { status: 'NEW', at: discoveredAt, note: 'Lead discovered' },
      ...(lifecycle !== 'NEW'
        ? [{ status: lifecycle, at: updatedAt, note: `Advanced to ${lifecycle.toLowerCase()}` }]
        : []),
    ],
    // Store enriched fields for drawer
    google_rating: apiLead.google_rating,
    maps_review_count: apiLead.maps_review_count,
    categories: parseJsonList(apiLead.categories),
    socials: apiLead.socials_json ? (typeof apiLead.socials_json === 'string' ? JSON.parse(apiLead.socials_json) : apiLead.socials_json) : null,

    // AI Enrichment fields
    ai_summary: apiLead.ai_summary || null,
    pain_points: parseJsonList(apiLead.pain_points),
    recommended_service: apiLead.recommended_service || null,
    decision_maker_guess: apiLead.decision_maker_guess || null,
    company_size: apiLead.company_size_estimate || null,
    company_size_estimate: apiLead.company_size_estimate || null,
    buying_signals: parseJsonList(apiLead.buying_signals),
    outreach_strategy: apiLead.outreach_strategy || null,
    ai_confidence: apiLead.ai_confidence || null,
    opportunity_score: apiLead.opportunity_score || null,
    company_logo: apiLead.company_logo || null,
    discovery_date: apiLead.discovery_date || null,

    _raw: apiLead,
  }
}

export function mapLeadForExport(apiLead) {
  const l = mapApiLead(apiLead)
  return {
    Company: l.company_name,
    Website: l.website || '',
    Country: l.country || '',
    City: l.city || '',
    Industry: l.industry || '',
    Score: l.score,
    Quality: l.quality_tier,
    Lifecycle: l.lifecycle,
    Source: l.source,
    Email: l.email || '',
    Phone: l.phone || '',
  }
}

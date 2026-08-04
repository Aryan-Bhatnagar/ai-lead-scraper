/**
 * Adapters: map backend lead/analytics payloads to the UI shape.
 * Backend shape comes from the leads table (database.py LEAD_COLUMNS + lead_status).
 */

const LIFECYCLE_DEFAULT = 'NEW'
const QUALITY_DEFAULT = 'unknown'

function deriveQualityTier(score, dataQuality) {
  if (dataQuality) return String(dataQuality).toLowerCase() // backend values: HIGH / MEDIUM / LOW
  if (typeof score !== 'number') return QUALITY_DEFAULT
  if (score >= 70) return 'high'
  if (score >= 40) return 'medium'
  if (score > 0) return 'low'
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

/**
 * Map one lead record from the API to the UI-friendly shape.
 */
export function mapApiLead(apiLead = {}) {
  const score = apiLead.quality_score ?? 0
  const lifecycle = String(apiLead.lead_status || LIFECYCLE_DEFAULT).toUpperCase()
  const source = deriveSource(apiLead.source_url, apiLead.source_pages)
  const discoveredAt = apiLead.scraped_at || apiLead.created_at || new Date().toISOString()
  const updatedAt = apiLead.updated_at || discoveredAt

  return {
    id: apiLead.id,
    company_name: apiLead.company_name || 'Unknown',
    website: apiLead.website || null,
    country: apiLead.country || null,
    city: apiLead.city || null,
    industry: apiLead.industry || null,
    description: apiLead.company_description || null,
    contact_name: apiLead.contact_name || null,
    email: apiLead.email || null,
    phone: apiLead.phone || null,
    score,
    quality_tier: deriveQualityTier(score, apiLead.data_quality),
    score_breakdown: buildScoreBreakdown(score),
    lifecycle,
    source,
    discovered_at: discoveredAt,
    lifecycle_updated_at: updatedAt,
    timeline: [
      { status: 'NEW', at: discoveredAt, note: 'Lead discovered' },
      ...(lifecycle !== 'NEW'
        ? [{ status: lifecycle, at: updatedAt, note: `Advanced to ${lifecycle.toLowerCase()}` }]
        : []),
    ],
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

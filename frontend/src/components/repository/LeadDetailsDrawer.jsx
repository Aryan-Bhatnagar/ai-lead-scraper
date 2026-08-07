import { useEffect } from 'react'
import {
  X,
  Globe,
  MapPin,
  Mail,
  Phone,
  User,
  Clock,
  Tag,
  Star,
  MessageSquare,
  Building2,
  Share2,
  Linkedin,
  Twitter,
  Facebook,
  Instagram,
  Brain,
  Target,
  AlertTriangle,
  Lightbulb,
  Users,
  DollarSign,
  TrendingUp,
  Briefcase,
  Send,
} from 'lucide-react'
import ScoreBadge from '../reusable/badges/ScoreBadge'
import OpportunityScoreBadge from '../reusable/badges/OpportunityScoreBadge'
import LifecycleBadge from '../reusable/badges/LifecycleBadge'
import SourceBadge from '../reusable/badges/SourceBadge'

function DrawerRow({ icon: Icon, label, children }) {
  return (
    <div className="flex items-start gap-3 py-2.5">
      <Icon className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
        <div className="text-sm text-slate-800 dark:text-slate-200">{children}</div>
      </div>
    </div>
  )
}

function SocialIcon({ platform, url }) {
  const icons = {
    linkedin: Linkedin,
    twitter: Twitter,
    x: Twitter,
    facebook: Facebook,
    instagram: Instagram,
  }
  const Icon = icons[platform.toLowerCase()] || Share2
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="p-1.5 text-slate-500 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
      title={platform}
      aria-label={platform}
    >
      <Icon className="w-4 h-4" />
    </a>
  )
}

function ListItems({ items, accent = 'text-amber-500', fallback = '—' }) {
  const list = Array.isArray(items) && items.length > 0 ? items : null
  if (!list) return <span className="text-slate-400">{fallback}</span>
  return (
    <ul className="space-y-1">
      {list.map((item, i) => (
        <li key={i} className="text-sm text-slate-700 dark:text-slate-300 flex items-start gap-2">
          <span className={`mt-1.5 w-1 h-1 rounded-full shrink-0 ${accent}`} />
          <span className="min-w-0">{item}</span>
        </li>
      ))}
    </ul>
  )
}

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function qualityTierClass(tier) {
  const t = String(tier || '').toLowerCase()
  if (t === 'excellent') return 'text-emerald-600 dark:text-emerald-400'
  if (t === 'good') return 'text-success-600 dark:text-success-500'
  if (t === 'average') return 'text-warning-600 dark:text-warning-500'
  if (t === 'poor') return 'text-danger-600 dark:text-danger-500'
  return 'text-slate-500 dark:text-slate-400'
}

export default function LeadDetailsDrawer({ lead, onClose }) {
  useEffect(() => {
    if (!lead) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [lead, onClose])

  const open = !!lead

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40 transition-opacity duration-300 ${
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Panel */}
      <aside
        className={`fixed top-0 right-0 h-full w-full max-w-md z-50 bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700/60 shadow-2xl transition-transform duration-300 ease-out ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
        aria-hidden={!open}
      >
        {lead && (
          <div className="h-full flex flex-col">
            {/* Header */}
            <div className="flex items-start justify-between p-5 border-b border-slate-200 dark:border-slate-700/60">
              <div className="min-w-0 flex-1 pr-4">
                <div className="flex items-center gap-3">
                  {lead.company_logo && lead.company_logo.startsWith('http') ? (
                    <img
                      src={lead.company_logo}
                      alt={lead.company_name}
                      className="w-11 h-11 rounded-xl bg-white object-contain p-1 ring-1 ring-slate-200 dark:ring-slate-700 shrink-0"
                      onError={(e) => { e.currentTarget.style.display = 'none' }}
                    />
                  ) : (
                    <div className="w-11 h-11 rounded-xl bg-primary-50 dark:bg-primary-500/10 flex items-center justify-center text-primary-600 dark:text-primary-400 shrink-0">
                      <Building2 className="w-5 h-5" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white truncate">
                      {lead.company_name}
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                      {lead.website?.replace(/^https?:\/\//, '') || lead.industry || 'CRM lead'}
                    </p>
                  </div>
                </div>
                <div className="mt-2.5 flex flex-wrap items-center gap-2">
                  <OpportunityScoreBadge score={lead.opportunity_score} />
                  <ScoreBadge score={lead.score} size="sm" />
                  <LifecycleBadge state={lead.lifecycle} />
                  <SourceBadge source={lead.source} size="sm" />
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                aria-label="Close drawer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Scrollable body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {/* Company overview */}
              <section>
                <div className="divide-y divide-slate-100 dark:divide-slate-800">
                  <DrawerRow icon={Globe} label="Website">
                    {lead.website ? (
                      <a
                        href={lead.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-600 dark:text-primary-400 hover:underline break-all"
                      >
                        {lead.website}
                      </a>
                    ) : (
                      '—'
                    )}
                  </DrawerRow>
                  <DrawerRow icon={MapPin} label="Location">
                    {[lead.address, lead.city, lead.region, lead.country].filter(Boolean).join(', ') || '—'}
                    {lead.industry && <span className="text-slate-400"> · {lead.industry}</span>}
                  </DrawerRow>
                  {lead.company_size && (
                    <DrawerRow icon={Users} label="Company Size">
                      {lead.company_size}
                    </DrawerRow>
                  )}
                  <DrawerRow icon={User} label="Contact">
                    {lead.contact_name || '—'}
                  </DrawerRow>
                  {lead.job_title && (
                    <DrawerRow icon={Briefcase} label="Job Title">
                      {lead.job_title}
                    </DrawerRow>
                  )}
                  <DrawerRow icon={Mail} label="Email">
                    {lead.email ? (
                      <a href={`mailto:${lead.email}`} className="text-primary-600 dark:text-primary-400 hover:underline break-all">
                        {lead.email}
                      </a>
                    ) : (
                      '—'
                    )}
                  </DrawerRow>
                  <DrawerRow icon={Phone} label="Phone">
                    {lead.phone || '—'}
                  </DrawerRow>
                  {/* Google Maps Rating & Reviews */}
                  {(lead.google_rating || lead.maps_review_count) && (
                    <DrawerRow icon={Star} label="Google Maps Rating">
                      <div className="flex items-center gap-2">
                        {lead.google_rating !== undefined && lead.google_rating !== null && (
                          <span className="flex items-center gap-1 text-yellow-600 dark:text-yellow-400 font-medium">
                            <Star className="w-4 h-4 fill-current" />
                            {lead.google_rating}
                          </span>
                        )}
                        {lead.maps_review_count && (
                          <span className="text-slate-500 dark:text-slate-400">
                            ({lead.maps_review_count} reviews)
                          </span>
                        )}
                      </div>
                    </DrawerRow>
                  )}
                  {/* Categories */}
                  {lead.categories && lead.categories.length > 0 && (
                    <DrawerRow icon={Tag} label="Categories">
                      <div className="flex flex-wrap gap-1.5">
                        {lead.categories.map((cat, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 text-xs rounded-full bg-primary-50 dark:bg-primary-500/20 text-primary-700 dark:text-primary-300"
                          >
                            {cat}
                          </span>
                        ))}
                      </div>
                    </DrawerRow>
                  )}
                  {/* Social Profiles */}
                  {lead.socials && Object.keys(lead.socials).length > 0 && (
                    <DrawerRow icon={Share2} label="Social Profiles">
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(lead.socials).map(([platform, url]) => (
                          url && (
                            <SocialIcon key={platform} platform={platform} url={url} />
                          )
                        ))}
                      </div>
                    </DrawerRow>
                  )}
                </div>
                {lead.description && (
                  <div className="mt-4 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60">
                    <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5">
                      Description
                    </p>
                    <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                      {lead.description}
                    </p>
                  </div>
                )}
              </section>

              {/* AI Summary */}
              {lead.ai_summary && (
                <section>
                  <div className="p-3.5 rounded-xl bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-800/60">
                    <p className="text-xs font-medium text-violet-700 dark:text-violet-300 mb-1.5 flex items-center gap-1.5">
                      <Brain className="w-3.5 h-3.5" />
                      AI Summary
                      {lead.ai_confidence !== null && lead.ai_confidence !== undefined && (
                        <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-violet-100 dark:bg-violet-800 text-violet-700 dark:text-violet-300">
                          {Math.round(lead.ai_confidence * 100)}% confidence
                        </span>
                      )}
                    </p>
                    <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                      {lead.ai_summary}
                    </p>
                  </div>
                </section>
              )}

              {/* AI Enrichment grid */}
              {(lead.recommended_service || lead.decision_maker_guess) && (
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                    <Brain className="w-3.5 h-3.5 text-violet-600" />
                    AI Intelligence
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    {lead.recommended_service && (
                      <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800/60 col-span-2">
                        <p className="text-xs font-medium text-emerald-700 dark:text-emerald-300 mb-1 flex items-center gap-1.5">
                          <Target className="w-3.5 h-3.5" />
                          Recommended BilvaLeaf Service
                        </p>
                        <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                          {lead.recommended_service}
                        </p>
                      </div>
                    )}
                    {lead.decision_maker_guess && (
                      <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60">
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 flex items-center gap-1">
                          <Users className="w-3.5 h-3.5" />
                          Decision Maker
                        </p>
                        <p className="text-sm text-slate-700 dark:text-slate-300">
                          {lead.decision_maker_guess}
                        </p>
                      </div>
                    )}
                    {lead.company_size && (
                      <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60">
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 flex items-center gap-1">
                          <Building2 className="w-3.5 h-3.5" />
                          Company Size
                        </p>
                        <p className="text-sm text-slate-700 dark:text-slate-300">
                          {lead.company_size}
                        </p>
                      </div>
                    )}
                  </div>
                </section>
              )}

              {/* Pain Points */}
              {lead.pain_points && lead.pain_points.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                    Pain Points
                  </h3>
                  <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/60">
                    <ListItems items={lead.pain_points} accent="bg-amber-500" />
                  </div>
                </section>
              )}

              {/* Buying Signals */}
              {(lead.buying_signals && lead.buying_signals.length > 0) && (
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                    <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
                    Buying Signals
                  </h3>
                  <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800/60">
                    <ListItems items={lead.buying_signals} accent="bg-emerald-500" />
                  </div>
                </section>
              )}

              {/* Outreach Strategy */}
              {lead.outreach_strategy && (
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                    <Send className="w-3.5 h-3.5 text-primary-500" />
                    Outreach Strategy
                  </h3>
                  <div className="p-3.5 rounded-xl bg-primary-50 dark:bg-primary-500/10 border border-primary-200 dark:border-primary-500/20">
                    <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                      {lead.outreach_strategy}
                    </p>
                  </div>
                </section>
              )}

              {/* Opportunity Score Breakdown */}
              {lead.score_explanation && lead.score_explanation.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                    <DollarSign className="w-3.5 h-3.5 text-emerald-600" />
                    Opportunity Score Breakdown
                  </h3>
                  <div className="space-y-2.5">
                    {lead.score_explanation.map((b) => {
                      const pct = Math.round((b.quality_ratio || 0) * 100)
                      return (
                        <div key={b.feature}>
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="font-medium text-slate-600 dark:text-slate-300">
                              {b.label || b.feature}
                            </span>
                            <span className="text-slate-400 tabular-nums">
                              {(b.contribution || 0).toFixed(1)} / {b.weight}
                            </span>
                          </div>
                          <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-500"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          {b.detail && (
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                              {b.detail}
                            </p>
                          )}
                        </div>
                      )
                    })}
                    <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
                      <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                        Opportunity Score
                      </span>
                      <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                        {lead.opportunity_score || 0}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                        Quality Tier
                      </span>
                      <span className={`text-xs font-semibold capitalize ${qualityTierClass(lead.quality_tier)}`}>
                        {lead.quality_tier || '—'}
                      </span>
                    </div>
                  </div>
                </section>
              )}

              {/* Score Breakdown */}
              {lead.score_breakdown && lead.score_breakdown.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3">
                    Score Breakdown
                  </h3>
                  <div className="space-y-2.5">
                    {lead.score_breakdown.map((b) => {
                      const pct = Math.round(((b.contribution || 0) / (b.max || 25)) * 100)
                      return (
                        <div key={b.feature}>
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="font-medium text-slate-600 dark:text-slate-300">
                              {b.label}
                            </span>
                            <span className="text-slate-400 tabular-nums">
                              +{b.contribution} / {b.max}
                            </span>
                          </div>
                          <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-primary-500 to-primary-400 transition-all duration-500"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      )
                    })}
                    <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
                      <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                        Overall Score
                      </span>
                      <span className="text-xs font-semibold text-primary-600 dark:text-primary-400">
                        {lead.score || 0}
                      </span>
                    </div>
                  </div>
                </section>
              )}

              {/* Timeline */}
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" />
                  Lifecycle Timeline
                </h3>
                <ol className="relative space-y-4 pl-6">
                  <span className="absolute left-[9px] top-1 bottom-1 w-px bg-slate-200 dark:bg-slate-700" />
                  {[...(lead.timeline || [])].reverse().map((event, i) => (
                    <li key={`${event.status}-${event.at}`} className="relative">
                      <span
                        className={`absolute -left-6 top-1 w-[13px] h-[13px] rounded-full ring-4 ring-white dark:ring-slate-900 ${
                          i === 0 ? 'bg-primary-500 animate-pulse-ring' : 'bg-slate-300 dark:bg-slate-600'
                        }`}
                      />
                      <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                        {event.status}
                      </p>
                      <p className="text-xs text-slate-400">
                        {formatDate(event.at)}{' '}
                        {event.note && <span>· {event.note}</span>}
                      </p>
                    </li>
                  ))}
                </ol>
              </section>

              {/* Provenance */}
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                  <Tag className="w-3.5 h-3.5" />
                  Discovery
                </h3>
                <div className="rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 p-3.5 text-sm space-y-1.5">
                  <p className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">Source</span>
                    <SourceBadge source={lead.source} size="sm" />
                  </p>
                  <p className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">Discovered</span>
                    <span className="font-medium text-slate-800 dark:text-slate-200">
                      {formatDate(lead.discovered_at)}
                    </span>
                  </p>
                  <p className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">Last Updated</span>
                    <span className="font-medium text-slate-800 dark:text-slate-200">
                      {formatDate(lead.lifecycle_updated_at)}
                    </span>
                  </p>
                </div>
              </section>

              {/* Messaging placeholder when nothing enriched yet */}
              {!lead.ai_summary && !lead.opportunity_score && (
                <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-center">
                  <MessageSquare className="w-5 h-5 text-slate-400 mx-auto mb-1.5" />
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    No AI enrichment yet. Run enrichment to generate intelligence for this lead.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </aside>
    </>
  )
}

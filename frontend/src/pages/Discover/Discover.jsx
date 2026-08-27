import { useState, useEffect } from 'react'
import { Search, MapPin, Globe, Cloud, Camera, Zap, ExternalLink, FileText, Sparkles, CheckCircle2, Clock, Hourglass, Send, Code2 } from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'
import LoadingSpinner from '../../components/layout/LoadingSpinner'
import ProviderMultiSelect from '../../components/campaigns/ProviderMultiSelect'
import SourceBadge from '../../components/reusable/badges/SourceBadge'
import api from '../../services/api'
import toast from 'react-hot-toast'

export default function Discover() {
  const [industry, setIndustry] = useState('')
  const [location, setLocation] = useState('')
  const [maxResults, setMaxResults] = useState(10)
  const [providers, setProviders] = useState(['freelancer'])
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState([])
  const [error, setError] = useState('')
  const [teamMembers, setTeamMembers] = useState([])

  useEffect(() => {
    api.get('/api/team').then(res => {
      setTeamMembers(res.data.team || [])
    }).catch(() => {})
  }, [])

  const handleAssignWork = async (lead, cardIndex, member) => {
    try {
      const primaryDomain = Array.isArray(member.domains) ? member.domains[0] : (member.domains || 'Development')
      await api.post('/api/leads/assign-direct', {
        member_id: member.id,
        member_name: member.name,
        member_domain: primaryDomain,
        lead: lead
      })
      toast.success(`Assigned work to ${member.name}! Lead status set to QUALIFIED.`)
      setResults(prev => {
        const next = [...prev]
        next[cardIndex] = {
          ...next[cardIndex],
          assigned_member_id: member.id,
          assigned_member_name: member.name,
          assigned_member_domain: primaryDomain
        }
        return next
      })
    } catch (err) {
      toast.error('Failed to assign work')
    }
  }

  const handleDiscover = async () => {
    if (!industry.trim()) { toast.error('Industry is required'); return }
    if (!location.trim()) { toast.error('Location is required'); return }
    if (providers.length === 0) { toast.error('Select at least one provider'); return }
    const max = Number(maxResults)
    if (isNaN(max) || max < 1 || max > 100) { toast.error('Maximum results must be between 1 and 100'); return }

    setLoading(true)
    setError('')
    setResults([])

    const payload = {
      industry,
      location,
      max_results: max,
      providers: providers
    }

    try {
      const { data } = await api.post('/api/discover', payload)
      let discovered = []
      if (Array.isArray(data.results)) { discovered = data.results }
      else if (Array.isArray(data.urls)) { discovered = data.urls.map(url => ({ url })) }
      setResults(discovered)
      toast.success(`Discovered ${discovered.length} potential leads`)
    } catch (err) {
      const msg = err?.response?.data?.error || err.message || 'Discovery failed'
      setError(msg)
      toast.error(msg)
    } finally { setLoading(false) }
  }

  return (
    <div className="p-4 lg:p-8 space-y-8">
      <PageHeader title="Prospect Intelligence" subtitle="Find new business prospects using high-fidelity discovery providers." />

      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm max-w-4xl mx-auto">
        <form onSubmit={e => { e.preventDefault(); handleDiscover(); }} className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6">
            <div className="space-y-1">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300" htmlFor="industry">Industry</label>
              <input type="text" id="industry" className="w-full border rounded-lg p-2 dark:bg-slate-800 dark:border-slate-700 dark:text-white" placeholder="e.g. Coffee Shops" value={industry} onChange={e => setIndustry(e.target.value)} required />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300" htmlFor="location">Location</label>
              <input type="text" id="location" className="w-full border rounded-lg p-2 dark:bg-slate-800 dark:border-slate-700 dark:text-white" placeholder="e.g. Chandigarh, India" value={location} onChange={e => setLocation(e.target.value)} required />
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">Discovery Providers</label>
              <ProviderMultiSelect value={providers} onChange={setProviders} />
            </div>

            <div className="flex items-center gap-4">
              <div className="w-full sm:w-48 space-y-1">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300" htmlFor="max-results">Max Results</label>
                <input type="number" id="max-results" className="w-full border rounded-lg p-2 dark:bg-slate-800 dark:border-slate-700 dark:text-white" value={maxResults} onChange={e => setMaxResults(e.target.value)} min={1} max={100} required />
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-4">
            <button type="submit" className="inline-flex items-center gap-2 px-6 py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-95" disabled={loading}>
              {loading ? (
                <>
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 100 100">
                    <circle className="opacity-25" cx="50" cy="50" r="20" stroke="currentColor" strokeWidth="4" fill="none"/>
                    <path className="opacity-75" d="M58 12a46 46 0 0 1 22 36" stroke="currentColor" strokeWidth="4" fill="none"/>
                  </svg>
                  <span>Scanning...</span>
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  <span>Launch Discovery</span>
                </>
              )}
            </button>
          </div>
        </form>

        {loading && (
          <div className="flex items-center justify-center gap-2 mt-8 py-12">
            <LoadingSpinner className="h-8 w-8 text-primary-600" />
            <span className="text-slate-600 dark:text-slate-400 font-medium">Identifying high-quality prospects...</span>
          </div>
        )}

        {error && (
          <div className="mt-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 rounded-lg text-sm">
            {error}
          </div>
        )}

        {!loading && !error && results.length === 0 && (
          <div className="mt-8 py-12">
            <EmptyState icon={Search} title="No prospects identified yet." description="Enter industry and location to start the discovery engine." />
          </div>
        )}

        {results.length > 0 && (
          <div className="mt-8 space-y-4">
            <div className="flex items-center justify-between px-1">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-500 fill-amber-500" />
                Discovered Prospects & Scraped Requirements ({results.length})
              </h3>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {results.map((r, idx) => {
                const isFreelance = (r.source || '').toLowerCase().includes('freelancer') || (r.url || '').toLowerCase().includes('freelancer.com')
                return (
                  <div key={idx} className="bg-white dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 shadow-sm space-y-4 hover:border-slate-300 dark:hover:border-slate-600 transition-all">
                    {/* Header */}
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-1.5 flex-1 min-w-[280px]">
                        <div className="flex items-center gap-2 flex-wrap">
                          <SourceBadge source={r.source || 'freelancer'} />
                          {Boolean(r.has_requirement_evidence || r.has_intent || isFreelance) && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                              <CheckCircle2 className="w-3 h-3" />
                              Active Client Project
                            </span>
                          )}
                          {r.score && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-primary-50 text-primary-700 dark:bg-primary-500/10 dark:text-primary-400">
                              AI Score: {r.score}
                            </span>
                          )}
                        </div>
                        <h4 className="text-base font-semibold text-slate-900 dark:text-white">
                          {r.title || 'Client Project Prospect'}
                        </h4>
                      </div>

                      <a
                        href={r.url || '#'}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-primary-600 hover:bg-primary-700 text-white text-xs font-medium rounded-lg shadow-sm transition-all"
                      >
                        <span>{isFreelance ? 'Apply on Freelancer' : 'View Prospect'}</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>

                    {/* Real-time Project Specs: Proposals, Posted Time, Time Remaining */}
                    {(r.proposals_str || r.posted_time_str || r.time_left_str || isFreelance) && (
                      <div className="flex items-center gap-2.5 flex-wrap text-xs font-medium">
                        {r.proposals_str && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                            <Send className="w-3 h-3 text-purple-500" />
                            {r.proposals_str}
                          </span>
                        )}
                        {r.posted_time_str && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-sky-50 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300 border border-sky-200 dark:border-sky-800">
                            <Clock className="w-3 h-3 text-sky-500" />
                            {r.posted_time_str}
                          </span>
                        )}
                        {r.time_left_str && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                            <Hourglass className="w-3 h-3 text-amber-500" />
                            {r.time_left_str}
                          </span>
                        )}
                      </div>
                    )}

                    {/* Must-Have Required Skills & Tech Stack */}
                    {((r.skills && r.skills.length > 0) || r.skills_str) && (
                      <div className="flex items-center gap-2 flex-wrap text-xs">
                        <span className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1">
                          <Code2 className="w-3.5 h-3.5 text-primary-500" />
                          Must-Have Skills:
                        </span>
                        {(Array.isArray(r.skills) && r.skills.length > 0 ? r.skills : (r.skills_str || '').split(',')).map((sk, sidx) => {
                          const cleanSk = typeof sk === 'string' ? sk.trim() : String(sk)
                          if (!cleanSk) return null
                          return (
                            <span key={sidx} className="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                              {cleanSk}
                            </span>
                          )
                        })}
                      </div>
                    )}

                    {/* Scraped Details: What They Want & How They Pay */}
                    <div className="bg-slate-50 dark:bg-slate-900/60 rounded-lg p-3.5 border border-slate-100 dark:border-slate-800 space-y-2">
                      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider flex-wrap gap-2">
                        <span className="flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
                          <FileText className="w-3.5 h-3.5 text-primary-500" />
                          Scraped Client Requirements (What They Want)
                        </span>
                        {r.buying_signals && (
                          <span className="normal-case text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-800">
                            💳 {r.buying_signals}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-normal">
                        {r.description || r.ai_summary || 'Active project details extracted from Freelancer REST API.'}
                      </p>
                    </div>

                      {/* AI Overview & Recommended Pitch Angle */}
                      {(r.ai_summary || r.outreach_strategy) && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                          {r.ai_summary && (
                            <div className="bg-amber-50/50 dark:bg-amber-950/20 rounded-lg p-2.5 border border-amber-100 dark:border-amber-900/30">
                              <span className="font-semibold text-amber-800 dark:text-amber-300 block mb-0.5 flex items-center gap-1">
                                <Sparkles className="w-3 h-3 text-amber-500" /> AI Team Overview
                              </span>
                              <span className="text-slate-600 dark:text-slate-400">{r.ai_summary}</span>
                            </div>
                          )}
                          {r.outreach_strategy && (
                            <div className="bg-blue-50/50 dark:bg-blue-950/20 rounded-lg p-2.5 border border-blue-100 dark:border-blue-900/30">
                              <span className="font-semibold text-blue-800 dark:text-blue-300 block mb-0.5 flex items-center gap-1">
                                <Zap className="w-3 h-3 text-blue-500" /> Recommended Pitch Angle
                              </span>
                              <span className="text-slate-600 dark:text-slate-400">{r.outreach_strategy}</span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Work Assignment Control */}
                      <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between flex-wrap gap-3 text-xs">
                        <div className="flex items-center gap-2">
                          {r.assigned_member_name ? (
                            <span className="flex items-center gap-1.5 bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 px-3 py-1 rounded-lg font-semibold">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> Assigned: {r.assigned_member_name} ({r.assigned_member_domain || 'Team'})
                            </span>
                          ) : (
                            <span className="text-slate-500 dark:text-slate-400 font-medium">Work Assignment:</span>
                          )}
                        </div>

                        <div className="flex items-center gap-2">
                          <select
                            onChange={(e) => {
                              const selectedId = Number(e.target.value)
                              if (!selectedId) return
                              const member = teamMembers.find(m => m.id === selectedId)
                              if (member) handleAssignWork(r, idx, member)
                              e.target.value = ""
                            }}
                            defaultValue=""
                            className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-primary-500 font-medium cursor-pointer shadow-sm"
                          >
                            <option value="" disabled>👤 Assign Work to Employee...</option>
                            {teamMembers.map(m => (
                              <option key={m.id} value={m.id}>
                                {m.name} — {(m.domains || []).join('/')} ({m.role})
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

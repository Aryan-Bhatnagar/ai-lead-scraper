import { useState } from 'react'
import { Search, MapPin, Globe, Cloud, Camera, Zap } from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'
import LoadingSpinner from '../../components/layout/LoadingSpinner'
import ProviderMultiSelect from '../../components/campaigns/ProviderMultiSelect'
import api from '../../services/api'
import toast from 'react-hot-toast'

export default function Discover() {
  const [industry, setIndustry] = useState('')
  const [location, setLocation] = useState('')
  const [maxResults, setMaxResults] = useState(10)
  const [providers, setProviders] = useState(['google_search'])
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState([])
  const [error, setError] = useState('')

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
          <div className="mt-8 overflow-hidden border border-slate-200 dark:border-slate-800 rounded-xl">
            <table className="w-full border-collapse text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/50">
                <tr>
                  <th className="text-left p-3 border-b dark:border-slate-700 font-semibold text-slate-700 dark:text-slate-300">Company</th>
                  <th className="text-left p-3 border-b dark:border-slate-700 font-semibold text-slate-700 dark:text-slate-300">Website</th>
                  <th className="text-left p-3 border-b dark:border-slate-700 font-semibold text-slate-700 dark:text-slate-300">Location</th>
                  <th className="text-left p-3 border-b dark:border-slate-700 font-semibold text-slate-700 dark:text-slate-300">Industry</th>
                  <th className="text-left p-3 border-b dark:border-slate-700 font-semibold text-slate-700 dark:text-slate-300">Email</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {results.map((r, idx) => (
                  <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                    <td className="p-3 font-medium text-slate-900 dark:text-slate-100">{r.title || 'N/A'}</td>
                    <td className="p-3">
                      <a href={r.url || '#'} target="_blank" rel="noopener noreferrer" className="text-primary-600 dark:text-primary-400 underline hover:text-primary-700 dark:hover:text-primary-300 truncate block max-w-[200px]">
                        {r.url || 'N/A'}
                      </a>
                    </td>
                    <td className="p-3 text-slate-600 dark:text-slate-400">{location || 'N/A'}</td>
                    <td className="p-3 text-slate-600 dark:text-slate-400">{industry || 'N/A'}</td>
                    <td className="p-3 text-slate-600 dark:text-slate-400">{r.email || 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

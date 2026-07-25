import { useState } from 'react'
import { Search } from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'
import LoadingSpinner from '../../components/layout/LoadingSpinner'
import api from '../../services/api'
import toast from 'react-hot-toast'

export default function Discover() {
  const [industry, setIndustry] = useState('')
  const [location, setLocation] = useState('')
  const [maxResults, setMaxResults] = useState(10)
  const [method, setMethod] = useState('standard')
  const [loading, setLoading] = useState(false)
const [enrichLoading, setEnrichLoading] = useState({})
const [expanded, setExpanded] = useState({})
  const [results, setResults] = useState([])
  const [error, setError] = useState('')

  const handleDiscover = async () => {
    if (!industry.trim()) { toast.error('Industry is required'); return }
    if (!location.trim()) { toast.error('Location is required'); return }
    const max = Number(maxResults)
    if (isNaN(max) || max < 1 || max > 50) { toast.error('Maximum results must be a number between 1 and 50'); return }

    setLoading(true)
    setError('')
    setResults([])

    const payload = { industry, location, max_results: max }
    let endpoint = '/api/discover'
    if (method === 'free') endpoint = '/api/discover/free'
    else if (method === 'google') endpoint = '/api/discover/google-maps'

    try {
      const { data } = await api.post(endpoint, payload)
      let discovered = []
      if (Array.isArray(data.results)) { discovered = data.results }
      else if (Array.isArray(data.urls)) { discovered = data.urls.map(url => ({ url })) }
      setResults(discovered)
    } catch (err) {
      const msg = err?.response?.data?.error || err.message || 'Discovery failed'
      setError(msg)
      toast.error(msg)
    } finally { setLoading(false) }
  }

  return (
    <div className="p-4 lg:p-8 space-y-8">
      <PageHeader title="Discover Leads" subtitle="Find new business leads by industry and location." />

      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm max-w-3xl mx-auto">
        <form onSubmit={e => { e.preventDefault(); handleDiscover(); }} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6">
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="industry">Industry</label>
              <input type="text" id="industry" className="w-full border rounded p-2" value={industry} onChange={e => setIndustry(e.target.value)} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="location">Location</label>
              <input type="text" id="location" className="w-full border rounded p-2" value={location} onChange={e => setLocation(e.target.value)} required />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6">
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="max-results">Maximum Results</label>
              <input type="number" id="max-results" className="w-full border rounded p-2" value={maxResults} onChange={e => setMaxResults(e.target.value)} min={1} max={50} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="method">Discovery Method</label>
              <select id="method" className="w-full border rounded p-2" value={method} onChange={e => setMethod(e.target.value)}>
                <option value="standard">Standard Discovery</option>
                <option value="free">Free Discovery</option>
                <option value="google">Google Maps Discovery</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end">
            <button type="submit" className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed" disabled={loading}>
              {loading ? (<svg className="h-4 w-4 animate-spin" viewBox="0 0 100 100"><circle className="opacity-25" cx="50" cy="50" r="20" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" d="M58 12a46 46 0 0 1 22 36" stroke="currentColor" strokeWidth="4" fill="none"/></svg>) : ('Discover Leads')}
            </button>
          </div>
        </form>

        {loading && (
          <div className="flex items-center gap-2 mt-4">
            <LoadingSpinner className="h-5 w-5" />
            <span>Discovering leads…</span>
          </div>
        )}

        {error && <div className="mt-4 text-red-600">{error}</div>}

        {!loading && !error && results.length === 0 && <EmptyState icon={Search} title="No leads discovered yet." />}

        {results.length > 0 && (
          <table className="mt-6 w-full border-collapse">
            <thead>
              <tr>
                <th className="text-left p-2 border-b">Company</th>
                <th className="text-left p-2 border-b">Website</th>
                <th className="text-left p-2 border-b">Location</th>
                <th className="text-left p-2 border-b">Industry</th>
                <th className="text-left p-2 border-b">Email</th>
                <th className="text-left p-2 border-b">Status</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, idx) => (
                <tr key={idx} className="border-b last:border-0">
                  <td className="p-2 font-medium">{r.title || 'N/A'}</td>
                  <td className="p-2"><a href={r.url || '#'} target="_blank" rel="noopener noreferrer" className="text-primary-500 underline hover:text-primary-600">{r.url || 'N/A'}</a></td>
                  <td className="p-2">{location || 'N/A'}</td>
                  <td className="p-2">{industry || 'N/A'}</td>
                  <td className="p-2">N/A</td>
                  <td className="p-2">N/A</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

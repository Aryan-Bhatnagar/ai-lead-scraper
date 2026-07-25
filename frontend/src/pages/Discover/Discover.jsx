import { useState } from 'react'
import { Search } from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'
import DiscoverResultsTable from '../../components/DiscoverResultsTable'
import api from '../../services/api'
import toast from 'react-hot-toast'
import DiscoverStatCard from '../../components/DiscoverStatCard'

export default function Discover() {
  const [industry, setIndustry] = useState('')
  const [location, setLocation] = useState('')
  const [maxResults, setMaxResults] = useState(10)
  const [method, setMethod] = useState('standard')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState([])
  const [error, setError] = useState('')
  // Stats state
  const [totalResults, setTotalResults] = useState(0)
  const [discoveryMethod, setDiscoveryMethod] = useState('')
  const [searchLocation, setSearchLocation] = useState('')
  const [apiSource, setApiSource] = useState('')
  const [executionTime, setExecutionTime] = useState('')

  const handleDiscover = async () => {
    if (!industry.trim()) {
      toast.error('Industry is required')
      return
    }
    if (!location.trim()) {
      toast.error('Location is required')
      return
    }
    const max = Number(maxResults)
    if (isNaN(max) || max < 1 || max > 50) {
      toast.error('Maximum results must be a number between 1 and 50')
      return
    }

    setLoading(true)
    setError('')
    setResults([])
    setTotalResults(0)
    setDiscoveryMethod('')
    setSearchLocation('')
    setApiSource('')
    setExecutionTime('')

    const startTime = Date.now()
    const payload = { industry, location, max_results: max }
    let endpoint = '/api/discover'
    if (method === 'free') endpoint = '/api/discover/free'
    else if (method === 'google') endpoint = '/api/discover/google-maps'

    try {
      const { data } = await api.post(endpoint, payload)
      let discovered = []
      if (Array.isArray(data.results)) {
        discovered = data.results
      } else if (Array.isArray(data.urls)) {
        discovered = data.urls.map(url => ({ url }))
      }
      setResults(discovered)
      setTotalResults(discovered.length)
      setDiscoveryMethod(method)
      setSearchLocation(location)
      setApiSource(endpoint)
      setExecutionTime(Date.now() - startTime)
    } catch (err) {
      const msg = err?.response?.data?.error || err.message || 'Discovery failed'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const retryDiscover = () => {
    handleDiscover()
  }

  return (
    <div className="p-4 lg:p-8 space-y-8 w-full">
      <PageHeader title="Discover Leads" subtitle="Find new business leads by industry and location." />

      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm max-w-6xl mx-auto">
        <form
          onSubmit={e => {
            e.preventDefault()
            handleDiscover()
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6">
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="industry">
                Industry
              </label>
              <input
                type="text"
                id="industry"
                className="w-full border rounded p-2"
                value={industry}
                onChange={e => setIndustry(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="location">
                Location
              </label>
              <input
                type="text"
                id="location"
                className="w-full border rounded p-2"
                value={location}
                onChange={e => setLocation(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6">
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="max-results">
                Maximum Results
              </label>
              <input
                type="number"
                id="max-results"
                className="w-full border rounded p-2"
                value={maxResults}
                onChange={e => setMaxResults(e.target.value)}
                min={1}
                max={50}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="method">
                Discovery Method
              </label>
              <select
                id="method"
                className="w-full border rounded p-2"
                value={method}
                onChange={e => setMethod(e.target.value)}
              >
                <option value="standard">Standard Discovery</option>
                <option value="free">Free Discovery</option>
                <option value="google">Google Maps Discovery</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? (
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 100 100">
                  <circle className="opacity-25" cx="50" cy="50" r="20" stroke="currentColor" strokeWidth="4" fill="none"/>
                  <path className="opacity-75" d="M58 12a46 46 0 0 1 22 36" stroke="currentColor" strokeWidth="4" fill="none"/>
                </svg>
              ) : ('Discover Leads')}
            </button>
          </div>
        </form>

        {/* Statistics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 md:grid-cols-5 gap-4 mt-6">
          <DiscoverStatCard title="Total Results" value={totalResults.toString()} />
          <DiscoverStatCard title="Discovery Method" value={discoveryMethod ? discoveryMethod : 'N/A'} />
          <DiscoverStatCard title="Search Location" value={searchLocation || 'N/A'} />
          <DiscoverStatCard title="API Source" value={apiSource || 'N/A'} />
          <DiscoverStatCard title="Execution Time" value={executionTime ? `${executionTime} ms` : 'N/A'} />
        </div>

        {/* Loading, Error, Empty, Table */}
        {loading && (
          <div className="mt-6">
            {/* Skeleton table */}
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead>
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Company</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Website</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Location</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Industry</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Email</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Status</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-slate-200">
                  {[...Array(5)].map((_, i) => (
                    <tr key={i} className="bg-white">
                      {Array(7).map((_, j) => (
                        <td key={j} className="px-4 py-2">
                          <div className="h-4 bg-gray-200 rounded w-32 animate-pulse" />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 text-red-700 p-4 rounded flex justify-between items-center">
            <span>{error}</span>
            <button
              onClick={retryDiscover}
              className="ml-4 bg-red-600 text-white px-3 py-1 rounded"
              disabled={loading}
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && results.length === 0 && (
          <EmptyState icon={Search} title="No leads discovered yet." />
        )}

        {!loading && !error && results.length > 0 && (
          <DiscoverResultsTable results={results} industry={industry} location={location} />
        )}

      </div>
    </div>
  )
}

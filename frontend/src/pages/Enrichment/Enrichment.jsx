import { useEffect, useState } from 'react'
import { Sparkles } from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'
import LoadingSpinner from '../../components/layout/LoadingSpinner'
import toast from 'react-hot-toast'
import api from '../../services/api'

export default function Enrichment() {
  const [leads, setLeads] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [enriching, setEnriching] = useState(false)

  useEffect(() => {
    fetchLeads()
  }, [])

  async function fetchLeads() {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/api/leads')
      setLeads(data.leads || [])
    } catch (err) {
      const msg = err?.response?.data?.error || err.message || 'Failed to load leads'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleEnrich = async () => {
    if (selectedId === null) return
    const lead = leads.find((l) => l.id === selectedId)
    if (!lead) return
    setEnriching(true)
    try {
      const payload = { leads: [{ website: lead.website }] }
      const { data } = await api.post('/api/leads/enrich', payload)
      const enriched = data.results?.[0] || {}
      setLeads((prev) =>
        prev.map((l) => (l.id === lead.id ? { ...l, ...enriched } : l))
      )
      toast.success('Enrichment complete')
    } catch (err) {
      const msg = err?.response?.data?.error || err.message || 'Enrichment failed'
      toast.error(msg)
    } finally {
      setEnriching(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner className="h-8 w-8" />
        <span className="ml-2">Loading leads…</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="text-red-600">{error}</div>
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Lead Enrichment"
        subtitle="Enhance lead data via web scraping"
      />

      <div className="bg-white rounded-xl border border-slate-200 p-8">
        {leads.length === 0 ? (
          <EmptyState
            icon={Sparkles}
            title="No leads to enrich"
            description="Discover leads first, then enrich them here."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse border border-slate-200">
              <thead>
                <tr className="bg-slate-100">
                  <th className="border p-2 text-left">Select</th>
                  <th className="border p-2 text-left">Company</th>
                  <th className="border p-2 text-left">Website</th>
                  <th className="border p-2 text-left">Email</th>
                  <th className="border p-2 text-left">Phone</th>
                  <th className="border p-2 text-left">LinkedIn</th>
                  <th className="border p-2 text-left">Facebook</th>
                  <th className="border p-2 text-left">Instagram</th>
                  <th className="border p-2 text-left">Address</th>
                  <th className="border p-2 text-left">Business Category</th>
                  <th className="border p-2 text-left">Company Description</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((l) => (
                  <tr key={l.id} className="border-t">
                    <td className="border p-2" title="Select lead">
                      <input
                        type="radio"
                        name="selectedLead"
                        checked={selectedId === l.id}
                        onChange={() => setSelectedId(l.id)}
                      />
                    </td>
                    <td className="border p-2">{l.company_name || 'N/A'}</td>
                    <td className="border p-2">{l.website || 'N/A'}</td>
                    <td className="border p-2">{l.email || 'N/A'}</td>
                    <td className="border p-2">{l.phone || 'N/A'}</td>
                    <td className="border p-2">{l.linkedin || 'N/A'}</td>
                    <td className="border p-2">{l.facebook || 'N/A'}</td>
                    <td className="border p-2">{l.instagram || 'N/A'}</td>
                    <td className="border p-2">{l.address || 'N/A'}</td>
                    <td className="border p-2">{l.business_category || 'N/A'}</td>
                    <td className="border p-2">{l.company_description || 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex justify-end mt-4">
              <button
                disabled={selectedId === null || enriching}
                onClick={handleEnrich}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
              >
                {enriching ? (
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 100 100"><circle className="opacity-25" cx="50" cy="50" r="20" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" d="M58 12a46 46 0 0 1 22 36" stroke="currentColor" strokeWidth="4" fill="none"/></svg>
                ) : ('Enrich')}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

import React, { useState, useEffect, useMemo } from 'react'
import { Search, Mail, Play, CheckCircle, AlertCircle, RefreshCcw } from 'lucide-react'
import toast from 'react-hot-toast'

import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'
import LoadingSpinner from '../../components/layout/LoadingSpinner'

import EmailSummaryCard from '../../components/email/EmailSummaryCard'
import ExtractionProgress from '../../components/email/ExtractionProgress'
import EmailResultsTable from '../../components/email/EmailResultsTable'
import EmailDetailsModal from '../../components/email/EmailDetailsModal'

export default function EmailExtraction() {
  const [candidates, setCandidates] = useState([])
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [loadingCandidates, setLoadingCandidates] = useState(true)
  const [error, setError] = useState(null)

  const [searchQuery, setSearchQuery] = useState('')
  const [isExtracting, setIsExtracting] = useState(false)
  const [results, setResults] = useState([])
  const [selectedResult, setSelectedResult] = useState(null)
  const [progress, setProgress] = useState({ currentCompany: '', processed: 0, total: 0, status: '' })

  const fetchCandidates = async () => {
    setLoadingCandidates(true)
    setError(null)
    try {
      const response = await fetch('/api/leads')
      if (!response.ok) throw new Error('Failed to fetch candidates')
      const data = await response.json()
      // Candidates: have website but no email
      const eligible = (data.leads || []).filter(l => l.website && !l.email)
      setCandidates(eligible)
    } catch (err) {
      setError(err.message)
      toast.error('Failed to load candidates')
    } finally {
      setLoadingCandidates(false)
    }
  }

  useEffect(() => {
    fetchCandidates()
  }, [])

  const filteredCandidates = useMemo(() => {
    return candidates.filter(c =>
      !searchQuery ||
      (c.company_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.website || '').toLowerCase().includes(searchQuery.toLowerCase())
    )
  }, [candidates, searchQuery])

  const stats = useMemo(() => {
    const foundCount = results.filter(r => r.email).length
    const successRate = results.length > 0
      ? Math.round((foundCount / results.length) * 100)
      : 0
    return {
      total: candidates.length,
      selected: selectedIds.size,
      found: foundCount,
      rate: `${successRate}%`
    }
  }, [candidates, selectedIds, results])

  const handleSelectAll = () => {
    if (selectedIds.size === filteredCandidates.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredCandidates.map(c => c.id)))
    }
  }

  const toggleSelect = (id) => {
    const next = new Set(selectedIds)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    setSelectedIds(next)
  }

  const startExtraction = async () => {
    if (selectedIds.size === 0) {
      toast.error('Please select at least one company')
      return
    }

    const selectedLeads = candidates.filter(c => selectedIds.has(c.id))

    setIsExtracting(true)
    setProgress({
      currentCompany: selectedLeads[0]?.company_name || '',
      processed: 0,
      total: selectedLeads.length,
      status: 'Initializing extraction...'
    })
    toast.success('Extraction started')

    try {
      const response = await fetch('/api/leads/extract-emails', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          leads: selectedLeads.map(l => ({ website: l.website }))
        })
      })

      if (!response.ok) throw new Error('Extraction request failed')

      const data = await response.json()
      setResults(data.results || [])
      setProgress(prev => ({ ...prev, processed: prev.total, status: 'Complete' }))
      toast.success('Extraction complete!')
    } catch (err) {
      toast.error(`Extraction failed: ${err.message}`)
      setProgress(prev => ({ ...prev, status: 'Error occurred' }))
    } finally {
      setIsExtracting(false)
    }
  }

  if (error) {
    return (
      <div className="p-8 text-center">
        <div className="bg-red-50 text-red-600 p-4 rounded-lg mb-4 max-w-md mx-auto">{error}</div>
        <button onClick={fetchCandidates} className="px-4 py-2 bg-primary-600 text-white rounded-lg flex items-center gap-2 mx-auto">
          <RefreshCcw size={16} /> Retry
        </button>
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Email Extraction Dashboard"
        subtitle="Identify and extract valid contact emails for the Bilvaleaf sales pipeline."
      />

      {/* 1. Extraction Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <EmailSummaryCard
          title="Total Candidates"
          value={stats.total}
          icon={Database}
        />
        <EmailSummaryCard
          title="Selected Companies"
          value={stats.selected}
          icon={CheckCircle}
        />

        <EmailSummaryCard
          title="Emails Found"
          value={stats.found}
          icon={Mail}
          color="success"
        />

        <EmailSummaryCard
          title="Success Rate"
          value={stats.rate}
          icon={AlertCircle}
        />
      </div>

      {/* 2. Candidate Companies */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-8 shadow-sm">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-6">
          <h3 className="text-lg font-semibold text-slate-800">Candidate Companies</h3>
          <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input
                type="text"
                placeholder="Search company or website..."
                className="pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none w-full sm:w-64"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <button
              onClick={startExtraction}
              disabled={isExtracting || selectedIds.size === 0}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
            >
              <Play size={16} /> Extract Emails
            </button>
          </div>
        </div>

        {loadingCandidates ? (
          <div className="py-12 flex justify-center"><LoadingSpinner size="md" text="Loading candidates..." /></div>
        ) : filteredCandidates.length === 0 ? (
          <div className="py-12"><EmptyState icon={Mail} title="No Candidates Found" description="All available leads already have emails or lack websites." /></div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-100">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 font-semibold text-slate-600">
                    <input
                      type="checkbox"
                      className="mr-2 rounded"
                      checked={selectedIds.size === filteredCandidates.length && filteredCandidates.length > 0}
                      onChange={handleSelectAll}
                    />
                    Company
                  </th>
                  <th className="px-4 py-3 font-semibold text-slate-600">Website</th>
                  <th className="px-4 py-3 font-semibold text-slate-600">Industry</th>
                  <th className="px-4 py-3 font-semibold text-slate-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredCandidates.map(c => (
                  <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 flex items-center gap-3">
                      <input
                        type="checkbox"
                        className="rounded"
                        checked={selectedIds.has(c.id)}
                        onChange={() => toggleSelect(c.id)}
                      />
                      <span className="font-medium text-slate-800">{c.company_name}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-600 truncate max-w-[200px]">{c.website}</td>
                    <td className="px-4 py-3 text-slate-600">{c.industry || 'N/A'}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-700 font-medium">Pending</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 3. Extraction Progress */}
      {isExtracting && (
        <ExtractionProgress
          currentCompany={progress.currentCompany}
          total={progress.total}
          processed={progress.processed}
          status={progress.status}
        />
      )}

      {/* 4. Email Results */}
      {results.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-800 mb-6">Extraction Results</h3>
          <EmailResultsTable
            results={results.map(res => {
              const candidate = candidates.find(c => c.website === res.website)
              return {
                ...res,
                company_name: res.company_name || candidate?.company_name || 'Unknown'
              }
            })}
            onViewDetails={setSelectedResult}
          />
        </div>
      )}

      <EmailDetailsModal
        result={selectedResult}
        isOpen={!!selectedResult}
        onClose={() => setSelectedResult(null)}
      />
    </div>
  )
}

// Small helper for icons since Database wasn't imported
function Database({ size }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M3 5V19A9 3 0 0 0 21 19V5" />
      <path d="M3 12A9 3 0 0 0 21 12" />
    </svg>
  )
}

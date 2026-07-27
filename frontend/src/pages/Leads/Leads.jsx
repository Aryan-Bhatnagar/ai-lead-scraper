import React, { useState, useEffect, useMemo } from 'react'
import { Search, RefreshCcw, Filter } from 'lucide-react'
import toast from 'react-hot-toast'

import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'
import LoadingSpinner from '../../components/layout/LoadingSpinner'
import { Database } from 'lucide-react'

import LeadTable from '../../components/leads/LeadTable'
import LeadDetailsModal from '../../components/leads/LeadDetailsModal'
import DeleteLeadDialog from '../../components/leads/DeleteLeadDialog'
import LeadSummaryCard from '../../components/leads/LeadSummaryCard'

export default function Leads() {
  const [leads, setLeads] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Filters state
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [industryFilter, setIndustryFilter] = useState('All')

  // Modal states
  const [selectedLead, setSelectedLead] = useState(null)
  const [leadToDelete, setLeadToDelete] = useState(null)

  const fetchLeads = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/leads')
      if (!response.ok) throw new Error('Failed to fetch leads')
      const data = await response.json()
      setLeads(data.leads || [])
    } catch (err) {
      setError(err.message)
      toast.error('Failed to load leads')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLeads()
  }, [])

  // Derived State
  const filteredLeads = useMemo(() => {
    return leads.filter(lead => {
      const matchesSearch =
        !search ||
        (lead.company_name || '').toLowerCase().includes(search.toLowerCase()) ||
        (lead.website || '').toLowerCase().includes(search.toLowerCase()) ||
        (lead.email || '').toLowerCase().includes(search.toLowerCase()) ||
        (lead.city || '').toLowerCase().includes(search.toLowerCase()) ||
        (lead.country || '').toLowerCase().includes(search.toLowerCase());

      const matchesStatus = statusFilter === 'All' || lead.lead_status === statusFilter;
      const matchesIndustry = industryFilter === 'All' || lead.industry === industryFilter;

      return matchesSearch && matchesStatus && matchesIndustry;
    })
  }, [leads, search, statusFilter, industryFilter])

  const uniqueIndustries = useMemo(() => {
    const industries = new Set(leads.map(l => l.industry).filter(Boolean))
    return Array.from(industries).sort()
  }, [leads])

  const stats = useMemo(() => ({
    total: leads.length,
    enriched: leads.filter(l => l.lead_status === 'Enriched').length,
    email: leads.filter(l => l.email).length,
    website: leads.filter(l => l.website).length,
  }), [leads])

  const handleDeleteLead = async () => {
    if (!leadToDelete) return

    try {
      const response = await fetch(`/api/leads/${leadToDelete.id}`, {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to delete lead')

      setLeads(prev => prev.filter(l => l.id !== leadToDelete.id))
      toast.success('Lead deleted successfully')
    } catch (err) {
      toast.error('Error deleting lead')
    } finally {
      setLeadToDelete(null)
    }
  }

  if (error) {
    return (
      <div className="p-8 text-center">
        <div className="bg-red-50 text-red-600 p-4 rounded-lg mb-4 max-w-md mx-auto">
          {error}
        </div>
        <button
          onClick={fetchLeads}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2 mx-auto"
        >
          <RefreshCcw size={16} /> Retry
        </button>
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Leads Database"
        subtitle="Manage and view all collected leads."
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <LeadSummaryCard title="Total Leads" value={stats.total} type="total" />
        <LeadSummaryCard title="Enriched Leads" value={stats.enriched} type="enriched" />
        <LeadSummaryCard title="Leads with Email" value={stats.email} type="email" />
        <LeadSummaryCard title="Leads with Website" value={stats.website} type="website" />
      </div>

      {/* Controls */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6 flex flex-col lg:flex-row gap-4 items-center justify-between">
        <div className="flex flex-col sm:flex-row gap-4 w-full lg:w-auto">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              placeholder="Search leads..."
              className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="flex gap-2">
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <select
                className="pl-9 pr-4 py-2 border border-slate-200 rounded-lg bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 appearance-none cursor-pointer"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="All">All Status</option>
                <option value="New">New</option>
                <option value="Enriched">Enriched</option>
              </select>
            </div>

            <div className="relative">
              <select
                className="pl-3 pr-8 py-2 border border-slate-200 rounded-lg bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 appearance-none cursor-pointer"
                value={industryFilter}
                onChange={(e) => setIndustryFilter(e.target.value)}
              >
                <option value="All">All Industries</option>
                {uniqueIndustries.map(ind => (
                  <option key={ind} value={ind}>{ind}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <button
          onClick={fetchLeads}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors disabled:opacity-50"
        >
          <RefreshCcw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh Data
        </button>
      </div>

      {/* Main Content */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <LoadingSpinner size="lg" text="Loading leads..." />
        </div>
      ) : filteredLeads.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12">
          <EmptyState
            icon={Database}
            title="No Leads Found"
            description="Try adjusting your search or filters to find what you're looking for."
          />
        </div>
      ) : (
        <LeadTable
          leads={filteredLeads}
          onView={setSelectedLead}
          onDelete={setLeadToDelete}
        />
      )}

      {/* Modals */}
      <LeadDetailsModal
        lead={selectedLead}
        onClose={() => setSelectedLead(null)}
      />
      <DeleteLeadDialog
        isOpen={!!leadToDelete}
        leadName={leadToDelete?.company_name}
        onClose={() => setLeadToDelete(null)}
        onConfirm={handleDeleteLead}
      />
    </div>
  )
}

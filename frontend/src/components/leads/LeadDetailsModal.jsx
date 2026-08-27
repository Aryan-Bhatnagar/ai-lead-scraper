import { Fragment, useEffect, useState } from 'react'
import IntelligencePanel from '../intelligence/IntelligencePanel'
import api from '../../services/api'
import { Send, Clock, CheckCircle2, AlertCircle } from 'lucide-react'

export default function LeadDetailsModal({ lead, onClose }) {
  const [history, setHistory] = useState([])
  const [loadingHistory, setLoadingHistory] = useState(false)

  useEffect(() => {
    if (lead && lead.id) {
      fetchOutreachHistory(lead.id)
    }
  }, [lead])

  const fetchOutreachHistory = async (leadId) => {
    setLoadingHistory(true)
    try {
      const resp = await api.get(`/api/outreach/lead/${leadId}/history`)
      setHistory(resp.data.logs || [])
    } catch (err) {
      console.error('Failed to fetch outreach history', err)
    } finally {
      setLoadingHistory(false)
    }
  }

  if (!lead) return null

  return (
    <Fragment>
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm"
          onClick={onClose}
        />
        <div className="relative bg-white rounded-xl shadow-xl p-6 w-full max-w-xl z-10 max-h-[90vh] overflow-y-auto space-y-6">
          <button
            className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 transition-colors"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
          <h2 className="text-xl font-semibold text-slate-800">Prospect Details</h2>

          <IntelligencePanel prospect={lead} />

          {/* Lead Information Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3 border-t border-b border-slate-100 py-4">
            {[
              { label: 'Company', value: lead.company_name },
              {
                label: 'Website',
                value: lead.website,
                isLink: true,
              },
              { label: 'Industry', value: lead.industry },
              {
                label: 'Location',
                value: lead.city && lead.country ? `${lead.city}, ${lead.country}` : lead.city || lead.country,
              },
              { label: 'Email', value: lead.email },
              { label: 'Phone', value: lead.phone },
              { label: 'Status', value: lead.lead_status },
              { label: 'Description', value: lead.company_description, fullWidth: true },
              { label: 'LinkedIn', value: lead.linkedin, isLink: true },
              { label: 'Facebook', value: lead.facebook, isLink: true },
              { label: 'Instagram', value: lead.instagram, isLink: true },
              { label: 'Business Category', value: lead.business_category },
            ].map((field, idx) => {
              if (!field.value) return null
              return (
                <div key={idx} className={`${field.fullWidth ? 'sm:col-span-2' : ''} flex flex-col gap-1`}>
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{field.label}</span>
                  <span className="text-sm font-medium text-slate-800">
                    {field.isLink ? (
                      <a
                        href={field.value}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-700 underline transition-colors"
                      >
                        {field.value}
                      </a>
                    ) : (
                      field.value
                    )}
                  </span>
                </div>
              )
            })}
          </div>

          {/* Outreach History Timeline Section */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2 text-sm font-semibold text-slate-800">
              <Send className="h-4 w-4 text-indigo-600" />
              <span>Outreach Cadence History</span>
            </div>

            {loadingHistory ? (
              <div className="text-xs text-slate-400 flex items-center space-x-2 py-2">
                <Clock className="h-3 w-3 animate-spin" />
                <span>Loading activity history...</span>
              </div>
            ) : history.length === 0 ? (
              <div className="p-3 bg-slate-50 rounded-lg text-xs text-slate-400 text-center">
                No outreach dispatches recorded for this lead yet.
              </div>
            ) : (
              <div className="space-y-2">
                {history.map((log) => (
                  <div
                    key={log.id}
                    className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs flex items-start space-x-3"
                  >
                    {log.event_type === 'SENT' || log.event_type === 'DISPATCHED' ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 mt-0.5 flex-shrink-0" />
                    ) : log.event_type === 'FAILED' ? (
                      <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                    ) : (
                      <Clock className="h-4 w-4 text-indigo-500 mt-0.5 flex-shrink-0" />
                    )}
                    <div className="flex-1">
                      <div className="flex justify-between items-center">
                        <span className="font-semibold text-slate-700">
                          Step {log.outreach_step} ({log.outreach_channel}) - {log.event_type}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {new Date(log.created_at).toLocaleString()}
                        </span>
                      </div>
                      {log.message_snippet && (
                        <p className="text-slate-500 mt-1 text-[11px]">{log.message_snippet}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </Fragment>
  )
}

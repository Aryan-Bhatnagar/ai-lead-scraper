import React from 'react'
import { Copy, Eye, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'

export default function EmailResultsTable({ results, onViewDetails }) {
  if (results.length === 0) return null

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    toast.success('Email copied to clipboard')
  }

  return (
    <div className="w-full overflow-x-auto rounded-xl border border border-slate-200 bg-white shadow-sm">
      <table className="w-full text-left border-collapse">
        <thead className="bg-slate-50 border-b border-slate-200">
          <tr>
            <th className="px-4 py-3 text-sm font-semibold text-slate-600">Company</th>
            <th className="px-4 py-3 text-sm font-semibold text-slate-600">Website</th>
            <th className="px-4 py-3 text-sm font-semibold text-slate-600">Extracted Email</th>
            <th className="px-4 py-3 text-sm font-semibold text-slate-600">Source</th>
            <th className="px-4 py-3 text-sm font-semibold text-slate-600">Status</th>
            <th className="px-4 py-3 text-sm font-semibold text-slate-600 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {results.map((res, idx) => {
            const hasEmail = !!res.email;
            return (
              <tr key={idx} className="hover:bg-slate-50 transition-colors group">
                <td className="px-4 py-3 text-sm font-medium text-slate-800">
                  {res.company_name || 'Unknown'}
                </td>
                <td className="px-4 py-3 text-sm text-slate-600 truncate max-w-[150px]">
                  {res.website}
                </td>
                <td className="px-4 py-3 text-sm font-mono text-slate-700">
                  {res.email || <span className="text-slate-300">Not found</span>}
                </td>
                <td className="px-4 py-3 text-sm text-slate-600">
                  {res.email_source_page ? (
                    <a
                      href={res.email_source_page}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline truncate block max-w-[150px]"
                    >
                      {res.email_source_page.replace(/^https?:\/\//, '')}
                    </a>
                  ) : 'N/A'}
                </td>
                <td className="px-4 py-3 text-sm">
                  {hasEmail ? (
                    <div className="flex items-center gap-1.5 text-green-600 font-medium">
                      <CheckCircle2 size={14} />
                      <span>Ready for Outreach</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-slate-400">
                      <XCircle size={14} />
                      <span>No Email Found</span>
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-right">
                  <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    {hasEmail && (
                      <button
                        onClick={() => copyToClipboard(res.email)}
                        className="p-1.5 text-slate-500 hover:text-primary-600 hover:bg-primary-50 rounded-md transition-colors"
                        title="Copy Email"
                      >
                        <Copy size={16} />
                      </button>
                    )}
                    <button
                      onClick={() => onViewDetails(res)}
                      className="p-1.5 text-slate-500 hover:text-primary-600 hover:bg-primary-50 rounded-md transition-colors"
                      title="View Details"
                    >
                      <Eye size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

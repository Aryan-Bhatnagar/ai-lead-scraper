import { Eye, Trash2 } from 'lucide-react'

export default function LeadTable({ leads, onView, onDelete }) {
  if (leads.length === 0) return null

  return (
    <div className="w-full overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            <th className="px-4 py-3 text-sm font-semibold text-slate-600">Company</th>
            <th className="px-4 py-3 text-sm font-semibold text-slate-600">Website</th>
            <th className="px-4 py-3 text-sm font-semibold text-slate-600">Industry</th>
            <th className="px-4 py-3 text-sm font-semibold text-slate-600">Email</th>
            <th className="px-4 py-3 text-sm font-semibold text-slate-600">Location</th>
            <th className="px-4 py-3 text-sm font-semibold text-slate-600">Status</th>
            <th className="px-4 py-3 text-sm font-semibold text-slate-600 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {leads.map((lead) => (
            <tr
              key={lead.id}
              className="hover:bg-slate-50 transition-colors group"
            >
              <td className="px-4 py-3 text-sm font-medium text-slate-800 truncate max-w-[200px]">
                {lead.company_name || 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm text-slate-600 truncate max-w-[200px]">
                {lead.website ? (
                  <a href={lead.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                    {lead.website.replace(/^https?:\/\//, '')}
                  </a>
                ) : 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm text-slate-600">
                {lead.industry || 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm text-slate-600">
                {lead.email || 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm text-slate-600">
                {lead.city ? `${lead.city}, ${lead.country}` : 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  lead.lead_status === 'Enriched'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-blue-100 text-blue-700'
                }`}>
                  {lead.lead_status || 'New'}
                </span>
              </td>
              <td className="px-4 py-3 text-sm text-right">
                <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => onView(lead)}
                    className="p-1.5 text-slate-500 hover:text-primary-600 hover:bg-primary-50 rounded-md transition-colors"
                    title="View Details"
                  >
                    <Eye size={16} />
                  </button>
                  <button
                    onClick={() => onDelete(lead)}
                    className="p-1.5 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                    title="Delete Lead"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

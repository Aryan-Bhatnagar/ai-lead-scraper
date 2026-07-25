import React from 'react'
import { toast } from 'react-hot-toast'

export default function DiscoverResultsTable({ results, industry, location }) {
  const handleAction = action => {
    toast('Coming in Phase 13C')
  }

  return (
    <div className="mt-6 overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Company</th>
            <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Website</th>
            <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Location</th>
            <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Industry</th>
            <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Email</th>
            <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
            <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-slate-200">
          {results.map((r, idx) => (
            <tr key={idx} className="hover:bg-slate-50">
              <td className="px-4 py-2 font-medium text-slate-900 whitespace-pre-line">{r.title || 'N/A'}</td>
              <td className="px-4 py-2 whitespace-nowrap"><a href={r.url || '#'} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">{r.url || 'N/A'}</a></td>
              <td className="px-4 py-2 whitespace-pre-line">{location || 'N/A'}</td>
              <td className="px-4 py-2 whitespace-pre-line">{industry || 'N/A'}</td>
              <td className="px-4 py-2">{r.email || 'N/A'}</td>
              <td className="px-4 py-2">{r.status || 'N/A'}</td>
              <td className="px-4 py-2">
                <button onClick={() => handleAction('view')} className="text-sm text-primary-600 hover:underline mr-2">View</button>
                <button onClick={() => handleAction('enrich')} className="text-sm text-primary-600 hover:underline mr-2">Enrich</button>
                <button onClick={() => handleAction('extractEmail')} className="text-sm text-primary-600 hover:underline">Extract Email</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

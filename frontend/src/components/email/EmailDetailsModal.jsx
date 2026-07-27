import React from 'react'

export default function EmailDetailsModal({ result, isOpen, onClose }) {
  if (!isOpen || !result) return null

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
      <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl p-6 w-full max-w-lg z-10 max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 transition-colors"
        >
          ✕
        </button>

        <h2 className="text-xl font-semibold mb-6 text-slate-800">Extraction Details</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-4">
          {[
            { label: 'Company', value: result.company_name },
            { label: 'Website', value: result.website, isLink: true },
            { label: 'Extracted Email', value: result.email },
            { label: 'Source URL', value: result.email_source_page, isLink: true },
            { label: 'Source Type', value: result.email_source_type },
            { label: 'Status', value: result._error ? 'Failed' : (result.email ? 'Found' : 'Not Found') },
          ].map((field, idx) => {
            if (!field.value) return null;
            return (
              <div key={idx} className="flex flex-col gap-1">
                <span className="text-sm font-medium text-slate-500">{field.label}</span>
                <span className="text-slate-800">
                  {field.isLink ? (
                    <a href={field.value} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline truncate block max-w-full">
                      {field.value}
                    </a>
                  ) : (
                    field.value
                  )}
                </span>
              </div>
            );
          })}
        </div>

        {result.pages_checked && result.pages_checked.length > 0 && (
          <div className="mt-6 pt-6 border-t border-slate-100">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Pages Checked</h3>
            <div className="flex flex-wrap gap-2">
              {result.pages_checked.map((url, idx) => (
                <span key={idx} className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded border border-slate-200 truncate max-w-[200px]">
                  {url.replace(/^https?:\/\//, '')}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

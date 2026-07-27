import { Fragment } from 'react'

export default function LeadDetailsModal({ lead, onClose }) {
  if (!lead) return null

  return (
    <Fragment>
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm"
          onClick={onClose}
        />
        <div className="relative bg-white rounded-xl shadow-xl p-6 w-full max-w-xl z-10 max-h-[90vh] overflow-y-auto">
          <button
            className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 transition-colors"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
          <h2 className="text-xl font-semibold mb-6 text-slate-800">Lead Details</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3">
            {[
              { label: 'Company', value: lead.company_name },
              {
                label: 'Website',
                value: lead.website,
                isLink: true
              },
              { label: 'Industry', value: lead.industry },
              {
                label: 'Location',
                value: lead.city && lead.country ? `${lead.city}, ${lead.country}` : lead.city || lead.country
              },
              { label: 'Email', value: lead.email },
              { label: 'Phone', value: lead.phone },
              { label: 'Description', value: lead.company_description, fullWidth: true },
              { label: 'LinkedIn', value: lead.linkedin, isLink: true },
              { label: 'Facebook', value: lead.facebook, isLink: true },
              { label: 'Instagram', value: lead.instagram, isLink: true },
              { label: 'Business Category', value: lead.business_category },
            ].map((field, idx) => {
              if (!field.value) return null;
              return (
                <div key={idx} className={`${field.fullWidth ? 'sm:col-span-2' : ''} flex flex-col gap-1`}>
                  <span className="text-sm font-medium text-slate-500">{field.label}</span>
                  <span className="text-slate-800">
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
              );
            })}
          </div>
        </div>
      </div>
    </Fragment>
  )
}

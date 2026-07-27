import { Fragment } from 'react'

export default function DeleteLeadDialog({ isOpen, onClose, onConfirm, leadName }) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
      <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl p-6 w-full max-w-md z-10">
        <div className="flex flex-col items-center text-center">
          <div className="w-12 h-12 bg-red-100 text-red-600 rounded-full flex items-center justify-center mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.023 0 1.864-1.023 1.864-2.046V5.17C17.864 4.147 16.98 3.124 16.007 3.124H7.993C7.02 3.124 6.136 4.147 6.136 5.17V14.91C6.136 15.933 7.02 16.956 7.993 16.956" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-slate-800 mb-2">Delete Lead</h2>
          <p className="text-slate-600 mb-6">
            Are you sure you want to delete <span className="font-semibold text-slate-800">{leadName}</span>? This action cannot be undone.
          </p>
          <div className="flex gap-3 w-full">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors font-medium"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

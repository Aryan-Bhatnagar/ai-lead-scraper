import React from 'react'

export default function ExtractionProgress({ currentCompany, total, processed, status }) {
  const progress = Math.round((processed / total) * 100) || 0

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-800">Extraction in Progress</h3>
          <p className="text-sm text-slate-500">
            {status || `Processing leads... (${processed}/${total})`}
          </p>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold text-primary-600">{progress}%</span>
        </div>
      </div>

      <div className="w-full bg-slate-100 rounded-full h-3 mb-4 overflow-hidden">
        <div
          className="bg-primary-600 h-full transition-all duration-500 ease-out rounded-full"
          style={{ width: `${progress}%` }}
        />
      </div>

      {currentCompany && (
        <div className="flex items-center gap-2 text-sm text-slate-600 italic">
          <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
          Currently extracting: <span className="font-medium">{currentCompany}</span>
        </div>
      )}
    </div>
  )
}

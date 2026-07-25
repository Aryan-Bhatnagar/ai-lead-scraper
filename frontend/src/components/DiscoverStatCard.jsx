import React from 'react'

export default function DiscoverStatCard({ title, value }) {
  return (
    <div className="bg-white rounded-lg shadow p-4 flex-1">
      <p className="text-sm text-slate-500 font-medium">{title}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
    </div>
  )
}

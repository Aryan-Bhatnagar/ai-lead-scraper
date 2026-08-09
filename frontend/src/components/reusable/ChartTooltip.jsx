/**
 * ChartTooltip
 * ------------
 * Shared Recharts custom tooltip. Dark-mode aware via the `dark` class
 * on <html>, consistent with the app's glass-card aesthetic.
 */
export default function ChartTooltip({ active, payload, label, formatter }) {
  if (!active || !payload || payload.length === 0) return null

  const isDark =
    typeof document !== 'undefined' && document.documentElement.classList.contains('dark')

  return (
    <div
      className="rounded-xl border px-3 py-2 shadow-lg text-xs"
      style={{
        background: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.97)',
        borderColor: isDark ? 'rgba(71, 85, 105, 0.6)' : '#e2e8f0',
        backdropFilter: 'blur(8px)',
      }}
    >
      {label != null && label !== '' && (
        <p className="mb-1 font-semibold text-slate-700 dark:text-slate-200">{label}</p>
      )}
      <ul className="space-y-0.5">
        {payload.map((entry) => (
          <li key={entry.dataKey ?? entry.name} className="flex items-center gap-2">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: entry.color || entry.payload?.fill || '#6366f1' }}
            />
            <span className="text-slate-500 dark:text-slate-400">{entry.name}:</span>
            <span className="font-semibold text-slate-800 dark:text-slate-100 tabular-nums">
              {formatter ? formatter(entry.value, entry) : entry.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

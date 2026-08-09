/**
 * Format a duration in milliseconds into a compact human string.
 * Input is always derived from backend timestamps — never fabricated.
 */
export function formatDurationMs(ms) {
  if (ms == null || Number.isNaN(ms) || ms < 0) return '—'
  const seconds = Math.round(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ${minutes % 60}m`
  const days = Math.floor(hours / 24)
  return `${days}d ${hours % 24}h`
}

/** Duration between two ISO timestamps (end defaults to now for running campaigns). */
export function campaignDurationMs(startedAt, completedAt) {
  if (!startedAt) return null
  const start = new Date(startedAt).getTime()
  if (Number.isNaN(start)) return null
  const end = completedAt ? new Date(completedAt).getTime() : Date.now()
  if (Number.isNaN(end) || end < start) return null
  return end - start
}

/** Short date-time for the campaign start stamp. */
export function formatStartedAt(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

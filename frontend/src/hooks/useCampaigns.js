import { useCallback, useEffect, useRef, useState } from 'react'
import {
  listCampaigns,
  startCampaign,
  pauseCampaign,
  resumeCampaign,
  cancelCampaign,
  getCampaign,
  getCampaignProgress,
} from '../services/campaignService'

export const POLL_INTERVAL_MS = 5000

const ACTIVE_STATUSES = new Set(['running', 'paused', 'pending', 'queued', 'in_progress'])

/**
 * useCampaigns
 * ------------
 * Polls GET /api/campaigns every 5 seconds (live refresh). No mock
 * data — purely server-driven with retry-friendly error state.
 */
export function useCampaigns(pollMs = POLL_INTERVAL_MS) {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const timerRef = useRef(null)
  const mountedRef = useRef(true)

  const fetchCampaigns = useCallback(async (initial = false) => {
    if (initial) setLoading(true)
    try {
      const list = await listCampaigns()
      if (!mountedRef.current) return
      setCampaigns(list)
      setError(null)
      setLastUpdated(new Date())
    } catch (err) {
      if (!mountedRef.current) return
      setError(err)
    } finally {
      if (mountedRef.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    fetchCampaigns(true)
    timerRef.current = setInterval(() => fetchCampaigns(false), pollMs)
    return () => {
      mountedRef.current = false
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [fetchCampaigns, pollMs])

  return {
    campaigns,
    loading,
    error,
    lastUpdated,
    refetch: () => fetchCampaigns(true),
  }
}

/** Derives summary statistics from the campaign list (server data only). */
export function deriveCampaignStats(campaigns) {
  const running = campaigns.filter((c) => c.status === 'running').length
  const completed = campaigns.filter((c) => c.status === 'completed').length
  const totalLeads = campaigns.reduce((sum, c) => sum + (c.leadsDiscovered || 0), 0)

  const startOfToday = new Date()
  startOfToday.setHours(0, 0, 0, 0)
  const leadsToday = campaigns
    .filter((c) => {
      const stamp = c.startedAt || c.completedAt
      return stamp && new Date(stamp) >= startOfToday
    })
    .reduce((sum, c) => sum + (c.leadsDiscovered || 0), 0)

  const avgLeads = campaigns.length ? Math.round(totalLeads / campaigns.length) : 0

  return { running, completed, leadsToday, avgLeads, total: campaigns.length }
}

/** True while a campaign still has a live state worth polling fast. */
export function isCampaignActive(campaign) {
  return campaign ? ACTIVE_STATUSES.has(campaign.status) : false
}

/**
 * useCampaignDetails
 * ------------------
 * Fetches GET /api/campaigns/<id> and polls GET /api/campaigns/<id>/progress
 * every 5 seconds while the campaign is active.
 */
export function useCampaignDetails(id, pollMs = POLL_INTERVAL_MS) {
  const [campaign, setCampaign] = useState(null)
  const [progress, setProgress] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const mountedRef = useRef(true)
  const timerRef = useRef(null)
  const campaignRef = useRef(null)

  const load = useCallback(
    async (initial = false) => {
      if (!id) return
      if (initial) {
        setLoading(true)
        setError(null)
      }
      try {
        // The detail document is fetched on first load and whenever we do
        // not yet have one; progress is lightweight and polled every cycle.
        let detail = null
        if (initial || !campaignRef.current) {
          detail = await getCampaign(id)
          campaignRef.current = detail
        }
        let prog = null
        try {
          prog = await getCampaignProgress(id)
        } catch {
          prog = null // progress endpoint is best-effort; keep detail data
        }
        if (!mountedRef.current) return
        if (detail) {
          setCampaign(mergeProgressIntoCampaign(detail, prog))
        } else if (prog) {
          setCampaign((prev) => (prev ? mergeProgressIntoCampaign(prev, prog) : prev))
        }
        if (prog) setProgress(prog)
        setError(null)
      } catch (err) {
        if (mountedRef.current) setError(err)
      } finally {
        if (mountedRef.current) setLoading(false)
      }
    },
    [id]
  )

  useEffect(() => {
    mountedRef.current = true
    campaignRef.current = null
    setCampaign(null)
    setProgress(null)
    load(true)
    timerRef.current = setInterval(() => load(false), pollMs)
    return () => {
      mountedRef.current = false
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [load, pollMs])

  return { campaign, progress, loading, error, refetch: () => load(true) }
}

function mergeProgressIntoCampaign(campaign, progress) {
  if (!progress) return campaign
  return {
    ...campaign,
    status: progress.status || campaign.status,
    queriesCompleted: progress.queriesCompleted ?? campaign.queriesCompleted,
    queriesTotal: progress.queriesTotal ?? campaign.queriesTotal,
    leadsDiscovered: progress.leadsDiscovered ?? campaign.leadsDiscovered,
    averageScore: progress.averageScore ?? campaign.averageScore,
    progressPercent: progress.percent ?? campaign.progressPercent,
    progress,
  }
}

/**
 * useCampaignActions
 * ------------------
 * Thin wrappers around the action endpoints with error propagation
 * (callers render toasts). Always refreshes the provided callback.
 */
export function useCampaignActions(onChanged = () => {}) {
  const run = useCallback(
    async (fn, id) => {
      await fn(id)
      await onChanged()
    },
    [onChanged]
  )

  return {
    start: startCampaign,
    pause: (id) => run(pauseCampaign, id),
    resume: (id) => run(resumeCampaign, id),
    cancel: (id) => run(cancelCampaign, id),
  }
}

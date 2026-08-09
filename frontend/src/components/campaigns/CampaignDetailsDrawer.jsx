import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import {
  X,
  Users,
  Gauge,
  Clock,
  ListChecks,
  Search,
  Globe,
  MapPin,
  Layers,
  Pause,
  Play,
  XCircle,
  RefreshCcw,
  Timer,
  Hourglass,
} from 'lucide-react'
import CampaignStatusBadge from './CampaignStatusBadge'
import CampaignProgressBar from './CampaignProgressBar'
import SourceBadge from '../reusable/badges/SourceBadge'
import { PROVIDERS } from './ProviderMultiSelect'
import { useCampaignDetails } from '../../hooks/useCampaigns'
import { pauseCampaign, resumeCampaign, cancelCampaign } from '../../services/campaignService'
import { formatDurationMs, formatStartedAt } from '../../utils/formatDuration'
import LoadingState from '../reusable/LoadingState'

function providerLabel(id) {
  return PROVIDERS.find((p) => p.id === id)?.label || id
}

function MetricRow({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2 border-b border-slate-100 dark:border-slate-800 last:border-0">
      <span className="inline-flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 shrink-0">
        <Icon className="w-3.5 h-3.5" />
        {label}
      </span>
      <span className="text-sm font-medium text-slate-800 dark:text-slate-100 text-right truncate">{value}</span>
    </div>
  )
}

/**
 * CampaignDetailsDrawer — right-side slide-over with live polling.
 * Polls /api/campaigns/<id> and /api/campaigns/<id>/progress every 5s.
 */
export default function CampaignDetailsDrawer({ campaign: summary, onClose, onChanged }) {
  const id = summary?.id
  const open = !!summary
  const { campaign, progress, loading, error, refetch } = useCampaignDetails(id)
  const [acting, setActing] = useState(null)
  const [nowTick, setNowTick] = useState(Date.now())

  const data = campaign || summary
  const prog = progress || data?.progress || null
  const status = (prog?.status || data?.status || 'unknown').toLowerCase()
  const isRunning = status === 'running' || status === 'in_progress'
  const isPaused = status === 'paused'
  const isFinished = status === 'completed' || status === 'failed' || status === 'cancelled' || status === 'canceled'

  // Re-render every second so elapsed time updates live between polls
  useEffect(() => {
    if (!isRunning) return undefined
    const t = setInterval(() => setNowTick(Date.now()), 1000)
    return () => clearInterval(t)
  }, [isRunning])

  // Notify the parent list when terminal state is reached so it refreshes
  useEffect(() => {
    if (isFinished && summary && summary.status !== status) onChanged?.()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status])

  // Close on Escape
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const startMs = data?.startedAt ? new Date(data.startedAt).getTime() : null
  const endMs =
    isFinished && data?.completedAt ? new Date(data.completedAt).getTime() : nowTick
  const elapsedSeconds =
    prog?.elapsedSeconds != null
      ? prog.elapsedSeconds
      : startMs
        ? Math.max(0, Math.round((endMs - startMs) / 1000))
        : null
  const remainingSeconds = prog?.estimatedRemainingSeconds ?? null

  const queriesCompleted = prog?.queriesCompleted ?? data?.queriesCompleted ?? 0
  const queriesTotal = prog?.queriesTotal ?? data?.queriesTotal ?? 0
  const percent =
    prog?.percent != null
      ? prog.percent
      : data?.progressPercent != null
        ? data.progressPercent
        : queriesTotal > 0
          ? Math.round((queriesCompleted / queriesTotal) * 100)
          : 0

  const act = async (action, fn, successMsg) => {
    setActing(action)
    try {
      await fn(id)
      toast.success(successMsg)
      await refetch()
      onChanged?.()
    } catch (err) {
      toast.error(err?.response?.data?.error || `Failed to ${action} campaign`)
    } finally {
      setActing(null)
    }
  }

  return (
    <div className={`fixed inset-0 z-50 ${open ? '' : 'pointer-events-none'}`}>
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-950/50 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <aside className="absolute right-0 top-0 h-full w-full sm:max-w-md bg-white dark:bg-slate-900 shadow-2xl border-l border-slate-200 dark:border-slate-800 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-5 py-4 border-b border-slate-200 dark:border-slate-800 shrink-0">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-base font-bold text-slate-900 dark:text-white truncate">
                {data?.name || 'Campaign'}
              </h2>
              <CampaignStatusBadge status={status} />
            </div>
            <p className="mt-0.5 text-xs text-slate-400">
              Started {formatStartedAt(data?.startedAt)}
              {isRunning && (
                <span className="ml-2 inline-flex items-center gap-1 text-success-600 dark:text-success-500">
                  <span className="w-1.5 h-1.5 rounded-full bg-success-500 animate-pulse-dot" />
                  Live · refreshing every 5s
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={() => refetch()}
              className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
              title="Refresh"
              aria-label="Refresh progress"
            >
              <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
              aria-label="Close details"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
          {error && !data ? (
            <div className="text-center py-10 animate-fade-in">
              <p className="text-sm text-danger-600 dark:text-danger-500 mb-3">
                {error.response?.data?.error || 'Unable to load campaign details.'}
              </p>
              <button
                onClick={() => refetch()}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:scale-[0.98] transition-all"
              >
                <RefreshCcw className="w-4 h-4" />
                Retry
              </button>
            </div>
          ) : loading && !data ? (
            <LoadingState text="Loading campaign details…" />
          ) : (
            <>
              {/* Progress */}
              <section className="rounded-2xl border border-slate-200 dark:border-slate-800 p-4">
                <CampaignProgressBar percent={percent} status={status} />
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-slate-50 dark:bg-slate-800/50 px-3 py-2.5">
                    <p className="text-[11px] text-slate-400 uppercase tracking-wide">Queries done</p>
                    <p className="text-lg font-bold text-slate-900 dark:text-white tabular-nums">{queriesCompleted}</p>
                  </div>
                  <div className="rounded-xl bg-slate-50 dark:bg-slate-800/50 px-3 py-2.5">
                    <p className="text-[11px] text-slate-400 uppercase tracking-wide">Remaining</p>
                    <p className="text-lg font-bold text-slate-900 dark:text-white tabular-nums">
                      {queriesTotal > 0 ? Math.max(0, queriesTotal - queriesCompleted) : '—'}
                    </p>
                  </div>
                </div>
              </section>

              {/* Live progress view */}
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
                  Current Execution
                </h3>
                <div className="rounded-2xl border border-slate-200 dark:border-slate-800 px-4 py-1">
                  <MetricRow icon={Search} label="Current Query" value={prog?.currentQuery || '—'} />
                  <MetricRow
                    icon={Layers}
                    label="Current Provider"
                    value={prog?.currentProvider ? providerLabel(prog.currentProvider) : '—'}
                  />
                  <MetricRow icon={Layers} label="Current Industry" value={prog?.currentIndustry || '—'} />
                  <MetricRow icon={MapPin} label="Current City" value={prog?.currentCity || '—'} />
                  <MetricRow icon={Globe} label="Current Country" value={prog?.currentCountry || '—'} />
                  <MetricRow
                    icon={Timer}
                    label="Elapsed Time"
                    value={elapsedSeconds != null ? formatDurationMs(elapsedSeconds * 1000) : '—'}
                  />
                  <MetricRow
                    icon={Hourglass}
                    label="Estimated Remaining"
                    value={remainingSeconds != null ? formatDurationMs(remainingSeconds * 1000) : '—'}
                  />
                </div>
              </section>

              {/* Results */}
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
                  Results So Far
                </h3>
                <div className="rounded-2xl border border-slate-200 dark:border-slate-800 px-4 py-1">
                  <MetricRow
                    icon={Users}
                    label="Leads Discovered"
                    value={prog?.leadsDiscovered ?? data?.leadsDiscovered ?? 0}
                  />
                  <MetricRow
                    icon={Gauge}
                    label="Average Score"
                    value={
                      (prog?.averageScore ?? data?.averageScore) != null
                        ? Math.round(prog?.averageScore ?? data?.averageScore)
                        : '—'
                    }
                  />
                  <MetricRow icon={Clock} label="Duration" value={elapsedSeconds != null ? formatDurationMs(elapsedSeconds * 1000) : '—'} />
                  <MetricRow
                    icon={ListChecks}
                    label="Queries"
                    value={`${queriesCompleted} / ${queriesTotal || '—'}`}
                  />
                </div>
              </section>

              {/* Targeting */}
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
                  Targeting
                </h3>
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {(data?.providers || []).length > 0 ? (
                      (data.providers || []).map((p) => <SourceBadge key={p} source={providerLabel(p)} />)
                    ) : (
                      <span className="text-xs text-slate-400">No providers recorded</span>
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className="rounded-xl bg-slate-50 dark:bg-slate-800/50 px-3 py-2">
                      <p className="text-[10px] uppercase tracking-wide text-slate-400 mb-1">Industries</p>
                      <p className="text-slate-700 dark:text-slate-200 font-medium break-words">
                        {(data?.industries || []).join(', ') || '—'}
                      </p>
                    </div>
                    <div className="rounded-xl bg-slate-50 dark:bg-slate-800/50 px-3 py-2">
                      <p className="text-[10px] uppercase tracking-wide text-slate-400 mb-1">Cities</p>
                      <p className="text-slate-700 dark:text-slate-200 font-medium break-words">
                        {(data?.cities || []).join(', ') || '—'}
                      </p>
                    </div>
                    <div className="rounded-xl bg-slate-50 dark:bg-slate-800/50 px-3 py-2">
                      <p className="text-[10px] uppercase tracking-wide text-slate-400 mb-1">Countries</p>
                      <p className="text-slate-700 dark:text-slate-200 font-medium break-words">
                        {(data?.countries || []).join(', ') || '—'}
                      </p>
                    </div>
                  </div>
                </div>
              </section>
            </>
          )}
        </div>

        {/* Actions footer */}
        {!isFinished && data && (
          <div className="px-5 py-4 border-t border-slate-200 dark:border-slate-800 flex items-center gap-2 shrink-0">
            {isRunning && (
              <button
                onClick={() => act('pause', pauseCampaign, 'Campaign paused')}
                disabled={!!acting}
                className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium bg-amber-500 text-white rounded-lg hover:bg-amber-600 active:scale-[0.98] transition-all disabled:opacity-50"
              >
                <Pause className="w-4 h-4" />
                {acting === 'pause' ? 'Pausing…' : 'Pause'}
              </button>
            )}
            {isPaused && (
              <button
                onClick={() => act('resume', resumeCampaign, 'Campaign resumed')}
                disabled={!!acting}
                className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium bg-success-600 text-white rounded-lg hover:bg-success-700 active:scale-[0.98] transition-all disabled:opacity-50"
              >
                <Play className="w-4 h-4" />
                {acting === 'resume' ? 'Resuming…' : 'Resume'}
              </button>
            )}
            <button
              onClick={() => act('cancel', cancelCampaign, 'Campaign cancelled')}
              disabled={!!acting}
              className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium bg-white dark:bg-slate-900 text-danger-600 dark:text-danger-500 border border-danger-200 dark:border-danger-500/30 rounded-lg hover:bg-danger-50 dark:hover:bg-danger-500/10 active:scale-[0.98] transition-all disabled:opacity-50"
            >
              <XCircle className="w-4 h-4" />
              {acting === 'cancel' ? 'Cancelling…' : 'Cancel'}
            </button>
          </div>
        )}
      </aside>
    </div>
  )
}

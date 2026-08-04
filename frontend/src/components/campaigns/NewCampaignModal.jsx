import { useEffect, useState } from 'react'
import { X, Search, MapPin, Globe, Layers, Play, RotateCcw } from 'lucide-react'
import ProviderMultiSelect from './ProviderMultiSelect'

const inputCls =
  'w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-700 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-400 transition-all'

const labelCls = 'text-xs font-medium text-slate-500 dark:text-slate-400'

function Field({ icon: Icon, label, hint, children }) {
  return (
    <div className="space-y-1.5">
      <label className={`${labelCls} inline-flex items-center gap-1.5`}>
        {Icon && <Icon className="w-3.5 h-3.5" />}
        {label}
      </label>
      {children}
      {hint && <p className="text-[11px] text-slate-400 dark:text-slate-500">{hint}</p>}
    </div>
  )
}

const INITIAL = {
  name: '',
  industries: '',
  cities: '',
  countries: '',
  providers: [],
  max_results: 20,
  retry_count: 2,
}

/**
 * NewCampaignModal — POST /api/campaigns/start.
 * On success the backend returns the created campaign record.
 */
export default function NewCampaignModal({ open, onClose, onSubmit }) {
  const [form, setForm] = useState(INITIAL)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // Reset form whenever the modal (re)opens
  useEffect(() => {
    if (open) {
      setForm(INITIAL)
      setError(null)
      setSubmitting(false)
    }
  }, [open])

  // Close on Escape
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && !submitting && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, submitting, onClose])

  if (!open) return null

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const canSubmit =
    form.industries.trim().length > 0 && form.providers.length > 0 && !submitting

  const listify = (raw) =>
    raw
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    const industries = listify(form.industries)
    if (industries.length === 0) return setError('At least one industry is required.')
    if (form.providers.length === 0) return setError('Select at least one provider.')
    const maxResults = Number(form.max_results)
    if (!Number.isFinite(maxResults) || maxResults < 1 || maxResults > 500) {
      return setError('Maximum results must be between 1 and 500.')
    }
    const retryCount = Number(form.retry_count)
    if (!Number.isFinite(retryCount) || retryCount < 0 || retryCount > 10) {
      return setError('Retry count must be between 0 and 10.')
    }

    const payload = {
      industries,
      cities: listify(form.cities),
      countries: listify(form.countries),
      providers: form.providers,
      max_results: maxResults,
      retry_count: retryCount,
    }
    if (form.name.trim()) payload.name = form.name.trim()

    setSubmitting(true)
    try {
      await onSubmit(payload)
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to start campaign. Please retry.')
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-6">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-950/50 backdrop-blur-sm animate-fade-in"
        onClick={() => !submitting && onClose()}
        aria-hidden="true"
      />

      <div className="relative w-full sm:max-w-2xl max-h-[92vh] overflow-y-auto glass-card rounded-t-2xl sm:rounded-2xl shadow-2xl animate-fade-up">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-5 sm:px-6 pt-5 pb-4 border-b border-slate-200/80 dark:border-slate-700/60 sticky top-0 bg-inherit backdrop-blur-xl rounded-t-2xl z-10">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Start New Campaign</h2>
            <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
              Launch a multi-provider discovery campaign.
            </p>
          </div>
          <button
            onClick={() => !submitting && onClose()}
            className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-5 sm:px-6 py-5 space-y-5">
          <Field icon={Layers} label="Campaign Name">
            <input
              type="text"
              value={form.name}
              onChange={set('name')}
              placeholder="e.g. Q3 Dental Clinics — West Coast"
              className={inputCls}
            />
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Field icon={Search} label="Industries" hint="Required. Comma-separated.">
              <input
                type="text"
                value={form.industries}
                onChange={set('industries')}
                placeholder="Dental clinics, plumbers"
                className={inputCls}
                required
              />
            </Field>
            <Field icon={MapPin} label="Cities" hint="Optional. Comma-separated.">
              <input
                type="text"
                value={form.cities}
                onChange={set('cities')}
                placeholder="Austin, Denver"
                className={inputCls}
              />
            </Field>
            <Field icon={Globe} label="Countries" hint="Optional. Comma-separated.">
              <input
                type="text"
                value={form.countries}
                onChange={set('countries')}
                placeholder="United States"
                className={inputCls}
              />
            </Field>
          </div>

          <Field label="Providers">
            <ProviderMultiSelect value={form.providers} onChange={(v) => setForm((f) => ({ ...f, providers: v }))} />
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Maximum Results" hint="Total leads cap (1 – 500).">
              <input
                type="number"
                min="1"
                max="500"
                value={form.max_results}
                onChange={set('max_results')}
                className={inputCls}
                required
              />
            </Field>
            <Field label="Retry Count" hint="Retries per failed query (0 – 10).">
              <input
                type="number"
                min="0"
                max="10"
                value={form.retry_count}
                onChange={set('retry_count')}
                className={inputCls}
                required
              />
            </Field>
          </div>

          {error && (
            <div className="flex items-start gap-2 text-sm text-danger-600 dark:text-danger-500 bg-danger-50 dark:bg-danger-500/10 border border-danger-200/60 dark:border-danger-500/20 rounded-lg px-3 py-2.5 animate-fade-in">
              <RotateCcw className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Footer */}
          <div className="flex flex-col-reverse sm:flex-row sm:items-center justify-end gap-3 pt-4 border-t border-slate-200/80 dark:border-slate-700/60">
            <button
              type="button"
              onClick={() => !submitting && onClose()}
              className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className="inline-flex items-center justify-center gap-2 px-5 py-2 text-sm font-semibold bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="w-4 h-4" />
              {submitting ? 'Starting…' : 'Start Campaign'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

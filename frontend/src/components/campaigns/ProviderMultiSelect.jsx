import { Globe, MapPin, Linkedin, Instagram, Camera, Cloud } from 'lucide-react'
import GoogleMark from '../badges/GoogleMark'

/**
 * Provider catalog for campaign targeting.
 * `implemented` reflects whether the backend currently ships a scraper
 * for the provider — unimplemented providers render disabled in the UI.
 */
export const PROVIDERS = [
  { id: 'google', label: 'Google', icon: GoogleMark, implemented: true },
  { id: 'google_maps', label: 'Google Maps', icon: MapPin, implemented: true },
  { id: 'google_maps_scraper_kit', label: 'Google Maps Kit', icon: MapPin, implemented: true },
  { id: 'upwork', label: 'Upwork', icon: Cloud, implemented: true },
  { id: 'freelancer', label: 'Freelancer', icon: Camera, implemented: true },
  { id: 'guru', label: 'Guru', icon: Globe, implemented: true },
  { id: 'peopleperhour', label: 'PeoplePerHour', icon: Globe, implemented: true },
  { id: 'linkedin', label: 'LinkedIn', icon: Linkedin, implemented: false },
  { id: 'instagram', label: 'Instagram', icon: Instagram, implemented: false },
]

export default function ProviderMultiSelect({ value = [], onChange, disabled = false }) {
  const toggle = (id) => {
    if (disabled) return
    if (value.includes(id)) onChange(value.filter((v) => v !== id))
    else onChange([...value, id])
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
      {PROVIDERS.map((p) => {
        const selected = value.includes(p.id)
        const unavailable = !p.implemented
        const Icon = p.icon
        return (
          <button
            key={p.id}
            type="button"
            onClick={() => !unavailable && toggle(p.id)}
            disabled={unavailable || disabled}
            title={unavailable ? 'Not available on the backend yet' : p.label}
            className={`flex items-center gap-2 px-3 py-2.5 rounded-xl border text-xs font-medium transition-all ${
              unavailable
                ? 'border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 text-slate-300 dark:text-slate-600 cursor-not-allowed'
                : selected
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-500/10 text-primary-700 dark:text-primary-300 ring-1 ring-primary-500/30 shadow-sm'
                  : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:border-primary-300 dark:hover:border-primary-500/50 hover:bg-primary-50/50 dark:hover:bg-primary-500/5'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <Icon className="w-4 h-4 shrink-0" />
            <span className="truncate">{p.label}</span>
          </button>
        )
      })}
    </div>
  )
}

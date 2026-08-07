import { Globe, MapPin, Linkedin, Star, Briefcase, BookOpen, Search, Server, BriefcaseBusiness, Users } from 'lucide-react'
import { normalizeSourceName } from '../../../services/adapters'

const SOURCE_META = {
  // Google providers
  'Google Maps': { icon: MapPin, classes: 'bg-indigo-50 text-indigo-700 ring-indigo-600/20 dark:bg-indigo-500/10 dark:text-indigo-400 dark:ring-indigo-500/20' },
  'Google Maps Kit': { icon: MapPin, classes: 'bg-indigo-50 text-indigo-700 ring-indigo-600/20 dark:bg-indigo-500/10 dark:text-indigo-400 dark:ring-indigo-500/20' },
  'Google Search': { icon: Search, classes: 'bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-500/10 dark:text-blue-400 dark:ring-blue-500/20' },
  'Free Web Discovery': { icon: Globe, classes: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/20' },
  'Website Discovery': { icon: Globe, classes: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/20' },

  // Freelance platforms
  Upwork: { icon: BriefcaseBusiness, classes: 'bg-green-50 text-green-700 ring-green-600/20 dark:bg-green-500/10 dark:text-green-400 dark:ring-green-500/20' },
  Freelancer: { icon: BriefcaseBusiness, classes: 'bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-500/10 dark:text-blue-400 dark:ring-blue-500/20' },
  Guru: { icon: BriefcaseBusiness, classes: 'bg-purple-50 text-purple-700 ring-purple-600/20 dark:bg-purple-500/10 dark:text-purple-400 dark:ring-purple-500/20' },
  PeoplePerHour: { icon: BriefcaseBusiness, classes: 'bg-orange-50 text-orange-700 ring-orange-600/20 dark:bg-orange-500/10 dark:text-orange-400 dark:ring-orange-500/20' },

  // Data providers
  Apollo: { icon: Users, classes: 'bg-pink-50 text-pink-700 ring-pink-600/20 dark:bg-pink-500/10 dark:text-pink-400 dark:ring-pink-500/20' },
  Apify: { icon: Server, classes: 'bg-cyan-50 text-cyan-700 ring-cyan-600/20 dark:bg-cyan-500/10 dark:text-cyan-400 dark:ring-cyan-500/20' },
  Lusha: { icon: Users, classes: 'bg-violet-50 text-violet-700 ring-violet-600/20 dark:bg-violet-500/10 dark:text-violet-400 dark:ring-violet-500/20' },
  ZoomInfo: { icon: Users, classes: 'bg-indigo-50 text-indigo-700 ring-indigo-600/20 dark:bg-indigo-500/10 dark:text-indigo-400 dark:ring-indigo-500/20' },

  // Other
  LinkedIn: { icon: Linkedin, classes: 'bg-sky-50 text-sky-700 ring-sky-600/20 dark:bg-sky-500/10 dark:text-sky-400 dark:ring-sky-500/20' },
  Yelp: { icon: Star, classes: 'bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-500/10 dark:text-rose-400 dark:ring-rose-500/20' },
  Clutch: { icon: Briefcase, classes: 'bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/20' },
  'Yellow Pages': { icon: BookOpen, classes: 'bg-violet-50 text-violet-700 ring-violet-600/20 dark:bg-violet-500/10 dark:text-violet-400 dark:ring-violet-500/20' },
}

/**
 * SourceBadge — always renders a friendly, provider-specific badge.
 * Any raw source value (provider key, imported:// URL, lower-case name) is
 * normalized first so raw IDs never leak into the UI.
 */
export default function SourceBadge({ source, size = 'md' }) {
  const label = normalizeSourceName(source)
  const meta = SOURCE_META[label] || { icon: Globe, classes: 'bg-slate-100 text-slate-600 ring-slate-500/20 dark:bg-slate-500/10 dark:text-slate-400 dark:ring-slate-400/20' }
  const Icon = meta.icon

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium ring-1 ring-inset transition-shadow hover:shadow-sm ${size === 'sm' ? 'text-[10px]' : 'text-[11px]'} ${meta.classes}`}
    >
      <Icon className="w-3 h-3" />
      {label}
    </span>
  )
}

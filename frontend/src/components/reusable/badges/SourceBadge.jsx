import { Globe, MapPin, Linkedin, Star, Briefcase, BookOpen } from 'lucide-react'

const SOURCE_META = {
  'Google Maps': { icon: MapPin, classes: 'bg-indigo-50 text-indigo-700 ring-indigo-600/20 dark:bg-indigo-500/10 dark:text-indigo-400 dark:ring-indigo-500/20' },
  'Free Web Discovery': { icon: Globe, classes: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/20' },
  LinkedIn: { icon: Linkedin, classes: 'bg-sky-50 text-sky-700 ring-sky-600/20 dark:bg-sky-500/10 dark:text-sky-400 dark:ring-sky-500/20' },
  Yelp: { icon: Star, classes: 'bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-500/10 dark:text-rose-400 dark:ring-rose-500/20' },
  Clutch: { icon: Briefcase, classes: 'bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/20' },
  'Yellow Pages': { icon: BookOpen, classes: 'bg-violet-50 text-violet-700 ring-violet-600/20 dark:bg-violet-500/10 dark:text-violet-400 dark:ring-violet-500/20' },
}

export default function SourceBadge({ source }) {
  const meta = SOURCE_META[source] || { icon: Globe, classes: 'bg-slate-100 text-slate-600 ring-slate-500/20 dark:bg-slate-500/10 dark:text-slate-400 dark:ring-slate-400/20' }
  const Icon = meta.icon

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${meta.classes}`}
    >
      <Icon className="w-3 h-3" />
      {source}
    </span>
  )
}

import StatCard from '../layout/StatCard'
import { Eye, Mail, Search, Globe } from 'lucide-react'

const summaryIcons = {
  total: Eye,
  enriched: Search,
  email: Mail,
  website: Globe,
}

export default function LeadSummaryCard({ title, value, type }) {
  const Icon = summaryIcons[type] || Eye
  return (
    <StatCard
      title={title}
      value={value}
      icon={Icon}
      trend={null}
      trendValue={0}
      color="primary"
    />
  )
}

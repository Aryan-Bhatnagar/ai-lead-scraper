import StatCard from '../layout/StatCard'

export default function EmailSummaryCard({ title, value, icon, color = 'primary' }) {
  return (
    <StatCard
      title={title}
      value={value}
      icon={icon}
      trend={null}
      trendValue={0}
      color={color}
    />
  )
}

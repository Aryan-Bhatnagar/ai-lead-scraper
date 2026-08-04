import { useState } from 'react'
import { Check, Loader2, TrendingUp, Edit, MessageSquare, Calendar, DollarSign, MapPin, Users, ExternalLink } from 'lucide-react'
import { Table } from '../../ui/table'
import { Tooltip } from '../../ui/tooltip'
import { formatDistanceToNow, format } from 'date-fns'

export default function OpportunityTable({
  opportunities,
  loading,
  onView,
  page,
  totalPages,
  totalItems,
  onPageChange,
  sortBy,
  sortDesc,
  onSort,
  onExport,
}) {
  const [selectedOpportunity, setSelectedOpportunity] = useState(null)

  const handleView = (opportunity) => {
    setSelectedOpportunity(opportunity)
    onView(opportunity)
  }

  const columns = [
    {
      accessorKey: 'project_title',
      header: 'Project',
      cell: ({ row }) => {
        const opportunity = row.original
        return (
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0 h-8 w-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
              <Users className="h-4 w-4" />
            </div>
            <div>
              <h3 className="font-medium text-slate-800 dark:text-slate-100">{opportunity.project_title}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">{opportunity.provider}</p>
            </div>
          </div>
        )
      },
    },
    {
      accessorKey: 'provider',
      header: 'Provider',
      cell: ({ row }) => {
        const opportunity = row.original
        const providerIcons = {
          upwork: <Users className="h-4 w-4" />,
          freelancer: <Users className="h-4 w-4" />,
          guru: <Users className="h-4 w-4" />,
          peopleperhour: <Users className="h-4 w-4" />,
        }
        const Icon = providerIcons[opportunity.provider.toLowerCase()] || <Users className="h-4 w-4" />
        return (
          <div className="flex items-center space-x-2">
            <Icon className="h-4 w-4 text-primary" />
            <span className="text-slate-700 dark:text-slate-200 capitalize">{opportunity.provider}</span>
          </div>
        )
      },
    },
    {
      accessorKey: 'budget_max',
      header: 'Budget',
      cell: ({ row }) => {
        const opportunity = row.original
        if (opportunity.budget_min !== null || opportunity.budget_max !== null) {
          return (
            <>
              ${opportunity.budget_min?.toLocaleString() ?? '0'} -
              ${opportunity.budget_max?.toLocaleString() ?? '0'}
              {opportunity.currency}
            </>
          )
        }
        return <span className="text-slate-500">Not specified</span>
      },
    },
    {
      accessorKey: 'client_country',
      header: 'Country',
      cell: ({ row }) => {
        const opportunity = row.original
        return <span className="text-slate-700 dark:text-slate-200">{opportunity.client_country}</span>
      },
    },
    {
      accessorKey: 'category',
      header: 'Category',
      cell: ({ row }) => {
        const opportunity = row.original
        return <span className="text-slate-700 dark:text-slate-200 capitalize">{opportunity.category}</span>
      },
    },
    {
      accessorKey: 'skills',
      header: 'Skills',
      cell: ({ row }) => {
        const opportunity = row.original
        return (
          <div className="flex flex-wrap gap-1">
            {opportunity.skills.slice(0, 3).map((skill, index) => (
              <span
                key={index}
                className="px-2 py-0.5 rounded bg-secondary/10 text-secondary text-xs font-medium"
              >
                {skill}
              </span>
            ))}
            {opportunity.skills.length > 3 && (
              <span className="px-2 py-0.5 rounded bg-secondary/10 text-secondary text-xs font-medium">
                +{opportunity.skills.length - 3} more
              </span>
            )}
          </div>
        )
      },
    },
    {
      accessorKey: 'posted_time',
      header: 'Posted',
      cell: ({ row }) => {
        const opportunity = row.original
        const date = new Date(opportunity.posted_time)
        return (
          <Tooltip content={format(date, "PPP p")}>
            <span className="text-slate-500">{formatDistanceToNow(date, { addSuffix: true })}</span>
          </Tooltip>
        )
      },
    },
    {
      accessorKey: 'priority',
      header: 'Priority',
      cell: ({ row }) => {
        const opportunity = row.original
        // In a real app, we would have a priority field or compute it
        // For now, we'll use a placeholder based on budget and proposal count
        let priority = 1
        if (opportunity.budget_max !== null && opportunity.budget_max >= 5000) priority += 2
        else if (opportunity.budget_max !== null && opportunity.budget_max >= 1000) priority += 1
        if (opportunity.proposal_count < 5) priority += 1
        else if (opportunity.proposal_count < 15) priority += 0.5
        priority = Math.min(5, Math.max(1, Math.round(priority)))

        return (
          <div className="flex items-center space-x-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <span
                key={i}
                className={`h-2 w-2 rounded-full ${
                  i <= priority ? 'bg-primary-500' : 'bg-slate-200 dark:bg-slate-600'
                }`}
              />
            ))}
            <span className="text-xs text-slate-600 dark:text-slate-300 ml-1">{priority}/5</span>
          </div>
        )
      },
    },
    {
      accessorKey: 'url',
      header: 'Action',
      cell: ({ row }) => {
        const opportunity = row.original
        return (
          <div className="flex items-center space-x-3">
            <button
              onClick={() => {
                // We need to pass this up through props somehow
                // For now, let's just log
                console.log('View opportunity:', opportunity.id)
              }}
              className="p-1.5 text-slate-500 hover:text-primary-600 hover:bg-primary-50 rounded-md transition-colors"
              title="View Details"
            >
              <Edit className="h-4 w-4" />
            </button>
            <a
              href={opportunity.url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 text-slate-500 hover:text-primary-600 hover:bg-primary-50 rounded-md transition-colors"
              title="Open in new tab"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
        )
      },
    },
  ]

  return (
    <Table
      columns={columns}
      data={opportunities}
      loading={loading}
      emptyLabel="No opportunities found"
      showPagination
      currentPage={page}
      totalPages={totalPages}
      totalItems={totalItems}
      onPageChange={onPageChange}
      sortBy={sortBy}
      sortDesc={sortDesc}
      onSort={onSort}
      showExport
      onExport={onExport}
    />
  )
}
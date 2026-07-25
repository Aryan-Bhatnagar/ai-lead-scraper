import { Settings as SettingsIcon } from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'

export default function Settings() {
  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Configure your application preferences."
      />

      <div className="bg-white rounded-xl border border-slate-200 p-8">
        <EmptyState
          icon={SettingsIcon}
          title="Application Settings"
          description="Configure API endpoints, theme preferences, notification settings, and account details."
        >
          <p className="text-xs text-slate-400">
            Settings implementation coming in a future phase
          </p>
        </EmptyState>
      </div>
    </div>
  )
}

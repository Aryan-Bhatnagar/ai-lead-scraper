import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import DashboardLayout from './layouts/DashboardLayout'
import Dashboard from './pages/Dashboard/Dashboard'
import Discover from './pages/Discover/Discover'
import Enrichment from './pages/Enrichment/Enrichment'
import EmailExtraction from './pages/EmailExtraction/EmailExtraction'
import Leads from './pages/Leads/Leads'
import Outreach from './pages/Outreach/Outreach'
import Analytics from './pages/Analytics/Analytics'
import Settings from './pages/Settings/Settings'
import Opportunities from './pages/Opportunities'

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        gutter={10}
        toastOptions={{
          duration: 4000,
          style: {
            borderRadius: '12px',
            background: '#0f172a',
            color: '#f8fafc',
            fontSize: '13px',
            padding: '10px 14px',
            boxShadow: '0 10px 30px rgba(2,6,23,0.35)',
            border: '1px solid rgba(148,163,184,0.15)',
            maxWidth: 'min(420px, calc(100vw - 24px))',
          },
          success: {
            iconTheme: { primary: '#22c55e', secondary: '#0f172a' },
          },
          error: {
            duration: 5000,
            iconTheme: { primary: '#f43f5e', secondary: '#0f172a' },
          },
          loading: {
            iconTheme: { primary: '#6366f1', secondary: '#0f172a' },
          },
        }}
      />
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/discover" element={<Discover />} />
          <Route path="/enrichment" element={<Enrichment />} />
          <Route path="/email-extraction" element={<EmailExtraction />} />
          <Route path="/leads" element={<Leads />} />
          <Route path="/outreach" element={<Outreach />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/opportunities" element={<Opportunities />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

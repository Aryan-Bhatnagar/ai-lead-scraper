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
import Opportunities from './pages/Opportunities/Opportunities'

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            borderRadius: '10px',
            background: '#1e293b',
            color: '#f8fafc',
            fontSize: '14px',
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
          <Route path="/opportunities" element={<Opportunities />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

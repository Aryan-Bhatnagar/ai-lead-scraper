import React from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Overview from './pages/Overview';
import NewScrapeJob from './pages/NewScrapeJob';
import ScrapeJobs from './pages/ScrapeJobs';
import Leads from './pages/Leads';

const Nav = () => {
  const activeStyle = { textDecoration: 'underline', fontWeight: 'bold' };
  return (
    <nav style={{ borderBottom: '1px solid #ddd', padding: '0.5rem 1rem' }}>
      <NavLink to="/" end style={({ isActive }) => (isActive ? activeStyle : undefined)}>
        Overview
      </NavLink>{' '}
      <NavLink to="/new" style={({ isActive }) => (isActive ? activeStyle : undefined)}>
        New Scrape Job
      </NavLink>{' '}
      <NavLink to="/jobs" style={({ isActive }) => (isActive ? activeStyle : undefined)}>
        Scrape Jobs
      </NavLink>{' '}
      <NavLink to="/leads" style={({ isActive }) => (isActive ? activeStyle : undefined)}>
        Leads
      </NavLink>
    </nav>
  );
};

export default function App() {
  return (
    <BrowserRouter>
      <Header />
      <Nav />
      <main style={{ padding: '1rem' }}>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/new" element={<NewScrapeJob />} />
          <Route path="/jobs" element={<ScrapeJobs />} />
          <Route path="/leads" element={<Leads />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

function Header() {
  return (
    <header style={{ background: '#282c34', color: '#fff', padding: '1rem' }}>
      <h1>AI Lead Scraper Dashboard</h1>
    </header>
  );
}

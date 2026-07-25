# AI Lead Scraper — Frontend Dashboard

Modern React dashboard for managing the AI Lead Scraper pipeline.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 19 |
| Build Tool | Vite 6 |
| Styling | Tailwind CSS 4 |
| Routing | React Router 7 |
| HTTP Client | Axios |
| Charts | Recharts (installed, pending integration) |
| Forms | React Hook Form (installed, pending integration) |
| Tables | TanStack Table (installed, pending integration) |
| Icons | Lucide React |
| Notifications | React Hot Toast |
| Linting | ESLint 9 |

## Installation

```bash
cd frontend
npm install
```

## Running

```bash
npm run dev        # Start dev server on http://localhost:5173
npm run build      # Production build to dist/
npm run preview    # Preview production build
npm run lint       # Run ESLint
```

The dev server proxies `/api` requests to `http://localhost:5000` (the Flask backend).

## Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:5000` | Backend API base URL |

## Folder Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/          # Structural components
│   │   │   ├── Sidebar.jsx        # Collapsible sidebar navigation
│   │   │   ├── Navbar.jsx         # Top bar with search & user
│   │   │   ├── PageHeader.jsx     # Reusable page header
│   │   │   ├── StatCard.jsx       # Metric display card
│   │   │   ├── EmptyState.jsx     # Empty/placeholder state
│   │   │   └── LoadingSpinner.jsx # Loading indicator
│   │   └── reusable/        # Feature-agnostic reusable components
│   ├── pages/               # Route-level page components
│   │   ├── Dashboard/       # Main dashboard with stats & charts
│   │   ├── Discover/        # Lead discovery interface
│   │   ├── Enrichment/      # Lead enrichment pipeline
│   │   ├── EmailExtraction/ # Email extraction pipeline
│   │   ├── Leads/           # Leads database table view
│   │   ├── Outreach/        # Outreach queue management
│   │   ├── Analytics/       # Charts and performance metrics
│   │   └── Settings/        # Application settings
│   ├── services/
│   │   └── api.js           # Axios instance and interceptors
│   ├── hooks/
│   │   └── useApi.js        # Generic API call hook
│   ├── layouts/
│   │   └── DashboardLayout.jsx  # Main layout with sidebar + navbar
│   ├── assets/              # Static assets (images, icons)
│   ├── App.jsx              # Root component with routing
│   ├── main.jsx             # Entry point
│   └── index.css            # Tailwind CSS + custom theme
├── .env.example
├── vite.config.js
├── eslint.config.js
└── package.json
```

## Routes

| Path | Page | Description |
|------|------|-------------|
| `/` | Dashboard | Overview with stat cards and placeholder charts |
| `/discover` | Discover Leads | Lead discovery interface |
| `/enrichment` | Lead Enrichment | Data enrichment pipeline |
| `/email-extraction` | Email Extraction | Email extraction pipeline |
| `/leads` | Leads Database | Leads table with filters |
| `/outreach` | Outreach Queue | Outreach campaign management |
| `/analytics` | Analytics | Performance charts and metrics |
| `/settings` | Settings | Application configuration |

## Architecture Notes

- **No business logic** in this phase — all pages are placeholders
- **No API calls** — API layer is configured but not connected
- **No authentication** — user section is a placeholder
- **Sidebar is collapsible** and highlights the active route
- **Tailwind CSS 4** uses the new CSS-first configuration (`@theme` in index.css)
- **Vite proxy** forwards `/api` to the Flask backend during development

## Phase Roadmap

| Phase | Description |
|-------|-------------|
| **13A** | Frontend foundation (this phase) |
| **13B** | API integration — connect all pages to backend endpoints |
| **13C** | Charts and analytics — Recharts integration |
| **13D** | Forms — React Hook Form for discovery, enrichment |
| **13E** | Tables — TanStack Table for leads database |
| **13F** | Authentication and user management |

# AI Lead Scraper CRM

> **BilvaLeaf Business Development Platform** — A local-first, AI-powered lead discovery, enrichment, scoring, and CRM platform. Built with Flask, React, SQLite, and local LLMs via Ollama. No paid APIs required.

---

## What This Project Is

The AI Lead Scraper CRM is a complete lead management platform that:

1. **Discovers leads** from multiple sources: Google Maps (via Gosom scraper), Google Search, Upwork, and imported datasets (Apollo, Google Places, Upwork exports)
2. **Enriches leads** by scraping company websites and using local LLMs (Ollama) to generate business intelligence
3. **Scores leads** with a transparent, configurable algorithm producing opportunity scores (0-100) and quality tiers (Excellent/Good/Average)
4. **Provides a CRM** with dashboard, lead repository, analytics, and opportunity management
5. **Exposes a REST API** for integration with external tools (e.g., n8n for outreach automation)

**Key philosophy**: Local-first, privacy-respecting, no mandatory external API keys. Everything runs on your machine.

---

## Features

### Lead Discovery
- **Google Maps** — Real business listings via Gosom Google Maps Scraper (Docker)
- **Google Search** — Free web search via DuckDuckGo backend
- **Upwork** — Job postings as business opportunities
- **Dataset Imports** — Apollo, Google Places, Upwork JSON exports

### Lead Enrichment
- Website scraping with BeautifulSoup + ScrapeGraphAI
- AI business intelligence via Ollama (llama3.2 default)
- Contact extraction (emails, phones, socials)
- Technology stack detection

### AI Scoring
- **15 weighted features** (website, email, phone, description, location, social, size, recency, provider confidence, AI enrichment, Google rating, review count, company size, AI enrichment quality)
- **Three-tier quality model**: Excellent (≥70), Good (≥50), Average (≥30)
- **Opportunity score thresholds**: High (≥64), Medium (≥50), Low (≥35)
- Full score breakdown with explanations
- Configurable via `config/lead_scoring.yaml`

### CRM Interface
- **Dashboard** — KPIs, discovery timeline, source distribution, provider performance, score distribution, quality breakdown, lifecycle
- **Lead Repository** — Search, filter (city, country, source, quality), pagination, sorting, lead details drawer
- **Lead Details** — Company, contact, website, phone, email, location, source, AI score, quality, AI summary, pain points, buying signals, recommended service, decision maker, outreach strategy
- **Analytics** — Provider analytics, quality analytics, trends, lifecycle, insights
- **Opportunities** — Upwork/freelance job opportunities tracking

### API
- Full REST API for leads, analytics, discovery, enrichment, intelligence, outreach queue, opportunities
- CORS enabled for frontend integration

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   Frontend      │────▶│   Flask API     │────▶│  Discovery/Lead  │
│   (React/Vite)  │     │   (Port 5000)   │     │   Services       │
└─────────────────┘     └─────────────────┘     └────────┬─────────┘
                                                         │
                    ┌────────────────────────────────────┼────────────────────────────────────┐
                    ▼                                    ▼                                    ▼
            ┌───────────────┐                  ┌─────────────────┐              ┌─────────────────┐
            │ Google Maps   │                  │ Google Search   │              │ Upwork          │
            │ (Gosom/8080)  │                  │ (DDGS)          │              │ (Scraper)       │
            └───────────────┘                  └─────────────────┘              └─────────────────┘
                                                         │
                    ┌────────────────────────────────────┼────────────────────────────────────┐
                    ▼                                    ▼                                    ▼
            ┌───────────────┐                  ┌─────────────────┐              ┌─────────────────┐
            │ Normalization │                  │ Deduplication   │              │ AI Enrichment   │
            │ (Providers→   │                  │ (Email/Domain/  │              │ (Ollama +       │
            │  UnifiedLead) │                  │  Source URL)    │              │  Website Scrape)│
            └───────────────┘                  └─────────────────┘              └─────────────────┘
                                                         │
                                                         ▼
                                              ┌─────────────────┐
                                              │ AI Scoring      │
                                              │ (15 features,   │
                                              │  YAML config)   │
                                              └────────┬────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │ SQLite Database │
                                              │ (data/leads.db) │
                                              └─────────────────┘
```

### AI Enrichment Path
```
Lead (with website)
    ▼
WebsiteEnrichmentProvider (BeautifulSoup + ScrapeGraphAI)
    ▼
Business Profile (structured JSON)
    ▼
IntelligenceManager (OllamaProvider → llama3.2)
    ▼
AI Insights (summary, services, pain points, opportunities, tech stack, ICP)
    ▼
AIEnrichmentPipeline
    ▼
ScoreCalculator (extended features: google_rating, review_count, company_size, ai_enrichment_quality)
    ▼
Persistence (leads + ai_insights + business_profiles tables)
```

---

## Requirements

### System Requirements
| Component | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 20+ | Frontend build/dev |
| **Docker** | 24+ | Gosom Google Maps Scraper |
| **Ollama** | 0.5+ | Local LLM inference |
| **Git** | 2.40+ | Version control |

### Python Dependencies
See `requirements.txt` — key packages:
- `flask`, `flask-cors` — API framework
- `scrapegraphai`, `langchain-ollama` — AI enrichment
- `playwright`, `beautifulsoup4` — Web scraping
- `ddgs` — Google Search (free backend)
- `pydantic`, `pydantic-settings` — Validation
- `PyYAML` — Scoring config
- `requests`, `httpx` — HTTP clients

### Node Dependencies
See `frontend/package.json` — key packages:
- `react`, `react-dom`, `react-router-dom` — UI framework
- `axios` — API client
- `recharts` — Analytics charts
- `@tanstack/react-table` — Lead tables
- `lucide-react` — Icons
- `tailwindcss` — Styling
- `vite` — Build tool

### External Services (Must Be Running)
| Service | Port | Start Command | Health Check |
|---------|------|---------------|--------------|
| **Ollama** | 11434 | `ollama serve` | `curl http://localhost:11434/api/tags` |
| **Gosom Scraper** | 8080 | `docker run -d -p 8080:8080 gosom/google-maps-scraper` | `curl http://localhost:8080/api/v1/health` |

---

## Quick Start

### 1. Clone
```powershell
git clone <repository-url>
cd ai-lead-scraper
```

### 2. Python Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

### 3. Frontend Dependencies
```powershell
cd frontend
npm install
cd ..
```

### 4. Environment Variables
```powershell
copy .env.example .env
# Edit .env with your settings (see Environment Variables section)
```

### 5. Database
The database is auto-initialized on first backend start:
```powershell
.\venv\Scripts\python.exe -c "from scraper.database import initialize_database; initialize_database()"
```

### 6. Gosom Google Maps Scraper (Docker)
```powershell
# Pull image (one-time)
docker pull gosom/google-maps-scraper

# Start container
docker run -d --name gosom-scraper -p 8080:8080 gosom/google-maps-scraper

# Verify
curl http://localhost:8080/api/v1/health
```

**Expected response**: `{"status":"ok"}` or similar.

To stop: `docker stop gosom-scraper`
To restart: `docker restart gosom-scraper`

### 7. Ollama
```powershell
# Install Ollama from https://ollama.com/download (Windows installer)

# Start service (runs in background)
ollama serve

# Pull model (one-time)
ollama pull llama3.2

# Verify
curl http://localhost:11434/api/tags
```

**Expected response**: JSON list containing `llama3.2`.

### 8. Backend
```powershell
.\venv\Scripts\python.exe api\app.py
```
Backend runs on **http://localhost:5000**

### 9. Frontend
```powershell
cd frontend
npm run dev
```
Frontend runs on **http://localhost:5173** (Vite default)

---

## How to Use the CRM

### Dashboard
Visit http://localhost:5173 — shows overview KPIs, charts, and recent activity.

### Lead Repository
- **Search** — Free-text search across company, contact, website, email
- **Filters** — City, Country, Source (Google Maps/Upwork/Apollo/Google Search), Quality (Excellent/Good/Average)
- **Sort** — Click column headers (Company, Contact, Email, Phone, City, Source, Score, Quality, Status)
- **Pagination** — 50 leads per page (configurable)
- **Lead Details** — Click a row to open the drawer with full details

### Lead Details Drawer
Tabs:
- **Overview** — Company, contact, website, phone, email, location, source, AI score, quality tier
- **Intelligence** — AI summary, pain points, buying signals, recommended service, decision maker, outreach strategy
- **Scoring** — Score breakdown with feature contributions
- **Enrichment** — Business profile, AI insights, raw provider data

### Discovery
Navigate to **Discover** page:
1. Select provider(s): Google Maps, Google Search, Upwork
2. Enter industry (e.g., "software development")
3. Enter location (e.g., "San Francisco, CA")
4. Set max results (1-50)
5. Click **Discover** — runs discovery pipeline, scores leads, saves to database

### Importing Leads
```powershell
# Apollo dataset
.\venv\Scripts\python.exe import_all_datasets.py

# Or specific import scripts
.\venv\Scripts\python.exe import_upwork_datasets.py
.\venv\Scripts\python.exe import_and_enrich.py
```

**Expected JSON structure** for each source — see [Lead Import](#lead-import) below.

### Analytics
Navigate to **Analytics** page for:
- Provider performance comparison
- Quality tier distribution
- Discovery trends over time
- Lead lifecycle funnel
- AI-generated insights

### Opportunities
Navigate to **Opportunities** for Upwork/freelance job tracking.

---

## Lead Discovery

### Google Maps (Gosom)
- Requires Docker container on port 8080
- Submits search job → polls for completion → downloads CSV → enriches websites
- Filters: blacklisted domains (social media, directories), junk keywords, geo-fencing
- Returns real businesses with ratings, reviews, categories, contact info

### Google Search (Free)
- Uses DDGS (DuckDuckGo) backend — no API key
- Queries: `{industry} company {location}` + keywords
- Returns snippets with title, URL, snippet
- Requires website enrichment for contact data

### Upwork
- Scrapes Upwork job postings
- Maps to Opportunity model (separate from leads)
- Also imports as leads with client info

---

## Lead Import

### Supported Sources
| Source | Adapter | Source Label | Key Fields |
|--------|---------|--------------|------------|
| **Apollo** | `ApolloImportAdapter` | `Apollo` | firstName, lastName, title, email, phone, linkedinUrl, companyName, companyDomain, companyIndustry, companyDescription, companySize, city, country, state |
| **Google Maps** | `GoogleMapsImportAdapter` | `Google Maps` | name, place_id, website, formatted_address, rating, user_ratings_total, types, geometry, address_components |
| **Upwork (Leads)** | `UpworkImportAdapter` | `Upwork` | uid, title, description, budget, skills, publishedAt, category, client (name, countryCode, city, rating, reviews, jobsPosted, hireRate), externalLink |
| **Upwork (Opportunities)** | `UpworkOpportunityImportAdapter` | `Upwork` | Maps to Opportunity table directly |

### Import Process
1. **Parse** — JSON file → records array
2. **Map** — Each record → `UnifiedLead` (or `Opportunity`)
3. **Deduplicate** — Cross-file by email, domain, source_url, place_id, uid
4. **Persist** — Upsert into SQLite (`leads` table or `opportunities.json`)
5. **Enrich (optional)** — Trigger AI enrichment pipeline

### Run Imports
```powershell
# All datasets
.\venv\Scripts\python.exe import_all_datasets.py

# Apollo only
.\venv\Scripts\python.exe test_apollo_import.py

# Upwork only
.\venv\Scripts\python.exe import_upwork_datasets.py

# Import + Enrich
.\venv\Scripts\python.exe import_and_enrich.py
```

---

## AI Enrichment

### Pipeline
```
Lead (with website)
    │
    ▼
WebsiteEnrichmentProvider.fetch_data()
    │  ├─▶ requests.get(website) → HTML
    │  ├─▶ WebsiteParser.parse() → structural data (meta, socials, tech, key pages)
    │  └─▶ SmartScraperGraph (Ollama) → semantic data (summary, services, audience, model, tech, pain points)
    ▼
Business Profile (merged structural + semantic)
    │
    ▼
IntelligenceManager.get_or_generate_intelligence()
    │  ├─▶ Check cache (ai_insights table) — validates completeness
    │  └─▶ OllamaProvider.generate_intelligence() → AI Insights
    ▼
AIEnrichmentPipeline.enrich_lead()
    │  ├─▶ Derive: recommended_service, decision_maker, company_size, outreach_strategy
    │  ├─▶ Calculate: ai_confidence, opportunity_score (extended features)
    │  └─▶ Persist: leads table + ai_insights + business_profiles
    ▼
Complete
```

### Ollama Configuration
- **Model**: `llama3.2` (default, set via `SCRAPEGRAPH_MODEL=ollama/llama3.2`)
- **Base URL**: `http://localhost:11434` (set via `OLLAMA_BASE_URL`)
- **Temperature**: 0 (deterministic)
- **Format**: JSON

### Fallback Behavior
- If Ollama unavailable: enrichment fails gracefully, lead saved with `status="failed"` for enrichment
- AI insights cache validates completeness — invalid cache entries are regenerated
- No external API fallback (by design — local-first)

---

## AI Scoring

### Feature Weights (config/lead_scoring.yaml)
| Feature | Weight | Description |
|---------|--------|-------------|
| website_exists | 15 | Lead has a website URL |
| business_email | 12 | Business email (non-generic domain) |
| phone_number | 8 | At least one phone number |
| description_quality | 6 | Description length/richness |
| location_quality | 5 | Location completeness |
| multiple_sources | 6 | Discovered by 2+ providers |
| social_profiles | 3 | Social media links |
| company_size_hints | 4 | Reviews, categories, jobs |
| recent_activity | 3 | Discovered within 30 days |
| provider_confidence | 2 | Discovery provider confidence |
| ai_enrichment_confidence | 4 | AI enrichment succeeded |
| **google_rating** | **8** | Google Maps rating (0-5) |
| **review_count** | **6** | Maps review count (capped 100) |
| **company_size** | **8** | Estimated size from signals |
| **ai_enrichment_quality** | **10** | AI enrichment completeness |
| **Total** | **100** | |

### Quality Tiers (Three-Tier Model)
| Tier | Score Range | Label |
|------|-------------|-------|
| **Excellent** | ≥ 70 | `excellent` |
| **Good** | 50–69 | `good` |
| **Average** | 30–49 | `average` |
| Below 30 | 0–29 | `average` (lowest tier) |

### Opportunity Score Thresholds
| Tier | Score Range |
|------|-------------|
| **High** | ≥ 64 |
| **Medium** | 50–63 |
| **Low** | 35–49 |

### Score Breakdown
Each scored lead includes:
- `overall_score` (0-100)
- `quality_tier` (excellent/good/average)
- `explanation.breakdowns[]` — per-feature: feature, label, weight, quality_ratio, contribution, detail
- Rendered as: `+25 Website`, `+12 Business Email`, `+8 Phone`, etc.

---

## Analytics

### Endpoints
- `/api/analytics/overview` — KPIs, totals, distributions
- `/api/analytics/trends` — Discovery timeline (daily/weekly/monthly)
- `/api/analytics/providers` — Per-provider: count, avg score, quality distribution
- `/api/analytics/quality` — Quality tier breakdown
- `/api/analytics/lifecycle` — CRM lifecycle funnel (NEW→QUALIFIED→CONTACTED→INTERESTED→CONVERTED/REJECTED)
- `/api/analytics/insights` — AI-generated insights (top opportunities, common pain points, recommended services)

### Frontend
Analytics page renders interactive charts (Recharts) with:
- Bar charts for provider performance
- Pie/donut for quality/source distribution
- Line charts for trends
- Funnel for lifecycle
- Insight cards

---

## API Documentation

See **docs/API.md** for complete endpoint reference.

### Key Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check |
| GET | `/api/leads` | List leads (filter, sort, paginate) |
| GET | `/api/leads/:id` | Get lead details |
| POST | `/api/leads` | Create lead |
| PUT | `/api/leads/:id` | Update lead |
| PATCH | `/api/leads/:id/status` | Update CRM lead_status |
| PATCH | `/api/leads/:id/lifecycle` | Update lifecycle (validated transitions) |
| DELETE | `/api/leads/:id` | Delete lead |
| GET | `/api/leads/search` | Advanced search |
| GET | `/api/leads/statistics` | Lead stats |
| GET | `/api/leads/cities` | Unique cities for filter |
| POST | `/api/discover` | Run discovery (orchestrator) |
| POST | `/api/discover/google-maps` | Google Maps discovery |
| POST | `/api/discover/free` | Free web discovery |
| POST | `/api/enrich/:lead_id` | Enrich single lead |
| POST | `/api/intelligence/generate/:lead_id` | Generate AI intelligence |
| GET | `/api/analytics/overview` | Analytics overview |
| GET | `/api/analytics/trends` | Trends |
| GET | `/api/analytics/providers` | Provider analytics |
| GET | `/api/analytics/quality` | Quality analytics |
| GET | `/api/analytics/lifecycle` | Lifecycle analytics |
| GET | `/api/analytics/insights` | AI insights |
| POST | `/api/outreach` | Create outreach queue entry |
| POST | `/api/outreach/process` | Process outreach batch (webhook) |
| GET/POST | `/api/opportunities` | Opportunities CRUD |

---

## Testing

```powershell
# Backend tests
.\venv\Scripts\python.exe -m pytest api/test_*.py -v

# Specific test suites
.\venv\Scripts\python.exe -m pytest api/test_analytics.py -v
.\venv\Scripts\python.exe -m pytest api/test_recommendations.py -v
.\venv\Scripts\python.exe -m pytest scraper/test_*.py -v

# Frontend
cd frontend
npm run build  # Type-check + build
```

---

## Troubleshooting

See **docs/TROUBLESHOOTING.md** for detailed guide.

### Common Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| `Flask port 5000 in use` | Another process | `taskkill /PID <pid> /F` or change port in `.env` |
| `Frontend port 5173 in use` | Another Vite instance | `taskkill /PID <pid> /F` |
| `Gosom port 8080 unavailable` | Docker not running / port conflict | `docker stop gosom-scraper && docker start gosom-scraper` |
| `Docker container not running` | Container stopped/crashed | `docker logs gosom-scraper` → fix → `docker restart gosom-scraper` |
| `Ollama unavailable` | Service not started | `ollama serve` in separate terminal |
| `Chrome/Selenium issues` | Playwright browser missing | `playwright install chromium` |
| `CORS errors` | Frontend URL not allowed | Check `CORS(app)` in `api/app.py` |
| `Stale frontend data` | Browser cache | Hard refresh (Ctrl+Shift+R) |
| `Database missing` | Not initialized | Run `initialize_database()` |
| `Missing env vars` | `.env` not configured | Copy `.env.example` → `.env` and fill values |
| `npm install fails` | Node version / cache | `npm cache clean --force && npm install` |
| `Python import errors` | Venv not activated / deps missing | `.\venv\Scripts\Activate.ps1 && pip install -r requirements.txt` |

---

## Project Structure

```
ai-lead-scraper/
├── api/                          # Flask backend
│   ├── app.py                    # Application factory, all routes
│   ├── routes/                   # Route modules
│   │   ├── dashboard.py          # Dashboard KPI endpoints
│   │   └── opportunities.py      # Opportunities CRUD
│   ├── services/                 # Business logic
│   │   ├── lead_service.py       # Lead CRUD + search
│   │   ├── recommendation_service.py  # Next-action recommendations
│   │   ├── ai_intelligence.py    # AI insights (Ollama)
│   │   └── enrichment/           # Website enrichment
│   │       ├── base.py           # Provider interface
│   │       ├── engine.py         # UnifiedEnrichmentEngine
│   │       └── website.py        # WebsiteEnrichmentProvider
│   └── test_*.py                 # Backend tests
│
├── frontend/                     # React + Vite frontend
│   ├── src/
│   │   ├── components/           # Reusable UI components
│   │   │   ├── intelligence/     # AI insight panels
│   │   │   ├── layout/           # Navbar, Sidebar, StatCard
│   │   │   ├── leads/            # LeadTable, LeadDetailsDrawer
│   │   │   ├── repository/       # LeadRepository components
│   │   │   ├── reusable/         # Charts, Filters, Pagination
│   │   │   └── ...
│   │   ├── pages/                # Page components
│   │   │   ├── Dashboard/
│   │   │   ├── Leads/
│   │   │   ├── Analytics/
│   │   │   ├── Discover/
│   │   │   └── Opportunities/
│   │   ├── services/             # API clients
│   │   ├── hooks/                # React hooks
│   │   ├── utils/                # Helpers
│   │   ├── App.jsx               # Root component + routes
│   │   └── main.jsx              # Entry point
│   ├── package.json
│   └── vite.config.js
│
├── scraper/                      # Core scraping & processing logic
│   ├── database.py               # SQLite operations (leads, jobs, outreach, AI insights)
│   ├── ai_enrichment.py          # AIEnrichmentPipeline
│   ├── lead_discovery.py         # Legacy discovery
│   ├── google_maps_discovery.py  # Legacy Google Maps
│   ├── free_lead_discovery.py    # Free web discovery
│   ├── lead_enrichment.py        # Legacy enrichment
│   ├── email_extractor.py        # Email extraction
│   ├── outreach_service.py       # Outreach queue processor
│   │
│   ├── discovery/                # Discovery framework (Phase 15+)
│   │   ├── engine.py             # DiscoveryEngine
│   │   ├── orchestrator.py       # DiscoveryOrchestrator
│   │   ├── model.py              # UnifiedLead, Score, Provenance
│   │   ├── query.py              # DiscoveryQuery, DiscoveryBatch
│   │   ├── provider.py           # DiscoveryProvider base + CapabilitySet
│   │   ├── registry.py           # ProviderRegistry
│   │   ├── providers/            # Provider implementations
│   │   │   ├── google_maps_provider.py
│   │   │   ├── google_search_provider.py
│   │   │   ├── upwork_provider.py
│   │   │   └── website_provider.py
│   │   └── normalizers/          # RawCandidate → UnifiedLead
│   │
│   ├── scoring/                  # Lead scoring engine
│   │   ├── feature_extractor.py  # 0.0-1.0 quality ratios
│   │   ├── score_calculator.py   # Weighted score computation
│   │   ├── weight_provider.py    # YAML config loader
│   │   ├── models.py             # ScoredLead, ScoreExplanation
│   │   └── scoring_engine.py     # Batch scoring
│   │
│   ├── persistence/              # Repository pattern (Phase 19)
│   │   ├── models.py
│   │   ├── repository.py         # LeadRepository
│   │   ├── stores/               # SQLite, Memory backends
│   │   ├── config.py             # PersistenceConfig
│   │   └── lifecycle.py          # LeadStatus + LifecycleEngine
│   │
│   ├── import_package/           # Dataset imports
│   │   ├── base.py               # BaseImportAdapter, ImportResult
│   │   ├── registry.py           # ImportAdapterRegistry
│   │   ├── orchestrator.py       # ImportOrchestrator
│   │   ├── apollo.py             # ApolloImportAdapter
│   │   ├── google_maps.py        # GoogleMapsImportAdapter
│   │   ├── google_places.py      # GooglePlacesImportAdapter
│   │   └── upwork.py             # UpworkImportAdapter (+ Opportunities)
│   │
│   ├── opportunities/            # Opportunity tracking
│   │   ├── opportunity_models.py
│   │   ├── opportunity_repository.py
│   │   ├── opportunity_service.py
│   │   └── providers/            # Upwork, Freelancer, Guru, PeoplePerHour
│   │
│   ├── recommendations/          # Next-action recommendations
│   │   ├── recommendation_engine.py
│   │   ├── priority_rules.py
│   │   └── next_action.py
│   │
│   ├── deduplication/            # Cross-source deduplication
│   │   ├── deduper.py
│   │   ├── config.py
│   │   └── models.py
│   │
│   ├── analytics/                # Analytics engine
│   │   ├── analytics_service.py
│   │   ├── analytics_models.py
│   │   ├── statistics.py
│   │   ├── trend_analysis.py
│   │   └── insights.py
│   │
│   └── services/search/          # Search service (DDGS backend)
│
├── config/
│   └── lead_scoring.yaml         # Scoring weights + thresholds
│
├── data/                         # SQLite databases + exports (gitignored)
│   ├── leads.db                  # Main database
│   ├── leads_repo.db             # Repository database
│   ├── opportunities.json        # Opportunities file store
│   └── *.csv                     # Legacy CSV exports
│
├── scripts/                      # Utility scripts
├── requirements.txt              # Python dependencies
├── package.json                  # Root (Playwright only)
├── .env.example                  # Environment template
├── .gitignore
└── README.md                     # This file
```

---

## Security

### Secrets Management
- **Never commit `.env`** — listed in `.gitignore`
- **Use `.env.example`** as template with placeholders only
- **API keys**: Only `OPENAI_API_KEY` if using OpenAI provider (optional)
- **Webhook URL**: `OUTREACH_WEBHOOK_URL` for n8n integration (optional)

### Environment Variables
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OLLAMA_BASE_URL` | Yes | `http://localhost:11434` | Ollama server URL |
| `SCRAPEGRAPH_MODEL` | Yes | `ollama/llama3.2` | Model for ScrapeGraphAI |
| `AI_INTELLIGENCE_PROVIDER` | No | `ollama` | `ollama` or `openai` |
| `OPENAI_API_KEY` | No* | — | Required if provider=openai |
| `OUTREACH_WEBHOOK_URL` | No | — | n8n webhook for outreach dispatch |
| `OUTREACH_BATCH_LIMIT` | No | `10` | Max entries per batch |
| `OUTREACH_MAX_RETRY` | No | `3` | Max retry attempts |
| `LEAD_REPOSITORY_URI` | No | `sqlite:///data/leads_repo.db` | Repository DB URI |
| `DATABASE` | No | `data/leads.db` | Main database path |

### Data Privacy
- All processing local — no data leaves your machine (except optional OpenAI calls)
- Lead data stored in local SQLite
- No telemetry or tracking

---

## Database Handoff

The repository does **NOT** contain the production lead database.

The current CRM database (`data/leads.db`) contains 1,887 leads with full AI enrichment, scoring, and opportunity data. This database must be obtained separately from the project owner — it is intentionally excluded from GitHub because it contains lead/contact data (PII).

### Obtaining the Database
1. Request the backup files (`leads_backup_*.db` and `opportunities_backup_*.json`) from the project owner via secure file transfer.
2. Place them in the `backups/` directory (create if needed).
3. Restore using the provided script:
   ```powershell
   .\restore_database.ps1 -BackupFile "backups\leads_backup_20260810_161421.db" -Force
   ```
4. Verify the restoration:
   ```bash
   python verify_database_backup.py data/leads.db backups/leads_backup_20260810_161421.db data/opportunities.json backups/opportunities_backup_20260810_161421.json
   ```

### Documentation
See **docs/DATABASE_HANDOFF.md** for complete details including:
- Database schema and all preserved fields
- Backup file locations and SHA-256 checksums
- Step-by-step restore and verification procedures
- Lead statistics and quality distributions
- AI enrichment fields preserved

---

## n8n Integration Handoff

See **docs/N8N_INTEGRATION_HANDOFF.md** for complete details.

### Current State
- **CRM owns**: Lead discovery, storage, enrichment, AI scoring, quality, presentation, filtering, analytics
- **n8n owns**: Outreach automation (Email, WhatsApp), future workflow automation

### Integration Points (Existing API)
| CRM Endpoint | Purpose | n8n Use Case |
|--------------|---------|--------------|
| `GET /api/leads` | List qualified leads | Pull leads for outreach campaigns |
| `GET /api/leads/:id` | Full lead details | Get contact info, AI insights for personalization |
| `PATCH /api/leads/:id/lifecycle` | Update lead status | Mark CONTACTED/INTERESTED after outreach |
| `POST /api/outreach` | Create outreach queue | n8n creates entries when starting campaign |
| `POST /api/outreach/process` | Dispatch via webhook | **Called by CRM** → n8n webhook receives payload |
| `GET /api/outreach` | List outreach entries | Sync status back to CRM |

### Webhook Payload (CRM → n8n)
```json
{
  "queue_id": 123,
  "lead_id": 456,
  "company_name": "Acme Corp",
  "contact_name": "John Doe",
  "contact_role": "CTO",
  "email": "john@acme.com",
  "phone": "+1-555-0123",
  "website": "https://acme.com",
  "outreach_channel": "EMAIL",
  "outreach_status": "PROCESSING"
}
```

### Lead Fields Available to n8n
- `id`, `company_name`, `contact_name`, `contact_role`, `email`, `phone`, `website`
- `city`, `country`, `source`, `ai_score`, `quality_tier`, `opportunity_score`
- `recommended_service`, `pain_points[]`, `buying_signals[]`, `outreach_strategy`
- `decision_maker_guess`, `company_size_estimate`, `ai_summary`, `ai_confidence`

### Future Integration (Not Implemented)
- CRM → n8n: `outreach_status` callbacks (SENT/FAILED/COMPLETED)
- n8n → CRM: `PATCH /api/leads/:id/lifecycle` with `CONTACTED`/`INTERESTED`
- Campaign management in CRM (UI exists, backend partial)

---

## Development Workflow

### Branching
- `main` — Production-ready, protected
- Feature branches: `feat/<name>`, `fix/<name>`
- PRs required for all changes to `main`

### Running Locally
```powershell
# Terminal 1: Backend
.\venv\Scripts\Activate.ps1
.\venv\Scripts\python.exe api\app.py

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Ollama (if not running as service)
ollama serve

# Terminal 4: Gosom (Docker)
docker start gosom-scraper
```

### Code Style
- Python: Black + Ruff (configured in `pyproject.toml` if present)
- JavaScript: ESLint + Prettier (configured in `frontend/`)

### Adding a New Discovery Provider
1. Create `scraper/discovery/providers/<name>_provider.py` extending `DiscoveryProvider`
2. Implement `discover(query: DiscoveryQuery) -> DiscoveryBatch`
3. Register in `scraper/discovery/registry.py`
4. Add normalizer in `scraper/discovery/normalizers/` if needed
5. Test with `test_discovery.py`

### Adding a New Import Adapter
1. Create `scraper/import_package/<source>.py` extending `BaseImportAdapter`
2. Implement `parse_file()` and `map_record()`
3. Register in `scraper/import_package/registry.py` (auto-register on import)
4. Test with `test_import.py`

### Modifying Scoring
- Edit `config/lead_scoring.yaml` — weights, thresholds, opportunity thresholds
- No code changes needed for weight adjustments
- Restart backend to reload config

---

## Production / Deployment Notes

### Current State
- **Development only** — SQLite, no auth, no HTTPS, no rate limiting
- Frontend served by Vite dev server (not production build)
- Backend runs with Flask dev server (not Gunicorn/uWSGI)

### For Production
1. **Build frontend**: `cd frontend && npm run build` → serve `dist/` via Nginx
2. **WSGI server**: `gunicorn -w 4 -b 0.0.0.0:5000 "api.app:create_app()"`
3. **Reverse proxy**: Nginx → Gunicorn (API) + static (frontend)
4. **HTTPS**: Certbot/Let's Encrypt on Nginx
5. **Auth**: Add JWT/OAuth middleware to Flask
6. **Database**: Migrate to PostgreSQL (SQLAlchemy ready in `scraper/persistence/`)
7. **Secrets**: Use Docker secrets / env file / vault
8. **Monitoring**: Add logging, health checks, Prometheus metrics

### Docker Compose (Future)
```yaml
services:
  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    volumes: [ollama_data:/root/.ollama]
  gosom:
    image: gosom/google-maps-scraper
    ports: ["8080:8080"]
  backend:
    build: .
    ports: ["5000:5000"]
    depends_on: [ollama, gosom]
    env_file: .env
  frontend:
    build: ./frontend
    ports: ["80:80"]
    depends_on: [backend]
```

---

## Handoff Notes

### For the Next Developer
1. **Start here** — Read this README completely
2. **Run the Quick Start** — Verify everything works on your machine
3. **Explore the API** — `GET /api/health`, then `/api/leads`, `/api/analytics/overview`
4. **Check the Database** — `sqlite3 data/leads.db ".schema"` then `SELECT * FROM leads LIMIT 5;`
5. **Review Key Files**:
   - `api/app.py` — All endpoints
   - `scraper/discovery/orchestrator.py` — Discovery pipeline
   - `scraper/ai_enrichment.py` — AI enrichment pipeline
   - `scraper/scoring/weight_provider.py` + `config/lead_scoring.yaml` — Scoring
   - `frontend/src/services/api.js` — Frontend API client
6. **Run Tests** — `pytest api/test_analytics.py` etc.

### For the n8n Developer
- Read **docs/N8N_INTEGRATION_HANDOFF.md**
- The `/api/outreach/process` endpoint calls your webhook — implement the receiver
- Lead data structure documented there
- CRM lifecycle transitions: `NEW → QUALIFIED → CONTACTED → INTERESTED → CONVERTED/REJECTED`

### Known Limitations
- No authentication/authorization (dev only)
- Single-user, no multi-tenancy
- SQLite — not suitable for concurrent production writes
- No automated test coverage for frontend
- Outreach queue webhook integration is one-way (CRM → n8n) currently

---

## License

Internal project — BilvaLeaf Business Development Platform. Not for external distribution.

---

*Generated for handoff — keep this README updated as the project evolves.*
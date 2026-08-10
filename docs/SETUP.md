# Setup Documentation

Complete setup guide for AI Lead Scraper CRM on a fresh Windows PC.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Fresh Windows PC Setup](#fresh-windows-pc-setup)
3. [Environment Variables](#environment-variables)
4. [Backend Setup](#backend-setup)
5. [Frontend Setup](#frontend-setup)
6. [Google Maps / Gosom Scraper Setup](#google-maps--gosom-scraper-setup)
7. [Ollama / AI Setup](#ollama--ai-setup)
8. [Database Setup](#database-setup)
9. [Lead Import Setup](#lead-import-setup)
10. [Verification Checklist](#verification-checklist)

---

## System Requirements

| Component | Minimum Version | Recommended | Purpose |
|-----------|-----------------|-------------|---------|
| **Windows** | 10/11 | 11 Pro | OS |
| **Python** | 3.11+ | 3.12 | Backend runtime |
| **Node.js** | 20+ | 22 LTS | Frontend build |
| **Docker Desktop** | 4.25+ | Latest | Gosom scraper |
| **Ollama** | 0.5+ | Latest | Local LLM |
| **Git** | 2.40+ | Latest | Version control |
| **RAM** | 8 GB | 16+ GB | Run all services |
| **Disk** | 10 GB free | 20+ GB | Models, DB, containers |

---

## Fresh Windows PC Setup

### Automated Setup (Recommended)

Run the setup script:

```powershell
# Clone repository
git clone <repository-url>
cd ai-lead-scraper

# Run setup (checks prerequisites, creates venv, installs deps)
.\setup.ps1
```

### Manual Step-by-Step Setup

#### 1. Install Prerequisites

**Python 3.12:**
```powershell
# Option A: winget (recommended)
winget install Python.Python.3.12

# Option B: Download from python.org
# https://www.python.org/downloads/windows/
```

**Node.js 22 LTS:**
```powershell
winget install OpenJS.NodeJS.LTS
# OR download from https://nodejs.org/
```

**Docker Desktop:**
```powershell
winget install Docker.DockerDesktop
# Requires restart after install
```

**Git:**
```powershell
winget install Git.Git
```

**Ollama:**
```powershell
winget install Ollama.Ollama
# OR download from https://ollama.com/download
```

#### 2. Verify Installations

```powershell
python --version       # Should show 3.12.x
node --version         # Should show v22.x.x
npm --version          # Should show 10.x.x
docker --version       # Should show 27.x.x
ollama --version       # Should show 0.5.x
git --version          # Should show 2.45.x
```

#### 3. Clone Repository

```powershell
git clone <repository-url>
cd ai-lead-scraper
```

---

## Environment Variables

### Create `.env` from Template

```powershell
copy .env.example .env
```

### Required Variables (Must Configure)

Edit `.env` with your values:

```bash
# AI / Ollama (REQUIRED)
OLLAMA_BASE_URL=http://localhost:11434
SCRAPEGRAPH_MODEL=ollama/llama3.2
AI_INTELLIGENCE_PROVIDER=ollama

# Database (auto-configured if not set)
DATABASE=data/leads.db

# Optional: OpenAI (if using OpenAI provider)
# OPENAI_API_KEY=sk-xxxxxxxxxx

# Optional: Google Maps API (for Places import)
# GOOGLE_MAPS_API_KEY=xxxxxxxxxx

# Optional: Upwork credentials (for live scraping)
# UPWORK_USERNAME=your_email@example.com
# UPWORK_PASSWORD=your_password

# Optional: Apify (for dataset imports)
# APIFY_TOKEN=apify_xxxxxxxxxx

# Optional: Outreach webhook (for n8n integration)
# OUTREACH_WEBHOOK_URL=https://your-n8n/webhook/outreach
# OUTREACH_BATCH_LIMIT=10
# OUTREACH_MAX_RETRY=3

# Frontend API URL
VITE_API_URL=http://localhost:5000
```

### Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OLLAMA_BASE_URL` | Yes | `http://localhost:11434` | Ollama server endpoint |
| `SCRAPEGRAPH_MODEL` | Yes | `ollama/llama3.2` | Model for ScrapeGraphAI enrichment |
| `AI_INTELLIGENCE_PROVIDER` | No | `ollama` | `ollama` or `openai` |
| `OPENAI_API_KEY` | If OpenAI | — | Required when provider=openai |
| `GOOGLE_MAPS_API_KEY` | No | — | Google Places API key |
| `UPWORK_USERNAME` | No | — | Upwork login email |
| `UPWORK_PASSWORD` | No | — | Upwork password |
| `APIFY_TOKEN` | No | — | Apify API token for imports |
| `OUTREACH_WEBHOOK_URL` | No | — | n8n webhook endpoint |
| `OUTREACH_BATCH_LIMIT` | No | `10` | Max outreach entries per batch |
| `OUTREACH_MAX_RETRY` | No | `3` | Max retry attempts for failed outreach |
| `DATABASE` | No | `data/leads.db` | SQLite database path |
| `LEAD_REPOSITORY_URI` | No | `sqlite:///data/leads_repo.db` | Repository DB URI |
| `VITE_API_URL` | No | `http://localhost:5000` | Frontend API base URL |

---

## Backend Setup

### 1. Create Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Upgrade pip and Install Dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Install Playwright Browsers

```powershell
playwright install chromium
# Optional: install all browsers
# playwright install
```

### 4. Initialize Database

```powershell
python -c "from scraper.database import initialize_database; initialize_database()"
```

Expected output: No errors (creates tables if not exist)

### 5. Run Backend

```powershell
python api/app.py
```

Backend starts at **http://localhost:5000**

Verify health endpoint:
```powershell
curl http://localhost:5000/api/health
# Expected: {"status":"ok"}
```

---

## Frontend Setup

### 1. Navigate to Frontend Directory

```powershell
cd frontend
```

### 2. Install Dependencies

```powershell
npm install
```

### 3. Build for Production (Optional)

```powershell
npm run build
# Output in frontend/dist/
```

### 4. Run Development Server

```powershell
npm run dev
```

Frontend starts at **http://localhost:5173** (Vite default)

---

## Google Maps / Gosom Scraper Setup

### Overview

The Google Maps discovery uses **gosom/google-maps-scraper** — a Go-based scraper running in Docker on port 8080.

### 1. Pull Docker Image

```powershell
docker pull gosom/google-maps-scraper
```

### 2. Start Container

```powershell
docker run -d --name gosom-scraper -p 8080:8080 gosom/google-maps-scraper
```

### 3. Verify Health

```powershell
curl http://localhost:8080/api/v1/health
# Expected: {"status":"ok"} or similar health response
```

### 4. Container Management

| Action | Command |
|--------|---------|
| Stop | `docker stop gosom-scraper` |
| Start | `docker start gosom-scraper` |
| Restart | `docker restart gosom-scraper` |
| Logs | `docker logs gosom-scraper` |
| Remove | `docker rm -f gosom-scraper` |

### 5. Troubleshooting Port 8080

If port 8080 is in use:

```powershell
# Find process using port 8080
netstat -ano | findstr :8080

# Kill process (replace PID)
taskkill /PID <PID> /F

# Or run on different port
docker run -d --name gosom-scraper -p 8081:8080 gosom/google-maps-scraper
# Then update API_BASE_URL in scraper/discovery/providers/google_maps_provider.py
```

### 6. How Flask Communicates with Gosom

**File:** `scraper/discovery/providers/google_maps_provider.py`

- **Base URL:** `http://localhost:8080/api/v1`
- **Flow:**
  1. `POST /jobs` — Submit scraping job with keywords
  2. `GET /jobs/{id}` — Poll for completion (5s interval, 10min max)
  3. `GET /jobs/{id}/download` — Download CSV results
- **Timeout:** 600 seconds max poll time
- **Filters applied:** Blacklisted domains, junk keywords, geo-fencing

---

## Ollama / AI Setup

### 1. Start Ollama Service

```powershell
# Option A: Run in foreground (separate terminal)
ollama serve

# Option B: Run as Windows service (after install)
# Ollama installer registers as service automatically
```

### 2. Pull Required Model

```powershell
ollama pull llama3.2
# Size: ~2 GB
```

### 3. Verify Installation

```powershell
# List models
ollama list
# Expected: llama3.2   latest   2.0 GB

# Test API
curl http://localhost:11434/api/tags
# Expected: JSON with models array containing llama3.2

# Test generation
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2", "prompt": "Say hello", "stream": false}'
```

### 4. Model Configuration

Default model: `llama3.2` (configured via `SCRAPEGRAPH_MODEL=ollama/llama3.2`)

To use a different model:
```bash
# In .env
SCRAPEGRAPH_MODEL=ollama/llama3.1
# OR
SCRAPEGRAPH_MODEL=ollama/mistral
# Then pull the model
ollama pull llama3.1
```

### 5. Fallback Behavior

If Ollama is unavailable:
- Enrichment fails gracefully with error logged
- Leads are saved with `status="failed"` for enrichment step
- AI insights cache validates completeness — invalid entries regenerated
- **No external API fallback** (by design — local-first)

### 6. Alternative: OpenAI Provider

```bash
# In .env
AI_INTELLIGENCE_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxx
```

---

## Database Setup

### Database Technology

- **SQLite** (file-based, no server)
- Python `sqlite3` with FK enforcement
- Row factory for dict-like access

### Database Locations

| Database | Path | Purpose |
|----------|------|---------|
| Main | `data/leads.db` | Leads, jobs, outreach, AI insights |
| Repository | `data/leads_repo.db` | LeadRepository (Phase 19) |
| Opportunities | `data/opportunities.json` | Upwork opportunities (file store) |

### Schema Initialization

Runs automatically on first backend start via `initialize_database()`:

```python
from scraper.database import initialize_database
initialize_database("data/leads.db")
```

**Idempotent** — safe to run multiple times. Performs migrations for missing columns.

### Create Empty Database (Fresh Start)

```powershell
# Backup existing (if any)
move data\leads.db data\leads_backup_$(Get-Date -Format "yyyyMMdd").db

# Re-initialize
.\venv\Scripts\python.exe -c "from scraper.database import initialize_database; initialize_database()"
```

### Backup Database

```powershell
copy data\leads.db data\leads_backup_$(Get-Date -Format "yyyyMMdd_HHmmss").db
```

### Restore Database

```powershell
copy data\leads_backup_20260115.db data\leads.db
```

### Database Inspection

```powershell
# View schema
.\venv\Scripts\python.exe -c "import sqlite3; conn=sqlite3.connect('data/leads.db'); [print(row[0]) for row in conn.execute('SELECT sql FROM sqlite_master WHERE type=\"table\"').fetchall()]"

# Count leads
.\venv\Scripts\python.exe -c "import sqlite3; conn=sqlite3.connect('data/leads.db'); print(conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0])"
```

---

## Lead Import Setup

### Import Scripts

| Script | Purpose |
|--------|---------|
| `import_all_datasets.py` | Imports all available datasets |
| `import_upwork_datasets.py` | Imports Upwork JSON exports |
| `import_and_enrich.py` | Import + trigger AI enrichment |
| `test_apollo_import.py` | Test Apollo import |
| `import_upwork_dataset.py` | Single Upwork dataset import |

### Run Imports

```powershell
# Import all datasets (Apollo, Google Maps, Upwork)
.\venv\Scripts\python.exe import_all_datasets.py

# Import with enrichment
.\venv\Scripts\python.exe import_and_enrich.py
```

### Expected Dataset Formats

#### Apollo JSON
```json
{
  "data": [
    {
      "id": "apollo_123",
      "firstName": "John",
      "lastName": "Doe",
      "title": "CTO",
      "email": "john@company.com",
      "phone": "+1-555-0123",
      "linkedinUrl": "https://linkedin.com/in/johndoe",
      "companyName": "Acme Corp",
      "companyDomain": "acme.com",
      "companyIndustry": "Software",
      "companyDescription": "We build tools...",
      "companySize": "51-200",
      "city": "San Francisco",
      "state": "CA",
      "country": "USA"
    }
  ]
}
```

#### Google Maps JSON
```json
{
  "results": [
    {
      "place_id": "ChIJ...",
      "name": "Acme Corp",
      "website": "https://acme.com",
      "formatted_address": "123 Market St, San Francisco, CA",
      "rating": 4.5,
      "user_ratings_total": 127,
      "types": ["software_company", "point_of_interest", "establishment"],
      "geometry": {"location": {"lat": 37.7749, "lng": -122.4194}},
      "address_components": [
        {"long_name": "San Francisco", "types": ["locality"]},
        {"long_name": "California", "types": ["administrative_area_level_1"]},
        {"long_name": "United States", "types": ["country"]}
      ]
    }
  ]
}
```

#### Upwork JSON
```json
{
  "jobs": [
    {
      "uid": "job_123",
      "title": "Build a React Dashboard",
      "description": "We need a dashboard...",
      "budget": {"type": "fixed", "fixedBudget": 5000},
      "skills": ["React", "TypeScript", "Recharts"],
      "publishedAt": "2026-01-15T10:30:00Z",
      "category": "Web Development",
      "subcategory": "Frontend Development",
      "externalLink": "https://upwork.com/jobs/123",
      "client": {
        "name": "Acme Corp",
        "countryCode": "US",
        "city": "San Francisco",
        "rating": 4.8,
        "stats": {"feedbackRate": 4.8, "feedbackCount": 50, "totalHires": 25, "hireRate": 0.8}
      }
    }
  ]
}
```

### Deduplication

Cross-file deduplication runs automatically:
- **Apollo:** Email + domain
- **Google Maps:** place_id + website
- **Upwork:** uid + externalLink

---

## Verification Checklist

### Pre-Flight Checks

Run each check and confirm ✅:

```powershell
# 1. Python environment
.\venv\Scripts\Activate.ps1
python --version
# ✅ Python 3.12.x

# 2. Dependencies installed
pip list | findstr -i "flask scrapegraph langchain playwright pydantic yaml requests"
# ✅ All packages listed

# 3. Playwright browser
playwright --version
# ✅ 1.61.0

# 4. Node.js
node --version && npm --version
# ✅ v22.x.x / 10.x.x

# 5. Docker
docker --version
# ✅ 27.x.x

# 6. Ollama
ollama --version && ollama list | findstr llama3.2
# ✅ 0.5.x / llama3.2 present
```

### Service Health Checks

```powershell
# 1. Ollama API
curl http://localhost:11434/api/tags
# ✅ {"models":[{"name":"llama3.2:latest",...}]}

# 2. Gosom Scraper
curl http://localhost:8080/api/v1/health
# ✅ {"status":"ok"}

# 3. Backend API
.\venv\Scripts\python.exe api/app.py &
Start-Sleep 3
curl http://localhost:5000/api/health
# ✅ {"status":"ok"}

# 4. Frontend
cd frontend && npm run dev &
Start-Sleep 5
curl http://localhost:5173
# ✅ HTML response (Vite dev server)

# 5. Database
.\venv\Scripts\python.exe -c "from scraper.database import initialize_database; initialize_database(); print('DB OK')"
# ✅ DB OK
```

### Functional Tests

```powershell
# 1. List leads (should work even if empty)
curl http://localhost:5000/api/leads
# ✅ {"leads":[],"count":0}

# 2. Analytics overview
curl http://localhost:5000/api/analytics/overview
# ✅ JSON with KPIs

# 3. Discovery test (Google Search - free)
curl -X POST http://localhost:5000/api/discover/free \
  -H "Content-Type: application/json" \
  -d '{"industry":"software","location":"San Francisco","max_results":3}'
# ✅ Results array with candidates

# 4. Frontend loads in browser
# Open http://localhost:5173 — verify Dashboard, Leads, Discover, Analytics pages
```

### Import Test

```powershell
# Test Apollo import (if dataset exists)
.\venv\Scripts\python.exe test_apollo_import.py
# ✅ Imported X leads

# Test Upwork import
.\venv\Scripts\python.exe test_upwork_import.py
# ✅ Imported X opportunities
```

---

## Complete Startup Sequence (All Services)

### Terminal 1: Ollama
```powershell
ollama serve
```

### Terminal 2: Gosom Scraper
```powershell
docker start gosom-scraper
```

### Terminal 3: Backend
```powershell
cd G:\ai-lead-scraper
.\venv\Scripts\Activate.ps1
python api/app.py
```

### Terminal 4: Frontend
```powershell
cd G:\ai-lead-scraper\frontend
npm run dev
```

### Access Points
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:5000
- **API Health:** http://localhost:5000/api/health
- **Gosom Health:** http://localhost:8080/api/v1/health
- **Ollama API:** http://localhost:11434

---

## Quick Reference Card

| Task | Command |
|------|---------|
| Activate venv | `.\venv\Scripts\Activate.ps1` |
| Start backend | `python api/app.py` |
| Start frontend | `cd frontend && npm run dev` |
| Start Ollama | `ollama serve` |
| Start Gosom | `docker start gosom-scraper` |
| Pull model | `ollama pull llama3.2` |
| Init DB | `python -c "from scraper.database import initialize_database; initialize_database()"` |
| Import all | `python import_all_datasets.py` |
| Run tests | `pytest api/test_analytics.py -v` |
| Backup DB | `copy data\leads.db data\leads_backup.db` |
| View logs | `docker logs gosom-scraper` |

---

*Keep this document updated as the project evolves.*
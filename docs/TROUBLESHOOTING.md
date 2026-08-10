# Troubleshooting Guide

Known issues and solutions for AI Lead Scraper CRM.

---

## Table of Contents

1. [Service Startup Issues](#service-startup-issues)
2. [Port Conflicts](#port-conflicts)
3. [Docker / Gosom Scraper Issues](#docker--gosom-scraper-issues)
4. [Ollama / AI Issues](#ollama--ai-issues)
5. [Database Issues](#database-issues)
6. [Frontend Issues](#frontend-issues)
7. [API / Backend Issues](#api--backend-issues)
8. [Import / Discovery Issues](#import--discovery-issues)
9. [Performance Issues](#performance-issues)
10. [Windows-Specific Issues](#windows-specific-issues)

---

## Service Startup Issues

### Flask Port Already in Use

**Symptom:**
```
OSError: [Errno 98] Address already in use
 * Running on http://127.0.0.1:5000
```

**Cause:** Another process is using port 5000 (common: AirPlay Receiver on macOS, other Flask apps, or previous run didn't clean up).

**Diagnosis:**
```powershell
# Windows
netstat -ano | findstr :5000

# Linux/macOS
lsof -i :5000
```

**Solution:**
```powershell
# Kill the process (replace PID)
taskkill /PID <PID> /F

# Or change port in .env / app config
# In api/app.py, change app.run(port=5001)
```

### Frontend Port Already in Use

**Symptom:**
```
VITE v6.3.5  ready in 300 ms
  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
Port 5173 is already in use
```

**Cause:** Another Vite dev server or process on port 5173.

**Diagnosis:**
```powershell
netstat -ano | findstr :5173
```

**Solution:**
```powershell
taskkill /PID <PID> /F

# Or Vite will auto-prompt to use another port (5174, 5175...)
```

### Virtual Environment Not Activated

**Symptom:**
```
ModuleNotFoundError: No module named 'flask'
```

**Cause:** Running Python without activated venv.

**Solution:**
```powershell
.\venv\Scripts\Activate.ps1
# Prompt should show (venv) prefix
python api/app.py
```

---

## Port Conflicts

### Common Port Usage

| Service | Default Port | Config Location |
|---------|--------------|-----------------|
| Flask Backend | 5000 | `api/app.py` |
| Vite Frontend | 5173 | `frontend/vite.config.js` |
| Gosom Scraper | 8080 | Docker run `-p 8080:8080` |
| Ollama | 11434 | `ollama serve` |

### Finding Process on Port

```powershell
# Windows - find PID
netstat -ano | findstr :<PORT>

# Get process name
tasklist /FI "PID eq <PID>"

# Kill
taskkill /PID <PID> /F
```

### Changing Ports

**Backend (Flask):**
```python
# api/app.py - in __main__ block
if __name__ == "__main__":
    app.run(debug=True, port=5001)
```

**Frontend (Vite):**
```js
// frontend/vite.config.js
export default defineConfig({
  server: { port: 5174 }
})
```

**Gosom Scraper:**
```powershell
docker run -d -p 8081:8080 gosom/google-maps-scraper
# Update API_BASE_URL in scraper/discovery/providers/google_maps_provider.py
```

---

## Docker / Gosom Scraper Issues

### Container Not Running

**Symptom:**
```
curl: (7) Failed to connect to localhost port 8080
```

**Diagnosis:**
```powershell
docker ps -a | findstr gosom
# Check STATUS column - should be "Up"
```

**Solutions:**
```powershell
# Start existing container
docker start gosom-scraper

# If container doesn't exist, create it
docker run -d --name gosom-scraper -p 8080:8080 gosom/google-maps-scraper

# Check logs for errors
docker logs gosom-scraper
```

### Container Crashes / Restart Loop

**Symptom:** Container shows "Restarting" status.

**Diagnosis:**
```powershell
docker logs gosom-scraper
# Look for error messages
```

**Common Causes:**
- Port 8080 already in use on host
- Insufficient memory (Gosom needs ~2GB)
- Chrome/Playwright issues in container

**Solutions:**
```powershell
# Increase Docker memory limit (Docker Desktop > Settings > Resources > Memory > 4GB)

# Check for port conflict
netstat -ano | findstr :8080

# Run with more memory
docker run -d --name gosom-scraper -p 8080:8080 --memory=4g gosom/google-maps-scraper
```

### Health Check Fails

**Symptom:**
```powershell
curl http://localhost:8080/api/v1/health
# Returns 404 or connection refused
```

**Cause:** API endpoint path may differ, or scraper not ready.

**Solutions:**
```powershell
# Try alternative endpoints
curl http://localhost:8080/health
curl http://localhost:8080/api/health
curl http://localhost:8080/

# Wait longer after startup (can take 30-60s)
Start-Sleep 60
curl http://localhost:8080/api/v1/health
```

### Job Submission Fails

**Symptom:** Discovery returns empty results or timeout.

**Diagnosis:**
```powershell
# Check if job was created
curl -X POST http://localhost:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"name":"test","keywords":["software"],"lang":"en","depth":1,"max_time":60}'
```

**Check job status:**
```powershell
curl http://localhost:8080/api/v1/jobs/<JOB_ID>
```

**Common Issues:**
- Keywords too broad/specific
- `max_time` too short (default 3600s in code)
- Gosom scraper version incompatibility

---

## Ollama / AI Issues

### Ollama Service Not Running

**Symptom:**
```
requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=11434): Failed to connect
```

**Diagnosis:**
```powershell
# Check if process exists
tasklist | findstr ollama

# Try API
curl http://localhost:11434/api/tags
```

**Solution:**
```powershell
# Start Ollama (run in separate terminal)
ollama serve

# Or start as service (Windows)
# Ollama installer registers service - check Services.msc
```

### Model Not Found

**Symptom:**
```
Error: model 'llama3.2' not found, try pulling it first
```

**Solution:**
```powershell
ollama pull llama3.2
# Wait for download (~2GB)
```

### Wrong Model Name in Config

**Symptom:** Enrichment works but uses wrong model, or fails silently.

**Check Config:**
```powershell
# In .env
SCRAPEGRAPH_MODEL=ollama/llama3.2

# In code, model is used as:
# "model": os.getenv("SCRAPEGRAPH_MODEL", "ollama/llama3.2")
# Then .replace("ollama/", "") for ChatOllama
```

**Fix:** Ensure `.env` has correct value and restart backend.

### Ollama Out of Memory

**Symptom:** Generation hangs, times out, or returns error.

**Diagnosis:**
```powershell
# Check system memory
# Ollama + model needs ~4-8GB RAM
```

**Solutions:**
```powershell
# Use smaller model
ollama pull llama3.2:1b  # 1B parameter version
# Update .env
SCRAPEGRAPH_MODEL=ollama/llama3.2:1b

# Or increase system RAM / swap
```

### Slow Generation

**Symptom:** Enrichment takes >60 seconds per lead.

**Causes:**
- CPU-only inference (no GPU)
- Large context / complex prompts
- Model too large for hardware

**Solutions:**
- Use smaller model (`llama3.2:1b`, `phi3:mini`)
- Reduce `max_tokens` in prompts
- Enable GPU if available (Ollama auto-detects)

### OpenAI Fallback Not Working

**Symptom:** Set `AI_INTELLIGENCE_PROVIDER=openai` but still uses Ollama.

**Check:**
```powershell
# Verify env var loaded
python -c "import os; print(os.getenv('AI_INTELLIGENCE_PROVIDER'))"

# Restart backend after changing .env
```

---

## Database Issues

### Database File Missing

**Symptom:**
```
sqlite3.OperationalError: unable to open database file
```

**Cause:** `data/` directory doesn't exist or DB not initialized.

**Solution:**
```powershell
# Ensure data directory exists
mkdir data

# Initialize database
python -c "from scraper.database import initialize_database; initialize_database()"
```

### Database Locked

**Symptom:**
```
sqlite3.OperationalError: database is locked
```

**Cause:** Multiple processes accessing DB (Flask + script + tests).

**Solutions:**
```powershell
# Ensure only one backend running
# Close other Python scripts using DB

# If stuck, check for stale connections
# Restart all Python processes
```

### Migration Errors

**Symptom:**
```
sqlite3.OperationalError: no such column: lead_status
```

**Cause:** Old database schema, migration didn't run.

**Solution:**
```powershell
# initialize_database() handles migrations automatically
python -c "from scraper.database import initialize_database; initialize_database()"

# If still fails, backup and recreate
move data\leads.db data\leads_old.db
python -c "from scraper.database import initialize_database; initialize_database()"
```

### Corrupted Database

**Symptom:** Strange errors, missing data, constraint violations.

**Solution:**
```powershell
# Backup first
copy data\leads.db data\leads_corrupt_backup.db

# Try SQLite recovery
sqlite3 data\leads.db ".recover" | sqlite3 data\leads_recovered.db

# Or restore from backup
copy data\leads_backup_20260115.db data\leads.db
```

---

## Frontend Issues

### Blank Page / White Screen

**Symptom:** Frontend loads but shows empty page.

**Diagnosis:**
```bash
# Check browser console (F12)
# Look for:
# - Network errors (API calls failing)
# - JavaScript errors
# - CORS errors
```

**Common Causes:**
1. Backend not running → Check `http://localhost:5000/api/health`
2. CORS issue → Check Flask `CORS(app)` in `api/app.py`
3. Wrong API URL → Check `VITE_API_URL` in `.env` or `frontend/.env`

### Stale Data / Not Updating

**Symptom:** Frontend shows old data after backend changes.

**Solutions:**
```bash
# Hard refresh
Ctrl + Shift + R  (Windows/Linux)
Cmd + Shift + R  (Mac)

# Clear browser cache for localhost
# DevTools > Application > Clear storage

# Restart Vite dev server
Ctrl+C in terminal, then npm run dev
```

### Build Failures

**Symptom:** `npm run build` fails.

**Diagnosis:**
```bash
npm run build
# Check error output
```

**Common Fixes:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Node version issue
node --version  # Ensure 20+

# TypeScript errors (if any)
# Check for missing type definitions
```

### Module Not Found Errors

**Symptom:**
```
Error: Could not find module '@/components/...'
```

**Cause:** Vite alias not configured or import path wrong.

**Check:** `frontend/vite.config.js` for alias config:
```js
resolve: {
  alias: {
    '@': '/src',
  },
}
```

---

## API / Backend Issues

### CORS Errors

**Symptom (Browser Console):**
```
Access to fetch at 'http://localhost:5000/api/leads' from origin 'http://localhost:5173' has been blocked by CORS policy
```

**Cause:** Flask-CORS not configured or origin not allowed.

**Solution:**
```python
# api/app.py - ensure CORS is enabled
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allows all origins in development
```

### 500 Internal Server Error

**Symptom:** API returns 500 with generic error.

**Diagnosis:**
```bash
# Check Flask logs in terminal running backend
# Or check flask.log file
```

**Common Causes:**
- Database error (constraint violation, locked)
- Missing environment variable
- Ollama connection failure
- Import error in route handler

### Import Errors (ModuleNotFoundError)

**Symptom:**
```
ModuleNotFoundError: No module named 'scraper.database'
```

**Cause:** Python path not set correctly.

**Solution:**
```python
# api/app.py already has this:
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
```

**Verify:**
```powershell
.\venv\Scripts\python.exe -c "import sys; print('\n'.join(sys.path))"
# Should include project root
```

### Request Timeout

**Symptom:** Discovery/enrichment requests timeout.

**Cause:** Gosom scraper or Ollama taking too long.

**Solutions:**
- Increase timeout in `requests.post()` calls
- Check Gosom health
- Check Ollama responsiveness
- Reduce `max_results` for discovery

---

## Import / Discovery Issues

### Import Script Fails

**Symptom:** `import_all_datasets.py` or similar fails.

**Diagnosis:**
```powershell
# Run with verbose output
python import_all_datasets.py 2>&1 | Tee-Object import.log
```

**Common Issues:**
- Dataset file not found (check `data/` directory)
- JSON format mismatch (check adapter's `parse_file`)
- Encoding issues (use `encoding="utf-8"`)

### No Leads Discovered

**Symptom:** Discovery returns empty results.

**Checklist:**
1. Gosom scraper running? `curl http://localhost:8080/api/v1/health`
2. Valid industry/location? Try "software" + "San Francisco"
3. `max_results` > 0?
4. Check backend logs for provider errors

### Deduplication Removing Valid Leads

**Symptom:** Expected leads not appearing after import.

**Cause:** Cross-file dedup by email/domain too aggressive.

**Check:** `scraper/import_package/orchestrator.py` `_apply_cross_file_dedup()`

**Debug:**
```python
# Add logging to see what's being deduped
print(f"Deduped: {email_key} / {domain_key}")
```

### Google Maps Returns Generic Pages

**Symptom:** Results are directories (Yelp, Facebook) not businesses.

**Cause:** Filters not working or too permissive.

**Check:** `scraper/discovery/providers/google_maps_provider.py`
- `BLACKLISTED_DOMAINS` 
- `JUNK_KEYWORDS`
- Geo-fencing logic

---

## Performance Issues

### Slow Lead List Loading

**Symptom:** `/api/leads` takes >5 seconds.

**Causes:**
- Too many leads (no pagination)
- Missing indexes
- Complex query

**Solutions:**
```sql
-- Check indexes exist
sqlite3 data/leads.db ".indexes"

-- Key indexes should exist:
-- idx_leads_source_url, idx_leads_data_quality, idx_leads_status, idx_leads_lead_status
```

**API Fix:** Always use pagination:
```
GET /api/leads?limit=50&offset=0
```

### High Memory Usage

**Symptom:** Python process uses >2GB RAM.

**Causes:**
- Large dataset loaded in memory
- Playwright browser instances not closed
- Ollama model in memory

**Solutions:**
- Use pagination/streaming for large operations
- Ensure `browser.close()` in Playwright code
- Ollama keeps model loaded (normal)

### Slow Enrichment

**Symptom:** Enriching 10 leads takes >10 minutes.

**Causes:**
- Sequential processing (by design for Ollama)
- Website timeouts (15s each)
- Large HTML pages

**Solutions:**
- Reduce `timeout` in `requests.get()`
- Skip enrichment for leads without websites
- Batch process overnight

---

## Windows-Specific Issues

### PowerShell Script Execution Blocked

**Symptom:**
```
.\venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled
```

**Solution:**
```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or bypass for single session
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

### Path Too Long Errors

**Symptom:** `FileNotFoundError` or `OSError` on deep paths.

**Solution:**
```powershell
# Enable long paths in Windows 10/11
# Run as Administrator:
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
# Restart required
```

### Docker Desktop WSL2 Issues

**Symptom:** Docker containers fail to start, networking issues.

**Solutions:**
```powershell
# Restart Docker Desktop
# Reset to factory defaults (Docker Desktop > Troubleshoot)

# Ensure WSL2 backend enabled
# Docker Desktop > Settings > General > Use WSL 2 based engine

# Update WSL
wsl --update
```

### Playwright Browser Install Fails

**Symptom:** `playwright install chromium` fails.

**Solutions:**
```powershell
# Run as Administrator
playwright install chromium

# Or install with dependencies
playwright install --with-deps chromium

# Check antivirus not blocking
```

### Environment Variables Not Persisting

**Symptom:** `.env` changes not picked up.

**Cause:** PowerShell session caching, or `.env` not in project root.

**Solutions:**
```powershell
# Restart terminal after .env changes
# Ensure .env is in project root (same level as api/, scraper/)

# Verify loading
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('OLLAMA_BASE_URL'))"
```

---

## Debugging Checklist

When reporting issues, include:

1. **OS & Version:** `Windows 11 Pro 10.0.26200`
2. **Python Version:** `python --version`
3. **Node Version:** `node --version`
4. **Docker Version:** `docker --version`
5. **Ollama Version:** `ollama --version`
6. **Error Message:** Full traceback
7. **Steps to Reproduce:** Numbered list
8. **Logs:** Relevant log output
9. **Config:** `.env` (with secrets redacted)

---

## Getting Help

1. Check this guide first
2. Search existing issues in repository
3. Check logs: `flask.log`, `docker logs gosom-scraper`, browser console
4. Run verification checklist in SETUP.md
5. Create minimal reproduction case

---

*Update this guide when new issues are discovered and resolved.*
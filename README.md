# AI Lead Scraper

Local, free AI lead scraper built with [ScrapeGraphAI](https://github.com/ScrapeGraphAI/Scrapegraph-ai) and a local [Ollama](https://ollama.com/) model. No paid APIs, no API keys.

## Stack

- Python (virtual environment: `venv/`)
- ScrapeGraphAI 2.1.5
- Playwright (headless browser for fetching pages)
- Ollama running locally at `http://localhost:11434` with the `llama3.2` model

## Project Structure

```
scraper/
    test_scraper.py         # Minimal single-URL ScrapeGraphAI test
    scrape_leads.py         # Multi-URL scraper with multi-page enrichment
    scrape_leads_phase2.py  # Phase 2 backup (homepage-only, fallback)
data/
    urls.txt          # Input: one website URL per line
    leads.csv         # Output: extracted leads (generated, git-ignored)
requirements.txt
README.md
```

## Setup

1. Install and start [Ollama](https://ollama.com/), then pull the model:

   ```powershell
   ollama pull llama3.2
   ```

2. Activate the virtual environment and install dependencies:

   ```powershell
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   playwright install chromium
   ```

## Run the Test Scraper

From the project root:

```powershell
.\venv\Scripts\python.exe scraper\test_scraper.py
```

The script scrapes the single URL set in the `TEST_URL` variable near the top of
[scraper/test_scraper.py](scraper/test_scraper.py) and prints the extracted lead
data (`business_name`, `contact_name`, `email`, `phone`, `website`, `city`) as
formatted JSON. Fields not found on the page are returned as `null`.

To test a different website, edit `TEST_URL` and re-run.

## Run the Multi-URL Lead Scraper

1. Add website URLs to [data/urls.txt](data/urls.txt), one per line.
   Blank lines and lines starting with `#` are ignored; duplicates are removed.

2. From the project root:

   ```powershell
   .\venv\Scripts\python.exe scraper\scrape_leads.py
   ```

Behavior:

- For each site, the scraper first extracts from the **homepage**, then
  discovers and scrapes up to 3 likely lead-bearing internal pages
  (contact, about, team, ...) until all lead fields are filled.
- **Verified contact policy:** `email` and `phone` come ONLY from
  deterministic harvesting of `mailto:`/`tel:` links and visible page text
  (scripts/styles stripped). LLM-generated emails/phones are always
  discarded — LLMs can hallucinate plausible-looking contact data.
- Each verified email/phone carries **provenance** in the CSV: the exact
  page it was found on and the mechanism (`mailto`, `tel`, `visible_text`).
- The `website` column is **canonicalized** to the scraped domain; an
  LLM-suggested website is only kept if it belongs to the same domain.
- Combined values like `"Filip Popovic, COO"` are split into
  `contact_name` + `contact_role` deterministically.
- URLs are processed **sequentially** (Ollama runs locally, one request at a time).
- Each result is appended to `data/leads.csv` **immediately**, so completed
  work is not lost if the run is interrupted.
- If a website fails, the error is recorded in the CSV and the run continues
  with the next URL.
- Re-running skips URLs that were already scraped successfully (no duplicate
  records); failed URLs are retried.
- A summary (total / successful / failed) is printed at the end.

### Lead schema (`data/leads.csv`)

| Column | Source | Notes |
|---|---|---|
| `company_name` | LLM | Company/brand name |
| `industry` | LLM | Short category, e.g. "Web Scraping", "SaaS" |
| `company_description` | LLM | 1-2 sentences |
| `contact_name` | LLM + validation | Person's name; company names rejected |
| `contact_role` | deterministic split | e.g. "COO" from "Filip Popovic, COO" |
| `email` | **harvest only** | mailto:/visible text; never LLM |
| `phone` | **harvest only** | tel: links; never LLM |
| `website` | canonicalized | Scraped domain wins over LLM guesses |
| `city`, `country` | LLM | |
| `source_url` | input | Original URL from urls.txt |
| `source_pages` | scraper | All pages used, `\|`-separated |
| `email_source_page/_type` | harvest | Provenance (`mailto`/`visible_text`) |
| `phone_source_page/_type` | harvest | Provenance (`tel`) |
| `scraped_at` | scraper | UTC timestamp |
| `status` | scraper | `success` / `no_data` / `failed` |
| `quality_score` | deterministic | 0-100, see below |
| `data_quality` | deterministic | HIGH / MEDIUM / LOW / NONE |
| `error` | scraper | Exception message on failure |

### Quality scoring (computed in Python, never by the LLM)

| Signal | Points |
|---|---|
| Verified email | +30 |
| Verified phone | +20 |
| Valid contact_name | +15 |
| contact_role | +10 |
| company_name | +10 |
| industry | +5 |
| city or country | +5 |
| company_description | +5 |

`data_quality`: 75-100 = HIGH, 50-74 = MEDIUM, 20-49 = LOW, 0-19 = NONE.
Failed rows are always NONE. The website/source_url alone contributes nothing.

> **Schema guard:** the scraper refuses to append to a `leads.csv` whose
> header doesn't match the current schema — rename/back up old files first
> (`Rename-Item data\leads.csv leads_old_schema_backup.csv`).

> **Re-scraping already-processed URLs:** successful URLs in `data/leads.csv`
> are skipped on re-run. To re-scrape everything,
> rename or delete `data/leads.csv` first.

The previous homepage-only implementation is preserved as
[scraper/scrape_leads_phase2.py](scraper/scrape_leads_phase2.py) and can be
run the same way as a fallback.

## Roadmap (not implemented yet)

- SQLite persistent storage
- Flask API + background scraping jobs
- React dashboard

"""
Phase 2: Multi-URL lead scraper.

Reads website URLs from data/urls.txt, extracts lead information from each
site using ScrapeGraphAI + local Ollama (llama3.2), and appends results to
data/leads.csv immediately after each URL so completed work survives an
interruption.

No API keys, no paid services. Ollama must be running at http://localhost:11434.
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scrapegraphai.graphs import SmartScraperGraph

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
URLS_FILE = PROJECT_ROOT / "data" / "urls.txt"
OUTPUT_CSV = PROJECT_ROOT / "data" / "leads.csv"

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"

LEAD_FIELDS = ["business_name", "contact_name", "email", "phone", "website", "city"]
CSV_COLUMNS = LEAD_FIELDS + ["source_url", "scraped_at", "status", "error"]

EXTRACTION_PROMPT = """
Extract business/lead information from this website.

Return a JSON object with exactly these keys:
- business_name
- contact_name
- email
- phone
- website
- city

Strict rules:
1. Do NOT invent, guess, or infer any information.
2. Only extract information that is actually present in the page content.
3. If a piece of information cannot be found on the page, set its value to null.
4. Never generate fake emails or phone numbers.
"""

GRAPH_CONFIG = {
    "llm": {
        "model": f"ollama/{OLLAMA_MODEL}",
        "base_url": OLLAMA_BASE_URL,
        "temperature": 0,
        "format": "json",
        "model_tokens": 8192,
    },
    "verbose": False,
    "headless": True,
}


# ---------------------------------------------------------------------------
# URL input handling
# ---------------------------------------------------------------------------
def normalize_url(raw: str) -> str:
    """Normalize a URL: trim whitespace, add https:// if no scheme."""
    url = raw.strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    return url


def load_urls(path: Path) -> list[str]:
    """Read URLs from file, skipping blanks and # comments, deduplicating."""
    urls: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        url = normalize_url(line)
        key = url.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        urls.append(url)
    return urls


# ---------------------------------------------------------------------------
# CSV output handling
# ---------------------------------------------------------------------------
def load_already_scraped(path: Path) -> set[str]:
    """Return source_urls already successfully scraped in a previous run."""
    if not path.exists():
        return set()
    done: set[str] = set()
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status") == "success" and row.get("source_url"):
                done.add(row["source_url"].rstrip("/").lower())
    return done


def append_row(path: Path, row: dict) -> None:
    """Append one result row, writing the header if the file is new."""
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------
def scrape_url(url: str) -> dict:
    """Scrape one URL and return the extracted lead fields."""
    graph = SmartScraperGraph(
        prompt=EXTRACTION_PROMPT,
        source=url,
        config=GRAPH_CONFIG,
    )
    result = graph.run()

    if isinstance(result, str):
        result = json.loads(result)
    if not isinstance(result, dict):
        raise ValueError(f"Unexpected result type from scraper: {type(result).__name__}")

    # Some models nest the answer under a single wrapper key
    if len(result) == 1 and isinstance(next(iter(result.values())), dict):
        result = next(iter(result.values()))

    lead = {}
    for field in LEAD_FIELDS:
        value = result.get(field)
        lead[field] = "" if value in (None, "null", "NA", "N/A") else str(value).strip()
    return lead


def make_row(url: str, lead: dict | None, error: str | None) -> dict:
    """Build a full CSV row for one processed URL."""
    row = {field: "" for field in LEAD_FIELDS}
    if lead:
        row.update(lead)
    row["source_url"] = url
    row["scraped_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    row["status"] = "failed" if error else "success"
    row["error"] = error or ""
    return row


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    if not URLS_FILE.exists():
        print(f"URL file not found: {URLS_FILE}", file=sys.stderr)
        return 1

    urls = load_urls(URLS_FILE)
    if not urls:
        print(f"No URLs found in {URLS_FILE}", file=sys.stderr)
        return 1

    already_scraped = load_already_scraped(OUTPUT_CSV)

    total = len(urls)
    successful = 0
    failed = 0

    for i, url in enumerate(urls, start=1):
        if url.rstrip("/").lower() in already_scraped:
            print(f"[{i}/{total}] Skipped (already scraped): {url}")
            continue

        print(f"[{i}/{total}] Scraping: {url}")
        try:
            lead = scrape_url(url)
        except Exception as exc:
            failed += 1
            error = f"{type(exc).__name__}: {exc}"
            append_row(OUTPUT_CSV, make_row(url, None, error))
            print(f"[{i}/{total}] Failed: {url}")
            print(f"Error: {error}")
            continue

        successful += 1
        append_row(OUTPUT_CSV, make_row(url, lead, None))
        print(f"[{i}/{total}] Completed successfully")

    print("\n--- SCRAPING SUMMARY ---")
    print(f"Total URLs: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Output: data/leads.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())

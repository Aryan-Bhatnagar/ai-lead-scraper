"""Deterministic contact-harvesting debug tool. NO Ollama, NO LLM.

Fetches a site's homepage plus discovered lead-bearing pages and prints every
email/phone candidate with full provenance, plus what would be rejected.

Run: python scraper/debug_harvest.py [url]   (default: https://scrapegraphai.com/)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scrape_leads as sl


def debug_site(url: str) -> None:
    print(f"=== Deterministic harvest debug: {url} ===\n")

    homepage_html = sl.fetch_html(url)
    pages = [url] + sl.discover_pages(url, homepage_html)
    print(f"Pages to inspect: {pages}\n")

    all_emails: list[dict] = []
    all_phones: list[dict] = []

    for page_url in pages:
        html = homepage_html if page_url == url else sl.fetch_html(page_url)
        print(f"--- {page_url} ({len(html)} bytes) ---")

        found = sl.harvest_contacts(html, source_page=page_url)
        for c in found["emails"] + found["phones"]:
            print(f"  ACCEPTED  value={c['value']!r}  source_type={c['source_type']}")
        all_emails += found["emails"]
        all_phones += found["phones"]

        # Also show what the OLD behavior would have found: raw regex over the
        # full document text incl. scripts — and why each hit is now rejected.
        soup = sl.BeautifulSoup(html, "html.parser")
        raw_hits = set(sl.EMAIL_REGEX.findall(soup.get_text(" ")))
        script_only = raw_hits - set(sl.EMAIL_REGEX.findall(sl.visible_text(soup)))
        accepted = {c["value"] for c in found["emails"]}
        for hit in sorted(raw_hits - accepted):
            reasons = []
            if hit in script_only:
                reasons.append("only in script/style, not visible text")
            if not sl.valid_email(hit):
                reasons.append("fails valid_email")
            elif sl.suspicious_visible_email(hit):
                reasons.append("suspicious/random-looking")
            print(f"  REJECTED  value={hit!r}  reason={'; '.join(reasons) or 'duplicate'}")
        if not raw_hits and not found["phones"]:
            print("  (no candidates found)")
        print()

    print("=== Final selection ===")
    email_pick = sl.select_email(all_emails)
    phone_pick = sl.select_phone(all_phones)
    for label, pick in (("email", email_pick), ("phone", phone_pick)):
        if pick:
            print(f"Selected {label}: {pick['value']}")
            print(f"Source page: {pick['source_page']}")
            print(f"Source type: {pick['source_type']}")
        else:
            print(f"Selected {label}: None")


if __name__ == "__main__":
    debug_site(sys.argv[1] if len(sys.argv) > 1 else "https://scrapegraphai.com/")

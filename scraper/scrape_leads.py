"""
Phase 4: Multi-page lead scraper with final schema and quality scoring.

For each website in data/urls.txt:
  1. Fetch the homepage and discover likely lead-bearing internal pages
     (contact, about, team, ...) from its links.
  2. Scrape pages with ScrapeGraphAI + local Ollama (llama3.2) for
     company/contact profile fields.
  3. Deterministically harvest email/phone from mailto:/tel: links and
     visible page text with full provenance. Email and phone are
     VERIFIED-ONLY: LLM-generated values for them are always discarded.
  4. Canonicalize the website against the source domain, split
     "Name, Role" contacts, compute a deterministic quality score, and
     append the row to data/leads.csv immediately.

No API keys, no paid services. Ollama must be running at http://localhost:11434.
"""

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from scrapegraphai.graphs import SmartScraperGraph

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
URLS_FILE = PROJECT_ROOT / "data" / "urls.txt"
OUTPUT_CSV = PROJECT_ROOT / "data" / "leads.csv"

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"

# Max additional pages (beyond the homepage) to scrape per site
MAX_EXTRA_PAGES = 3

# Exact path slugs that are almost certainly lead-bearing pages (best first).
# Matching one of these outranks any fuzzy keyword match.
EXACT_PAGE_SLUGS = [
    "contact",
    "contact-us",
    "about",
    "about-us",
    "team",
    "our-team",
    "leadership",
    "kontakt",
    "impressum",
]

# Fuzzy keywords used only when no exact slug matches (lower priority).
PAGE_KEYWORDS = [
    "contact",
    "kontakt",
    "about",
    "team",
    "company",
    "impressum",
    "support",
    "get-in-touch",
    "reach-us",
]

FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}
FETCH_TIMEOUT = 20  # seconds, for plain HTML fetches (not the LLM)

# ---------------------------------------------------------------------------
# Final lead schema (Phase 4)
# ---------------------------------------------------------------------------
LEAD_FIELDS = [
    "company_name",
    "industry",
    "company_description",
    "contact_name",
    "contact_role",
    "email",
    "phone",
    "website",
    "city",
    "country",
]

PROVENANCE_COLUMNS = [
    "email_source_page",
    "email_source_type",
    "phone_source_page",
    "phone_source_type",
]

CSV_COLUMNS = (
    LEAD_FIELDS
    + ["source_url", "source_pages"]
    + PROVENANCE_COLUMNS
    + ["scraped_at", "status", "quality_score", "data_quality", "error"]
)

# Fields that count as real lead data (website/source_url alone do not)
MEANINGFUL_FIELDS = ["company_name", "contact_name", "email", "phone", "city", "country"]

# VERIFIED CONTACT DATA POLICY:
# email/phone may ONLY come from deterministic HTML harvesting (mailto:/tel:
# links, visible text). LLM-generated values for these fields are
# discarded — LLMs hallucinate plausible-looking contact data.
LLM_ALLOWED_FIELDS = [
    "company_name",
    "industry",
    "company_description",
    "contact_name",
    "contact_role",
    "website",
    "city",
    "country",
]
VERIFIED_ONLY_FIELDS = ["email", "phone"]

# When several valid emails are harvested, prefer these prefixes in order
EMAIL_PRIORITY_PREFIXES = ["sales@", "hello@", "contact@", "info@"]

# Trust ranking for harvested email sources: mailto links are explicit and
# author-intended; visible-text matches are weaker evidence.
SOURCE_TYPE_RANK = {"mailto": 0, "visible_text": 1}

# Print selected email/phone provenance per company
DEBUG_CONTACTS = True

EXTRACTION_PROMPT = """
Extract company/lead profile information from this website page.

Return a JSON object with exactly these keys:
- company_name
- industry
- company_description
- contact_name
- contact_role
- website
- city
- country

Field guidance:
- industry: a short category such as "Web Scraping", "SaaS", "Data Services".
- company_description: 1-2 concise sentences describing what the company does.
- contact_name: a real person's name if one is shown on the page.
- contact_role: that person's role/title if shown (e.g. "CEO", "Head of Sales").

Strict rules:
1. Do NOT invent, guess, or infer any information.
2. Only extract information that is actually present in the page content.
3. If a piece of information cannot be found on the page, set its value to null.
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

# Emails that are boilerplate/false positives, not real leads
EMAIL_BLOCKLIST_PATTERNS = re.compile(
    r"(example\.com|sentry|wixpress|\.png$|\.jpg$|\.jpeg$|\.gif$|\.svg$|\.webp$|"
    r"noreply|no-reply|donotreply)",
    re.IGNORECASE,
)
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# Local part: allowed chars only (no whitespace), must contain >=1 alphanumeric,
# and must start with an alphanumeric (rejects "+@...", ".x@...").
EMAIL_LOCAL_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._%+-]*$")
# Domain label: alphanumeric, hyphens allowed inside, never empty.
DOMAIN_LABEL_REGEX = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$")
TLD_REGEX = re.compile(r"^[a-zA-Z]{2,}$")

# Placeholder / example addresses that must never be recorded as leads
PLACEHOLDER_EMAIL_DOMAINS = {
    "example.com", "example.org", "example.net", "email.com",
    "domain.com", "yourdomain.com", "yourcompany.com", "test.com",
    # Reserved/example TLDs – never accept
    "example", "invalid", "localhost", "test",
}
FILE_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".css", ".js", ".pdf", ".woff", ".woff2",
)

# LLM outputs that are UI text / placeholders, not real values
JUNK_VALUES = {
    "contact us", "contact", "call now", "call us", "get in touch", "reach us",
    "email us", "click here", "learn more", "n/a", "na", "null", "none",
    "unknown", "not found", "not available", "not provided", "-",
}

# Social media URL patterns for harvesting
SOCIAL_PATTERNS = {
    "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/(?:in|company)/[^/?\s]+", re.IGNORECASE),
    "twitter": re.compile(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/[^/?\s]+", re.IGNORECASE),
    "facebook": re.compile(r"https?://(?:www\.)?facebook\.com/[^/?\s]+", re.IGNORECASE),
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[^/?\s]+", re.IGNORECASE),
}

COMPANY_SUFFIXES = {
    "inc", "ltd", "limited", "llc", "llp", "pvt", "pvt ltd", "private",
    "private limited", "corp", "corporation", "company", "co", "gmbh",
    "srl", "sa", "ag", "plc",
}

# Words that identify a job title/role for contact_name splitting
ROLE_KEYWORDS = {
    "ceo", "coo", "cto", "cfo", "cmo", "cio", "founder", "co-founder",
    "cofounder", "owner", "president", "vp", "director", "manager",
    "head", "chief", "partner", "principal", "lead", "officer",
}


# ---------------------------------------------------------------------------
# Field validation
# ---------------------------------------------------------------------------
def is_junk(value: str) -> bool:
    return value.strip().lower() in JUNK_VALUES


def valid_email(value: str) -> bool:
    """Strict deterministic email validation (no LLM involved)."""
    value = value.strip()
    if not value or any(c.isspace() for c in value):
        return False
    if value.count("@") != 1:
        return False

    local, domain = value.split("@")

    # Local part: non-empty, allowed charset, contains and starts with alphanumeric
    if not local or not EMAIL_LOCAL_REGEX.match(local):
        return False
    if not any(c.isalnum() for c in local):
        return False

    # Domain: at least one dot, no empty labels, valid label charset, alpha TLD >= 2
    if "." not in domain:
        return False
    labels = domain.split(".")
    if any(not DOMAIN_LABEL_REGEX.match(label) for label in labels):
        return False
    if not TLD_REGEX.match(labels[-1]):
        return False

    # Placeholder domains, file extensions, and noreply-style blocklist
    if domain.lower() in PLACEHOLDER_EMAIL_DOMAINS:
        return False
    # Reserved/example TLDs – never accept
    for suffix in ("example", "invalid", "localhost", "test"):
        if domain.lower().endswith("." + suffix):
            return False
    if value.lower().endswith(FILE_EXTENSIONS):
        return False
    if EMAIL_BLOCKLIST_PATTERNS.search(value):
        return False
    return True


def valid_phone(value: str) -> bool:
    """A plausible phone: 7-15 digits once formatting is stripped."""
    value = value.strip()
    if not value or is_junk(value):
        return False
    digits = re.sub(r"\D", "", value)
    if not (7 <= len(digits) <= 15):
        return False
    # Reject strings that are mostly letters (e.g. "Call Now: sales team")
    letters = sum(c.isalpha() for c in value)
    return letters <= len(digits)


def normalize_company_name(value: str) -> str:
    """Lowercase, strip punctuation and trailing company suffixes.

    Used only for comparing contact_name against company_name.
    """
    cleaned = re.sub(r"[^\w\s]", " ", value.lower())
    words = cleaned.split()
    while words and words[-1] in COMPANY_SUFFIXES:
        words.pop()
    return " ".join(words)


def valid_contact_name(value: str, company_name: str = "") -> bool:
    """A person's name: not UI text, not the company name, looks like a name."""
    value = value.strip()
    if not value or is_junk(value):
        return False
    if company_name:
        # "PromptCloud Inc" vs company "PromptCloud" -> same after
        # suffix/punctuation normalization -> reject as a company name
        if normalize_company_name(value) == normalize_company_name(company_name):
            return False
    if EMAIL_REGEX.search(value) or any(c.isdigit() for c in value):
        return False
    words = value.split()
    return 1 < len(words) <= 4 and all(w[0].isalpha() for w in words)


# ---------------------------------------------------------------------------
# Contact role splitting
# ---------------------------------------------------------------------------
def looks_like_role(text: str) -> bool:
    """True when text reads as a job title (CEO, Head of Sales, ...)."""
    t = text.strip().rstrip(".").lower()
    if not t or len(t) > 60 or is_junk(t):
        return False
    words = re.split(r"[\s/&,]+", t)
    return any(w in ROLE_KEYWORDS for w in words) or "vice president" in t


def split_contact_role(value: str) -> tuple[str, str]:
    """Deterministically split "Filip Popovic, COO" -> ("Filip Popovic", "COO").

    Supports "Name, Role", "Name - Role", "Name | Role", "Name (Role)".
    Returns (value, "") unchanged when no recognizable role is attached.
    """
    value = value.strip()

    m = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", value)
    if m and looks_like_role(m.group(2)):
        return m.group(1).strip(" ,"), m.group(2).strip()

    for sep in (",", "|", " - ", " – ", " — "):
        if sep in value:
            name, role = value.split(sep, 1)
            if name.strip() and looks_like_role(role):
                return name.strip(), role.strip()
    return value, ""


# ---------------------------------------------------------------------------
# Website canonicalization
# ---------------------------------------------------------------------------
def domain_of(url: str) -> str:
    """Hostname without port or leading www."""
    host = urlparse(url).netloc.lower().split(":")[0]
    return host.removeprefix("www.")


def same_company_domain(a: str, b: str) -> bool:
    """True when two hostnames belong to the same site (subdomains allowed)."""
    if not a or not b:
        return False
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def canonical_website(source_url: str, llm_website: str) -> str:
    """The canonical website is the source_url's domain being scraped.

    An LLM-supplied website is accepted only when it clearly belongs to the
    same domain (e.g. console.apify.com for apify.com). Anything else —
    including near-miss hallucinations like scrapograph.ai for
    scrapegraphai.com — is discarded in favor of the source_url.
    """
    if not llm_website:
        return source_url
    candidate = llm_website.strip()
    if not candidate.lower().startswith(("http://", "https://")):
        candidate = "https://" + candidate
    if same_company_domain(domain_of(candidate), domain_of(source_url)):
        return candidate
    return source_url


# ---------------------------------------------------------------------------
# Lead cleaning
# ---------------------------------------------------------------------------
def clean_lead(lead: dict) -> dict:
    """Drop invalid/junk values and split combined name+role.

    Runs on every LLM result and once more on the final merged lead.
    """
    cleaned = dict(lead)
    for field in LEAD_FIELDS:
        if cleaned.get(field) and is_junk(cleaned[field]):
            cleaned[field] = ""

    if cleaned.get("email") and not valid_email(cleaned["email"]):
        cleaned["email"] = ""
    if cleaned.get("phone") and not valid_phone(cleaned["phone"]):
        cleaned["phone"] = ""

    # Split "Filip Popovic, COO" before validating the name
    if cleaned.get("contact_name"):
        name, role = split_contact_role(cleaned["contact_name"])
        if role:
            cleaned["contact_name"] = name
            if not cleaned.get("contact_role"):
                cleaned["contact_role"] = role

    if cleaned.get("contact_name") and not valid_contact_name(
        cleaned["contact_name"], cleaned.get("company_name", "")
    ):
        cleaned["contact_name"] = ""

    if cleaned.get("contact_role") and not looks_like_role(cleaned["contact_role"]):
        cleaned["contact_role"] = ""
    # A role without a person attached is not lead data
    if cleaned.get("contact_role") and not cleaned.get("contact_name"):
        cleaned["contact_role"] = ""

    return cleaned


def has_meaningful_data(lead: dict) -> bool:
    """True if at least one real lead field is filled (website doesn't count)."""
    return any(lead.get(f) for f in MEANINGFUL_FIELDS)


# ---------------------------------------------------------------------------
# Quality scoring (deterministic, no LLM)
# ---------------------------------------------------------------------------
def quality_score(lead: dict) -> int:
    """0-100 deterministic score. Website/source_url contribute nothing."""
    score = 0
    if lead.get("email"):
        score += 30
    if lead.get("phone"):
        score += 20
    if lead.get("contact_name"):
        score += 15
    if lead.get("contact_role"):
        score += 10
    if lead.get("company_name"):
        score += 10
    if lead.get("industry"):
        score += 5
    if lead.get("city") or lead.get("country"):
        score += 5
    if lead.get("company_description"):
        score += 5
    return min(score, 100)


def data_quality(score: int, status: str) -> str:
    """Map a quality score to HIGH/MEDIUM/LOW/NONE. Failed rows are NONE."""
    if status == "failed":
        return "NONE"
    if score >= 75:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    if score >= 20:
        return "LOW"
    return "NONE"


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
# Page fetching + discovery
# ---------------------------------------------------------------------------
def fetch_html_via_browser(url: str) -> str:
    """Fetch rendered HTML with headless Playwright (for bot-protected sites)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=FETCH_HEADERS["User-Agent"])
            page.goto(url, timeout=FETCH_TIMEOUT * 1000, wait_until="domcontentloaded")
            return page.content()
        finally:
            browser.close()


def fetch_html(url: str) -> str:
    """Fetch raw HTML for link discovery / contact harvesting.

    Tries a plain HTTP request first (fast); falls back to a headless
    browser when the site blocks non-browser clients (e.g. 403).
    """
    try:
        resp = requests.get(url, headers=FETCH_HEADERS, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException:
        return fetch_html_via_browser(url)


def discover_pages(homepage_url: str, html: str) -> list[str]:
    """Find internal pages likely to contain lead info, best-first."""
    base_host = domain_of(homepage_url)
    soup = BeautifulSoup(html, "html.parser")

    scored: dict[str, tuple] = {}  # url -> best (lowest) (tier, index) rank
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        full = urljoin(homepage_url, href).split("#")[0].rstrip("/")
        parsed = urlparse(full)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc.lower().removeprefix("www.") != base_host:
            continue  # external link
        if full.rstrip("/") == homepage_url.rstrip("/"):
            continue

        # Tier 0: last path segment IS an exact slug (/contact, /about-us, ...).
        # Tier 1: slug/keyword appears only as part of a longer path or link
        #         text (/contact-database, ...) — used only as a fallback.
        last_segment = parsed.path.rstrip("/").split("/")[-1].lower()
        haystack = (parsed.path + " " + a.get_text(" ", strip=True)).lower()

        rank = None
        if last_segment in EXACT_PAGE_SLUGS:
            rank = (0, EXACT_PAGE_SLUGS.index(last_segment))
        else:
            for i, keyword in enumerate(PAGE_KEYWORDS):
                if keyword in haystack:
                    rank = (1, i)
                    break
        if rank is not None and (full not in scored or rank < scored[full]):
            scored[full] = rank

    ordered = sorted(scored, key=lambda u: (scored[u], len(u)))
    return ordered[:MAX_EXTRA_PAGES]


# ---------------------------------------------------------------------------
# Deterministic contact harvesting (with provenance)
# ---------------------------------------------------------------------------
def suspicious_visible_email(value: str) -> bool:
    """Heuristic for random-looking visible-text emails (e.g. obfuscation
    artifacts or minified-code strings like pb.dlzmt@uw.ur).

    Applied ONLY to visible_text candidates — a valid mailto: address is
    never rejected for looking unusual.
    """
    local, _, domain = value.partition("@")
    local_letters = re.sub(r"[^a-zA-Z]", "", local)
    # Real mailbox names virtually always contain a vowel (sales, info, jsmith)
    if local_letters and not re.search(r"[aeiouyAEIOUY]", local_letters):
        return True
    # Gibberish second-level domain with no vowels (e.g. "xkcdq" but not "uw")
    sld_letters = re.sub(r"[^a-zA-Z]", "", domain.split(".")[0])
    if len(sld_letters) >= 4 and not re.search(r"[aeiouyAEIOUY]", sld_letters):
        return True
    return False


def visible_text(soup: BeautifulSoup) -> str:
    """Readable page text only: script/style/noscript/template removed."""
    soup = BeautifulSoup(str(soup), "html.parser")  # work on a copy
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    return soup.get_text(" ")


def harvest_contacts(html: str, source_page: str = "") -> dict:
    """Deterministically extract ALL emails/phones literally present in the HTML.

    Sources, in trust order:
      - mailto:/tel: hrefs (explicit, author-intended)
      - visible page text (script/style/noscript stripped first; candidates
        additionally pass a suspicious-gibberish filter)

    Nothing is guessed or generated. Every candidate is validated and carries
    provenance: {"value", "source_page", "source_type"}.
    """
    soup = BeautifulSoup(html, "html.parser")
    emails: list[dict] = []
    phones: list[dict] = []

    def seen_email(value: str) -> bool:
        return value.lower() in (c["value"].lower() for c in emails)

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("mailto:"):
            candidate = href[7:].split("?")[0].strip()
            if valid_email(candidate) and not seen_email(candidate):
                emails.append(
                    {"value": candidate, "source_page": source_page, "source_type": "mailto"}
                )
        elif href.lower().startswith("tel:"):
            candidate = href[4:].strip()
            if valid_phone(candidate) and candidate not in (c["value"] for c in phones):
                phones.append(
                    {"value": candidate, "source_page": source_page, "source_type": "tel"}
                )

    # Visible-text emails: readable text only, never raw HTML/JS/CSS/JSON
    for candidate in EMAIL_REGEX.findall(visible_text(soup)):
        if (
            valid_email(candidate)
            and not suspicious_visible_email(candidate)
            and not seen_email(candidate)
        ):
            emails.append(
                {"value": candidate, "source_page": source_page, "source_type": "visible_text"}
            )

    return {"emails": emails, "phones": phones}


def select_email(candidates: list[dict]) -> dict | None:
    """Pick the best harvested email candidate deterministically.

    Primary: source trust (mailto beats visible_text).
    Secondary: mailbox priority (sales@ > hello@ > contact@ > info@ > other).
    Ties keep discovery order.
    """
    if not candidates:
        return None

    def prefix_rank(value: str) -> int:
        for i, prefix in enumerate(EMAIL_PRIORITY_PREFIXES):
            if value.lower().startswith(prefix):
                return i
        return len(EMAIL_PRIORITY_PREFIXES)

    return min(
        candidates,
        key=lambda c: (
            SOURCE_TYPE_RANK.get(c["source_type"], 9),
            prefix_rank(c["value"]),
            candidates.index(c),
        ),
    )


def select_phone(candidates: list[dict]) -> dict | None:
    """Pick the first harvested (already validated) phone candidate."""
    return candidates[0] if candidates else None


def harvest_socials(html: str) -> dict:
    """Harvest social profile links from HTML."""
    socials = {}
    for platform, pattern in SOCIAL_PATTERNS.items():
        matches = pattern.findall(html)
        if matches:
            # Take the first unique match per platform
            seen = set()
            for match in matches:
                clean = match.split("?")[0].split("#")[0].rstrip("/")
                if clean.lower() not in seen:
                    seen.add(clean.lower())
                    socials[platform] = clean
                    break
    return socials


# ---------------------------------------------------------------------------
# LLM scraping + merging
# ---------------------------------------------------------------------------
def scrape_page(url: str) -> dict:
    """Scrape one page with ScrapeGraphAI and return LLM-allowed lead fields.

    Wrapped in a try-except block to prevent crashes if the local AI service (Ollama)
    is unavailable.
    """
    try:
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

        # VERIFIED CONTACT DATA POLICY: keep only LLM-allowed fields; any
        # LLM-generated email/phone is discarded here (provenance: "llm").
        lead = {field: "" for field in LEAD_FIELDS}
        for field in LLM_ALLOWED_FIELDS:
            value = result.get(field)
            # Migration shim: some prompts/models may still answer business_name
            if field == "company_name" and value in (None, ""):
                value = result.get("business_name")
            lead[field] = "" if value in (None, "null", "NA", "N/A") else str(value).strip()
        return clean_lead(lead)
    except (requests.exceptions.ConnectionError, ConnectionRefusedError) as e:
        print(f"    -> AI Service Unavailable (Ollama): {e}. Skipping LLM extraction for this page.")
        return {field: "" for field in LEAD_FIELDS}
    except Exception as e:
        print(f"    -> Unexpected error during LLM scrape of {url}: {e}")
        return {field: "" for field in LEAD_FIELDS}


def merge_leads(base: dict, extra: dict) -> dict:
    """Fill empty fields in `base` with values from `extra`."""
    merged = dict(base)
    for field in LEAD_FIELDS:
        if not merged.get(field) and extra.get(field):
            merged[field] = extra[field]
    return merged


def missing_fields(lead: dict) -> list[str]:
    return [f for f in LEAD_FIELDS if not lead.get(f)]


def build_lead(llm_lead: dict, harvested: dict, source_url: str,
               source_pages: list[str] | None = None) -> dict:
    """Combine LLM fields with harvested contacts under the verified-data policy.

    Provenance is explicit: profile fields come from the LLM ("llm");
    email/phone come ONLY from deterministic HTML harvesting — their
    provenance carries the exact source page and mechanism. scrape_page()
    has already stripped LLM email/phone, so nothing LLM-generated can
    reach the verified-only fields or their provenance columns.
    """
    lead = dict(llm_lead)
    email_pick = select_email(harvested.get("emails", []))
    phone_pick = select_phone(harvested.get("phones", []))
    lead["email"] = email_pick["value"] if email_pick else ""
    lead["phone"] = phone_pick["value"] if phone_pick else ""
    # Add social profiles
    lead["socials"] = harvested.get("socials", {})
    lead["_provenance"] = {
        "email": email_pick,   # full candidate dict or None
        "phone": phone_pick,
        "socials": "harvested" if harvested.get("socials") else "none",
        **{f: ("llm" if lead.get(f) else "none") for f in LLM_ALLOWED_FIELDS},
    }
    lead["_source_pages"] = list(source_pages or [])

    lead = clean_lead(lead)
    # Canonical website: the domain being scraped wins over LLM guesses
    lead["website"] = canonical_website(source_url, lead.get("website", ""))
    return lead


def scrape_site(url: str) -> dict:
    """Scrape a site across multiple pages until lead fields are filled.

    Harvested emails/phones are accumulated across ALL processed pages
    (homepage + contact/about/team/...) and only they may populate the
    email/phone columns.
    """
    llm_lead = {field: "" for field in LEAD_FIELDS}
    harvested = {"emails": [], "phones": [], "socials": {}}
    source_pages: list[str] = [url]

    def absorb_harvest(html: str, page_url: str) -> None:
        found = harvest_contacts(html, source_page=page_url)
        harvested["emails"] += [
            c for c in found["emails"]
            if c["value"].lower() not in (x["value"].lower() for x in harvested["emails"])
        ]
        harvested["phones"] += [
            c for c in found["phones"]
            if c["value"] not in (x["value"] for x in harvested["phones"])
        ]
        # Also harvest social profiles
        socials = harvest_socials(html)
        for platform, url in socials.items():
            if platform not in harvested["socials"]:
                harvested["socials"][platform] = url

    # Discover extra pages + harvest deterministic contacts from the homepage.
    # A failure here is non-fatal: the LLM scrape of the homepage still runs.
    extra_pages: list[str] = []
    try:
        homepage_html = fetch_html(url)
        extra_pages = discover_pages(url, homepage_html)
        absorb_harvest(homepage_html, url)
    except Exception as exc:
        print(f"    -> page discovery failed ({type(exc).__name__}), homepage only")

    # Scrape the homepage with the LLM (email/phone are stripped from its output)
    llm_lead = merge_leads(llm_lead, scrape_page(url))

    # Enrich from discovered pages until all fields are filled
    for page_url in extra_pages:
        current = build_lead(llm_lead, harvested, url, source_pages)
        if not missing_fields(current):
            break
        print(f"    -> enriching from: {page_url}")
        try:
            absorb_harvest(fetch_html(page_url), page_url)
            llm_lead = merge_leads(llm_lead, scrape_page(page_url))
            source_pages.append(page_url)
        except Exception as exc:
            print(f"    -> page failed ({type(exc).__name__}: {exc}), continuing")

    # build_lead runs clean_lead() on the final merged result
    lead = build_lead(llm_lead, harvested, url, source_pages)
    if DEBUG_CONTACTS:
        print_contact_provenance(lead)
    return lead


def print_contact_provenance(lead: dict) -> None:
    """Debug output: which page and mechanism each verified contact came from."""
    for field in ("email", "phone"):
        pick = (lead.get("_provenance") or {}).get(field)
        if pick and lead.get(field):
            print(f"    Selected {field}: {pick['value']}")
            print(f"    Source page: {pick['source_page']}")
            print(f"    Source type: {pick['source_type']}")
        else:
            print(f"    Selected {field}: None")


# ---------------------------------------------------------------------------
# CSV row construction
# ---------------------------------------------------------------------------
def make_row(url: str, lead: dict | None, error: str | None) -> dict:
    """Build a full CSV row for one processed URL (new Phase 4 schema)."""
    row = {column: "" for column in CSV_COLUMNS}
    if lead:
        # Copy only declared lead fields; internal keys like _provenance stay out
        row.update({f: lead.get(f, "") for f in LEAD_FIELDS})
        row["source_pages"] = "|".join(lead.get("_source_pages", []))

        provenance = lead.get("_provenance") or {}
        for field in ("email", "phone"):
            pick = provenance.get(field)
            # Provenance only exists for harvested (never LLM) contact values
            if pick and row[field]:
                row[f"{field}_source_page"] = pick.get("source_page", "")
                row[f"{field}_source_type"] = pick.get("source_type", "")

    row["source_url"] = url
    row["scraped_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if error:
        row["status"] = "failed"
    elif lead and has_meaningful_data(lead):
        row["status"] = "success"
    else:
        row["status"] = "no_data"
    row["error"] = error or ""

    score = quality_score(lead) if (lead and not error) else 0
    row["quality_score"] = score
    row["data_quality"] = data_quality(score, row["status"])
    return row


# ---------------------------------------------------------------------------
# CSV output handling
# ---------------------------------------------------------------------------
def csv_schema_ok(path: Path) -> bool:
    """True when the CSV doesn't exist yet or its header matches CSV_COLUMNS."""
    if not path.exists():
        return True
    with path.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), [])
    return header == CSV_COLUMNS


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
# Database integration
# ---------------------------------------------------------------------------
try:
    from . import database as db
except ImportError:
    import database as db

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    if not URLS_FILE.exists():
        print(f"URL file not found: {URLS_FILE}", file=sys.stderr)
        return 1

    if not csv_schema_ok(OUTPUT_CSV):
        print(
            f"ERROR: {OUTPUT_CSV} uses an old/incompatible schema.\n"
            "The Phase 4 scraper writes a new column layout and will not mix "
            "schemas in one file.\n"
            "Back up or rename the old file first, e.g.:\n"
            "    Rename-Item data\\leads.csv leads_old_schema_backup.csv\n"
            "then re-run the scraper.",
            file=sys.stderr,
        )
        return 1

    urls = load_urls(URLS_FILE)
    if not urls:
        print(f"No URLs found in {URLS_FILE}", file=sys.stderr)
        return 1

    already_scraped = load_already_scraped(OUTPUT_CSV)

    total = len(urls)
    successful = 0
    no_data = 0
    failed = 0
    skipped = 0

    for i, url in enumerate(urls, start=1):
        if url.rstrip("/").lower() in already_scraped:
            skipped += 1
            print(f"[{i}/{total}] Skipped (already scraped): {url}")
            continue

        print(f"[{i}/{total}] Scraping: {url}")
        try:
            lead = scrape_site(url)
        except Exception as exc:
            failed += 1
            error = f"{type(exc).__name__}: {exc}"
            append_row(OUTPUT_CSV, make_row(url, None, error))
            print(f"[{i}/{total}] Failed: {url}")
            print(f"Error: {error}")
            continue

        row = make_row(url, lead, None)
        append_row(OUTPUT_CSV, row)
        # Persist to SQLite if enabled (always enabled now).  Errors are
        # caught and logged, but they cannot invalidate the CSV row.
        try:
            db.upsert_lead(lead)
        except Exception as e:
            print(f"\n--- DATABASE ERROR ---", file=sys.stderr)
            print(f"Could not persist lead for {url}: {e}", file=sys.stderr)
        if row["status"] == "success":
            successful += 1
            print(f"[{i}/{total}] Completed successfully "
                  f"(quality: {row['quality_score']} {row['data_quality']})")
        else:
            no_data += 1
            print(f"[{i}/{total}] Completed, but no lead data found")

    print("\n--- SCRAPING SUMMARY ---")
    print(f"Total URLs: {total}")
    print(f"Successful with data: {successful}")
    print(f"No data found: {no_data}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print(f"Output: data/leads.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())

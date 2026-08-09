# Upwork Scraper Service (Selenium implementation)

"""upwork_scraper_service

Replaces the Apify‑based implementation with a Selenium‑driven scraper that
mirrors the behaviour of the original *UpworkScraper* repository.

The service returns a **list of dictionaries** where each dict matches the
structure produced by ``utils/job_helpers.parse_job_details``:

```python
{
    "posted_date": datetime,        # when the job was posted
    "job_title": str,
    "job_description": str,
    "job_proposals": str,
    "job_tags": str,               # JSON‑encoded list of skill strings
    "job_id": str,                 # stable identifier (cipher or MD5 hash)
    "job_url": str,                # URL of the Upwork job posting
}
```

The surrounding ``OpportunityProvider`` (or ``OpportunityEngine``) can map these
keys to its own domain model – the service does **not** touch the repository
layer, the Flask API, or the React frontend.
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
load_dotenv()

# Selenium / undetected‑chromedriver imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# Local helper functions from the original UpworkScraper (copied verbatim)
import hashlib
import re
from urllib.parse import unquote

# ---------------------------------------------------------------------------
# Helper utilities – same as utils/job_helpers.py (kept locally to avoid a new
# import path).
# ---------------------------------------------------------------------------

def extract_job_id_from_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    # Upwork URLs usually end with "_~<cipher>"
    match = re.search(r"_~([a-f0-9]+)", url)
    return match.group(1) if match else None


def extract_title_from_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        # Example: https://www.upwork.com/jobs/Software-Ai-Developer_~01abcd...
        path = url.split("/jobs/")[-1]
        slug = path.split("_~")[0]
        return unquote(slug.replace("-", " "))
    except Exception:
        return None


def generate_job_id(job_title: str, job_url: Optional[str] = None, job_description: str = "") -> str:
    cipher = extract_job_id_from_url(job_url)
    if cipher:
        return cipher
    # Fallback: deterministic hash of title+description
    content = f"{job_title.lower()}|{job_description[:100].lower()}"
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def calculate_posted_datetime(timestamp: str) -> datetime:
    now = datetime.now()
    t = timestamp.lower()
    try:
        if "just now" in t:
            return now
        if "yesterday" in t:
            return now - timedelta(days=1)
        if "hour" in t:
            hrs = int(re.findall(r"\d+", timestamp)[0])
            return now - timedelta(hours=hrs)
        if "day" in t:
            days = int(re.findall(r"\d+", timestamp)[0])
            return now - timedelta(days=days)
        if "last week" in t:
            return now - timedelta(weeks=1)
        if "week" in t:
            weeks = int(re.findall(r"\d+", timestamp)[0])
            return now - timedelta(weeks=weeks)
        if "minute" in t:
            mins = int(re.findall(r"\d+", timestamp)[0])
            return now - timedelta(minutes=mins)
    except Exception:
        pass
    return now


def clean_job_proposals(job_proposals_text: str) -> str:
    if not job_proposals_text:
        return ""
    if "freelancers" in job_proposals_text:
        return job_proposals_text.replace("Proposals: ", "").split(" Nu")[0].strip()
    if " ago" in job_proposals_text:
        return ""
    cleaned = (
        job_proposals_text.replace("Proposals: ", "")
        .replace("Load More Jobs", "")
        .replace("Featured", "")
    )
    return cleaned.strip()


def clean_skills(skills: List[str]) -> List[str]:
    cleaned = []
    exclude = [
        "more",
        "Next skills. Update list",
        "Skip skills",
        "  Payment verified",
        "  Payment unverified",
        "Skills",
        "Verified",
        "Payment verified",
        "Payment unverified",
    ]
    for s in skills:
        s = s.strip()
        if not s or s in exclude:
            continue
        if "Rating is" in s or "$" in s:
            continue
        cleaned.append(s)
    return cleaned


def parse_job_details(r: List[str], job_url: Optional[str] = None) -> Dict[str, Any]:
    """Parse a raw list of strings (one job posting) into a structured dict.

    The algorithm is a verbatim copy of the one shipped with the original
    *UpworkScraper* repository – it relies only on heuristics and the optional
    ``job_url`` for better title extraction.
    """
    if not r:
        return {
            "posted_date": datetime.now(),
            "job_title": "",
            "job_description": "",
            "job_proposals": "",
            "job_tags": json.dumps([]),
            "job_id": generate_job_id("", job_url),
            "job_url": job_url or "",
        }

    # -------------------------------------------------------------------
    # 1️⃣ Posted date heuristic
    # -------------------------------------------------------------------
    posted_date_str = r[0]
    time_keywords = ["ago", "yesterday", "week", "day", "hour", "minute", "just now"]
    for item in r:
        if any(kw in item.lower() for kw in time_keywords):
            posted_date_str = item
            break

    # -------------------------------------------------------------------
    # 2️⃣ Job proposals heuristic
    # -------------------------------------------------------------------
    job_proposals_text = ""
    for item in r:
        if "Proposals:" in item:
            job_proposals_text = item
            break

    # -------------------------------------------------------------------
    # 3️⃣ Job description – longest line
    # -------------------------------------------------------------------
    job_description = max(r, key=len) if r else ""

    # -------------------------------------------------------------------
    # 4️⃣ Job title – try to use URL hint first
    # -------------------------------------------------------------------
    job_title = ""
    url_title_hint = extract_title_from_url(job_url)
    if url_title_hint:
        hint_words = set(url_title_hint.lower().split())
        for item in r:
            it_clean = item.strip()
            if not it_clean or len(it_clean) > 150:
                continue
            it_words = set(it_clean.lower().split())
            if hint_words.issubset(it_words) or it_words.issubset(hint_words):
                job_title = it_clean
                break
    if not job_title:
        # Fallback – first line that looks like a title
        blacklist = [
            "•",
            "more",
            "skills",
            "verified",
            "rating is",
            "payment",
            "save job",
            "job feedback",
            "proposals:",
            "posted",
            "about \"",
        ]
        for item in r:
            it = item.strip()
            low = it.lower()
            if (
                it
                and not any(low == b or low.startswith(b) for b in blacklist)
                and not any(kw in low for kw in time_keywords)
                and len(it) < 150
            ):
                job_title = it
                break

    # -------------------------------------------------------------------
    # 5️⃣ Job tags / skills block
    # -------------------------------------------------------------------
    job_tags_list: List[str] = []
    try:
        skills_idx = -1
        for i, item in enumerate(r):
            if item.strip() == "Skills":
                skills_idx = i
                break
        if skills_idx != -1:
            end_idx = len(r)
            for i in range(skills_idx + 1, len(r)):
                if any(marker in r[i] for marker in ["Verified", "Payment", "Rating", "$", "United States"]):
                    end_idx = i
                    break
            job_tags_list = r[skills_idx + 1 : end_idx]
    except Exception:
        pass

    return {
        "posted_date": calculate_posted_datetime(posted_date_str),
        "job_title": job_title,
        "job_description": job_description,
        "job_proposals": clean_job_proposals(job_proposals_text),
        "job_tags": json.dumps(clean_skills(job_tags_list)),
        "job_id": generate_job_id(job_title, job_url, job_description),
        "job_url": job_url or "",
    }

# ---------------------------------------------------------------------------
# Selenium driver helpers – mirrors ``get_driver_with_retry`` from the original
# UpworkScraper.  They are kept private to this module because the service does
# not expose them publicly.
# ---------------------------------------------------------------------------

def _get_driver_with_retry(max_attempts: int = 3) -> Optional[webdriver.Chrome]:
    """Attempt to start a Chrome driver using the existing Windows Chrome profile.

    ``webdriver-manager`` automatically detects the locally installed Chrome
    version and downloads a matching driver binary.  The driver is launched with
    ``--user-data-dir`` pointing at the default Chrome user data directory so the
    browser re‑uses the current Windows user profile (cookies, login state, etc.).
    """
    user_data_dir = os.path.expanduser(r"%LOCALAPPDATA%\\Google\\Chrome\\User Data")
    for attempt in range(max_attempts):
        logger.debug(f"Attempt #{attempt + 1}/{max_attempts} – launching Chrome driver with user profile")
        try:
            driver_path = ChromeDriverManager().install()
            service = ChromeService(executable_path=driver_path)
            options = webdriver.ChromeOptions()
            options.add_argument(f"--user-data-dir={user_data_dir}")
            # Use the default profile; change if a named profile is required.
            options.add_argument("--profile-directory=Default")
            options.headless = False  # keep visible for manual login/debugging
            return webdriver.Chrome(service=service, options=options)
        except Exception as exc:  # pragma: no cover – only fires on driver issues
            logger.warning(f"Chrome driver launch failed on attempt {attempt + 1}: {exc}")
    logger.error("All attempts to launch Chrome driver failed")
    return None


def _login_upwork(driver: webdriver.Chrome, username: str, password: str, verification_pause: int) -> bool:
    """Perform the login steps used by the original script.

    Returns ``True`` on success, ``False`` otherwise.
    """
    try:
        # Username field (XPath taken verbatim from the original scraper)
        username_input = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "/html/body/div[3]/div/div/div/main/div/div/div[2]/div[2]/form/div/div/div[1]/div[3]/div/div/div/div/input")
            )
        )
        username_input.send_keys(username)
        # Press ENTER to move to password field (same XPath as username for consistency)
        username_input.send_keys(Keys.ENTER)
        time.sleep(4)

        password_input = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "/html/body/div[3]/div/div/div/main/div/div/div[2]/div[2]/div/form/div/div/div[1]/div[3]/div/div/div/div/input")
            )
        )
        password_input.send_keys(password)
        password_input.send_keys(Keys.ENTER)

        logger.debug(f"Pausing {verification_pause}s for credential verification")
        time.sleep(verification_pause)
        return True
    except Exception as exc:  # pragma: no cover – login failures are rare in tests
        logger.error(f"Upwork login failed: {exc}")
        return False


def _scroll_to_load_all(driver: webdriver.Chrome, user_name_indicator: str) -> bool:
    """Scroll the job list page until the footer appears.

    The original script also strips off the right‑hand user panel using
    ``user_name_indicator`` – we only need the scroll part here.
    """
    # Page‑down a few times (12 is the magic number from the original script)
    for _ in range(12):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
        time.sleep(2)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # Wait for the footer to be visible – this signals that lazy loading is done.
    timeout_wait = 120
    try:
        WebDriverWait(driver, timeout_wait).until(
            EC.visibility_of_element_located((By.TAG_NAME, "footer"))
        )
        return True
    except Exception as exc:  # pragma: no cover – only hits if Upwork changes layout
        logger.error(f"Footer not found after scrolling: {exc}")
        return False

# ---------------------------------------------------------------------------
# Service class – replaces the Apify based implementation.
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

class UpworkScraperService:
    """Selenium‑driven scraper that returns raw Upwork job dictionaries.

    The class purposefully mirrors the public signature of the previous
    ``ApifyScraperService`` implementation (``scrape_jobs``) so downstream code
    does not need to change – only the internals are swapped.
    """

    def __init__(self):
        # Configuration comes from environment variables; defaults match the
        # original repo's README example.
        self.username = os.getenv("UPWORK_USERNAME")
        self.password = os.getenv("UPWORK_PASSWORD")
        # Chrome major versions – e.g. "90,91,92" -> [90, 91, 92]
        versions = os.getenv("UPWORK_CHROME_VERSIONS", "90,91,92")
        self.chrome_versions = [int(v.strip()) for v in versions.split(",") if v.strip().isdigit()]
        self.max_driver_attempts = int(os.getenv("UPWORK_MAX_ATTEMPTS", "3"))
        self.verification_pause = int(os.getenv("UPWORK_VERIFICATION_PAUSE", "5"))
        # Upwork displays the logged‑in user name on the page; we use it to cut
        # out the sidebar that the original script removes.
        self.user_name_indicator = os.getenv("UPWORK_USER_NAME", "")

    def _collect_raw_posts(self, driver: webdriver.Chrome) -> List[Dict[str, Any]]:
        """Extract raw job text blocks and their URLs from the currently loaded page.

        Returns a list of dictionaries ``{"text": <raw block>, "url": <job url>}``.
        """
        # -------------------------------------------------------------------
        # 1️⃣ Locate the container that holds all jobs. The original XPath is
        #    very specific; we keep it to stay faithful to the reference
        #    implementation.
        # -------------------------------------------------------------------
        container_xpath = (
            "/html/body/div[3]/div/div/div[1]/div[2]/div/div/main/div"
        )
        containers = driver.find_elements(By.XPATH, container_xpath)
        if not containers:
            logger.error("Job container not found on the Upwork page")
            return []
        raw_text = containers[-1].text

        # -------------------------------------------------------------------
        # 2️⃣ Strip the right‑hand user panel using ``self.user_name_indicator``
        #    (if provided) and the "Ordered by most relevant." banner.
        # -------------------------------------------------------------------
        if self.user_name_indicator:
            raw_text = raw_text.split(self.user_name_indicator)[0]
        raw_text = raw_text.split("Ordered by most relevant.")[-1]

        # -------------------------------------------------------------------
        # 3️⃣ Split into individual postings. The original script uses the word
        #    "Posted" as a delimiter.
        # -------------------------------------------------------------------
        job_posts = raw_text.split("Posted")[1:]

        # -------------------------------------------------------------------
        # 4️⃣ Collect the URLs that correspond to each posting.  The ordering
        #    of ``job_posts`` and ``job_urls`` matches in the original scraper,
        #    so we rely on that alignment.
        # -------------------------------------------------------------------
        url_elements = driver.find_elements("xpath", "//a[contains(@href, '/jobs/')]")
        job_urls = [
            el.get_attribute("href").split("/?")[0]
            for el in url_elements
            if all(x not in el.get_attribute("href") for x in ["ontology_skill_uid", "search/saved", "search/jobs/saved"])
        ]

        # Zip together, guarding against length mismatches.
        combined: List[Dict[str, Any]] = []
        for idx, post in enumerate(job_posts):
            url = job_urls[idx] if idx < len(job_urls) else ""
            combined.append({"raw": post, "url": url})
        return combined

    def scrape_jobs(
        self,
        keywords: List[str] | None = None,
        max_results: int = 20,
        location: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Public entry point – returns a list of **raw** job dictionaries.

        Parameters are kept for API compatibility with the previous Apify
        implementation, but only ``keywords`` are used to build the search URL.
        ``max_results`` and ``location`` are currently ignored because the
        original Selenium flow scrapes the *default* Upwork job feed.
        """
        # -------------------------------------------------------------------
        # 1️⃣ Build the search URL – the original script navigates to the
        #    generic Upwork job discovery page after login.  We replicate that by
        #    constructing a URL with the supplied keywords.
        # -------------------------------------------------------------------
        base_search = "https://www.upwork.com/ab/jobs/search/"
        query = "+".join(keywords) if keywords else ""
        search_url = f"{base_search}?q={query}" if query else base_search

        driver = _get_driver_with_retry(self.max_driver_attempts)
        if not driver:
            logger.error("Unable to obtain a Selenium driver – aborting scrape")
            return []

        try:
            # ----------------------------------------------------------------
            # 2️⃣ Login flow (username / password)
            # ----------------------------------------------------------------
            driver.get("https://www.upwork.com/ab/account-security/login")
            if not self.username or not self.password:
                logger.error("UPWORK_USERNAME / UPWORK_PASSWORD env vars not set")
                return []
            if not _login_upwork(driver, self.username, self.password, self.verification_pause):
                logger.error("Login failed – cannot continue scraping")
                return []

            # ----------------------------------------------------------------
            # 3️⃣ Navigate to the search page (or stay on the dashboard if no
            #    keywords are supplied).
            # ----------------------------------------------------------------
            driver.get(search_url)
            if not _scroll_to_load_all(driver, self.user_name_indicator):
                logger.warning("Scrolling may not have loaded all jobs")

            # ----------------------------------------------------------------
            # 4️⃣ Extract raw text blocks + URLs.
            # ----------------------------------------------------------------
            raw_items = self._collect_raw_posts(driver)

            # ----------------------------------------------------------------
            # 5️⃣ Parse each block using the shared ``parse_job_details`` helper.
            # ----------------------------------------------------------------
            parsed_jobs: List[Dict[str, Any]] = []
            for item in raw_items:
                lines = item["raw"].split("\n")
                job = parse_job_details(lines, job_url=item["url"])
                parsed_jobs.append(job)
                if max_results and len(parsed_jobs) >= max_results:
                    break

            logger.info(f"Scraped {len(parsed_jobs)} Upwork jobs")
            return parsed_jobs
        finally:
            # Ensure the browser quits even if an exception bubbles up.
            try:
                driver.quit()
            except Exception:
                pass

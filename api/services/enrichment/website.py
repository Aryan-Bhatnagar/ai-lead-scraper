import os
import re
import requests
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from scrapegraphai.graphs import SmartScraperGraph
from .base import BaseEnrichmentProvider, ProviderResponse

class WebsiteParser:
    """Deterministic parser for extracting structural and technical data from HTML."""

    SOCIAL_PATTERNS = {
        "linkedin": re.compile(r"https?://(www\.)?linkedin\.com/(company|in)/[a-zA-Z0-9_-]+", re.I),
        "facebook": re.compile(r"https?://(www\.)?facebook\.com/[a-zA-Z0-9_-]+", re.I),
        "instagram": re.compile(r"https?://(www\.)?instagram\.com/[a-zA-Z0-9_-]+", re.I),
        "twitter": re.compile(r"https?://(www\.)?(twitter\.com|x\.com)/[a-zA-Z0-9_-]+", re.I),
        "youtube": re.compile(r"https?://(www\.)?youtube\.com/(channel|c|user)/[a-zA-Z0-9_-]+", re.I),
    }

    @staticmethod
    def parse(html: str, url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        # 1. Metadata
        title = soup.title.string.strip() if soup.title else None
        meta_desc = soup.find("meta", attrs={"name": "description"})
        meta_description = meta_desc["content"].strip() if meta_desc and meta_desc.has_attr("content") else None
        favicon = soup.find("link", rel=re.compile(r"icon", re.I))
        favicon_url = favicon["href"] if favicon and favicon.has_attr("href") else None
        lang = soup.find("html").get("lang") if soup.find("html") else None

        # 2. Social Links
        social_links = {}
        all_links = [a["href"] for a in soup.find_all("a", href=True)]
        for platform, pattern in WebsiteParser.SOCIAL_PATTERNS.items():
            for link in all_links:
                if pattern.search(link):
                    social_links[platform] = link
                    break

        # 3. Technical Signals
        cms = "unknown"
        if "wp-content" in html or "wp-includes" in html:
            cms = "wordpress"
        elif "cdn.shopify.com" in html or "Shopify.shop" in html:
            cms = "shopify"
        elif "wixsite.com" in html or "wix.com" in html:
            cms = "wix"

        analytics = []
        if "googletagmanager.com" in html or "google-analytics.com" in html:
            analytics.append("google_analytics")

        framework = "unknown"
        if "__NEXT_DATA__" in html:
            framework = "nextjs"
        elif "react" in html.lower() and "window.React" in html:
            framework = "react"

        # 4. Key Pages
        pages = {"contact_page": None, "about_page": None, "careers_page": None}
        for link_tag in soup.find_all("a", href=True):
            href = link_tag["href"].lower()
            text = link_tag.get_text().lower()
            if "contact" in href or "contact" in text:
                pages["contact_page"] = link_tag["href"]
            elif "about" in href or "about" in text:
                pages["about_page"] = link_tag["href"]
            elif "career" in href or "job" in href or "career" in text:
                pages["careers_page"] = link_tag["href"]

        return {
            "metadata": {
                "title": title,
                "meta_description": meta_description,
                "favicon": favicon_url,
                "language": lang,
            },
            "social_links": social_links,
            "technical_signals": {
                "cms": cms,
                "analytics": analytics,
                "framework": framework,
            },
            "pages": pages,
        }

class WebsiteEnrichmentProvider(BaseEnrichmentProvider):
    """Enrichment provider using a hybrid of BeautifulSoup and ScrapeGraphAI."""

    def __init__(self):
        self.graph_config = {
            "llm": {
                "model": os.getenv("SCRAPEGRAPH_MODEL", "ollama/llama3.2"),
                "temperature": 0,
                "format": "json",
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            },
            "headless": True,
            "verbose": False
        }
        if os.getenv("AI_INTELLIGENCE_PROVIDER") == "openai":
            self.graph_config["llm"] = {
                "model": "gpt-4o",
                "temperature": 0,
                "api_key": os.getenv("OPENAI_API_KEY"),
            }

    def fetch_data(self, lead_id: int, website: str, company_name: str) -> ProviderResponse:
        if not website:
            return ProviderResponse(data={}, status="no_data", error="No website URL provided")

        try:
            # Stage 1: Deterministic Extraction
            response = requests.get(website, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            html_content = response.text
            structural_data = WebsiteParser.parse(html_content, website)

            # Stage 2: Semantic Extraction
            extraction_prompt = (
                f"Analyze the website for {company_name}. Extract the following as a JSON object: "
                "- company_summary: A concise 2-sentence description of what they do. "
                "- services: A list of core services they offer. "
                "- products: A list of primary products. "
                "- target_audience: Who their ideal customers are. "
                "- business_model: How they operate (e.g. Agency, SaaS, E-commerce). "
                "- tagline: Their primary marketing slogan if available. "
                "- technologies_used: List of software/tools they mention using. "
                "- pain_points: Likely operational struggles they face."
            )

            smart_scraper = SmartScraperGraph(
                prompt=extraction_prompt,
                source=website,
                config=self.graph_config
            )
            semantic_data = smart_scraper.run()
            if not isinstance(semantic_data, dict):
                semantic_data = {"raw_text": semantic_data}

            # Merge results
            final_data = {**semantic_data, **structural_data}

            return ProviderResponse(
                data=final_data,
                confidence=1.0,
                status="success"
            )
        except Exception as e:
            return ProviderResponse(
                data={},
                status="failed",
                error=str(e)
            )

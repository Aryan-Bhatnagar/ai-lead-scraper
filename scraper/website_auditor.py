"""
Technical Website Flaw Auditor.

Runs a fast 5-point automated technical audit on client business website HTML:
1. SSL Certificate check (http vs https)
2. Mobile Responsiveness check (<meta name="viewport">)
3. Missing Logo / Branding check (logo / favicon tags)
4. Missing Contact Form check (<form>, mailto:)
5. Domain Reachability check
"""

from __future__ import annotations
import re
import urllib.parse
import urllib.request
from typing import Dict, Any, List

def audit_website(url: str, html_content: str = "") -> Dict[str, Any]:
    """
    Evaluates website URL and raw HTML for technical flaws.
    Returns audit status dict with flaws list and pitch insights.
    """
    flaws: List[str] = []
    audit_results: Dict[str, Any] = {
        "url": url,
        "is_https": False,
        "has_viewport": False,
        "has_logo": False,
        "has_contact_form": False,
        "flaws": flaws,
        "pitch_snippet": ""
    }

    if not url or url == "N/A" or not url.startswith(("http://", "https://")):
        flaws.append("🚨 No Official Website Found")
        audit_results["pitch_snippet"] = "No official website found — customer trust and organic discovery are severely limited."
        return audit_results

    # 1. SSL Certificate Check
    if url.startswith("https://"):
        audit_results["is_https"] = True
    else:
        flaws.append("🔒 Unsecure HTTP (Missing SSL Certificate)")

    # If HTML content was not supplied, attempt a fast fetch
    if not html_content:
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                html_content = resp.read().decode('utf-8', errors='ignore')
        except Exception:
            flaws.append("⚠️ Website Unresponsive or Connection Timed Out")
            audit_results["pitch_snippet"] = "Website connection timed out — high bounce rate for visiting customers."
            return audit_results

    html_lower = html_content.lower()

    # 2. Mobile Viewport Check
    if '<meta name="viewport"' in html_lower or "<meta name='viewport'" in html_lower:
        audit_results["has_viewport"] = True
    else:
        flaws.append("📱 Non-Mobile Responsive (Missing Viewport Tag)")

    # 3. Branding & Logo Check
    if any(k in html_lower for k in ["logo", "favicon", "brand-mark", "header-logo"]):
        audit_results["has_logo"] = True
    else:
        flaws.append("🎨 Missing or Outdated Logo & Branding")

    # 4. Contact Form Check
    if any(k in html_lower for k in ["<form", "mailto:", "contact-form", "wpforms", "elementor-form"]):
        audit_results["has_contact_form"] = True
    else:
        flaws.append("✉️ Missing Lead Capture / Contact Form")

    # Generate custom pitch snippet based on identified flaws
    if flaws:
        audit_results["pitch_snippet"] = f"Technical flaws detected: {', '.join(flaws)}. Modern web overhaul required."
    else:
        audit_results["pitch_snippet"] = "Website passed baseline audits — ready for AI chatbot & conversion optimization."

    return audit_results

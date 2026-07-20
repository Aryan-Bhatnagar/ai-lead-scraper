"""Offline sanity tests for scrape_leads (Phase 4 schema, no network, no LLM).

Run: python scraper/test_validation.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scrape_leads as sl

failures = []


def check(label, got, expected):
    if got != expected:
        failures.append(f"FAIL: {label} -> {got!r}, expected {expected!r}")


def cand(value, source_type="mailto", source_page="https://x.com"):
    return {"value": value, "source_page": source_page, "source_type": source_type}


# =========================================================================
# Email validation (strict, deterministic)
# =========================================================================
check("valid_email '+@p.ti'", sl.valid_email("+@p.ti"), False)
check("valid_email 'bad@'", sl.valid_email("bad@"), False)
check("valid_email '@company.com'", sl.valid_email("@company.com"), False)
check("valid_email whitespace", sl.valid_email("hello @company.com"), False)
check("valid_email placeholder", sl.valid_email("test@example.com"), False)
check("valid_email file ext", sl.valid_email("image@logo.png"), False)
check("valid_email symbol-only local", sl.valid_email("+-.@p.com"), False)
check("valid_email empty domain label", sl.valid_email("a@b..com"), False)
check("valid_email numeric tld", sl.valid_email("a@b.12"), False)
check("valid_email no tld", sl.valid_email("a@b"), False)
check("valid_email malformed", sl.valid_email("not-an-email"), False)
check("valid_email noreply blocked", sl.valid_email("noreply@company.com"), False)
check("valid_email apify", sl.valid_email("hello@apify.com"), True)
check("valid_email promptcloud", sl.valid_email("marketing@promptcloud.com"), True)
check("valid_email hirinfotech", sl.valid_email("info@hirinfotech.com"), True)
check("valid_email co.uk", sl.valid_email("john.smith@company.co.uk"), True)

# =========================================================================
# Phone validation
# =========================================================================
check("valid_phone intl", sl.valid_phone("+919909990610"), True)
check("valid_phone us formatted", sl.valid_phone("(555) 123-4567"), True)
check("valid_phone 'Call Now'", sl.valid_phone("Call Now"), False)
check("valid_phone too short", sl.valid_phone("123"), False)
check("valid_phone too long", sl.valid_phone("12345678901234567890"), False)

# =========================================================================
# Contact name validation (vs company name incl. suffixes)
# =========================================================================
check("name real person", sl.valid_contact_name("John Smith", "Acme Corp"), True)
check("name 'Contact Us'", sl.valid_contact_name("Contact Us", ""), False)
check("name = company", sl.valid_contact_name("Acme Corp", "Acme Corp"), False)
check("name company+Inc", sl.valid_contact_name("PromptCloud Inc", "PromptCloud"), False)
check("name company+Pvt Ltd", sl.valid_contact_name("Acme Pvt Ltd", "Acme"), False)
check("name 'Contact us' junk", sl.valid_contact_name("Contact us", "Apify"), False)
check("name single word", sl.valid_contact_name("John", ""), False)
check("name is email", sl.valid_contact_name("john@x.com", ""), False)
check("name plain person", sl.valid_contact_name("Lorenzo Padoan", "ScrapeGraphAI"), True)

# =========================================================================
# Contact role splitting (Phase 4)
# =========================================================================
check("split comma", sl.split_contact_role("Filip Popovic, COO"), ("Filip Popovic", "COO"))
check("split dash", sl.split_contact_role("Jane Doe - Head of Sales"), ("Jane Doe", "Head of Sales"))
check("split parens", sl.split_contact_role("John Smith (CEO)"), ("John Smith", "CEO"))
check("split pipe", sl.split_contact_role("Ana Lopez | Co-Founder"), ("Ana Lopez", "Co-Founder"))
check("split vp", sl.split_contact_role("Bob Ray, Vice President"), ("Bob Ray", "Vice President"))
check("no split plain name", sl.split_contact_role("Lorenzo Padoan"), ("Lorenzo Padoan", ""))
check(
    "no split on non-role suffix",
    sl.split_contact_role("Acme, Berlin"),
    ("Acme, Berlin", ""),
)
check("looks_like_role CEO", sl.looks_like_role("CEO"), True)
check("looks_like_role Head of Sales", sl.looks_like_role("Head of Sales"), True)
check("looks_like_role city", sl.looks_like_role("Berlin"), False)

# clean_lead applies the split and fills contact_role
lead = sl.clean_lead({"company_name": "Apify", "contact_name": "Filip Popovic, COO"})
check("clean_lead split name", lead["contact_name"], "Filip Popovic")
check("clean_lead split role", lead["contact_role"], "COO")
# role dropped when no person remains
lead = sl.clean_lead({"company_name": "X", "contact_name": "Contact Us", "contact_role": "CEO"})
check("role dropped w/o name", lead["contact_role"], "")

# =========================================================================
# clean_lead — junk/invalid rejection on the Phase 4 schema
# =========================================================================
lead = sl.clean_lead({
    "company_name": "Acme", "contact_name": "Contact Us",
    "email": "bad@", "phone": "Call Now", "city": "Berlin", "website": "x",
})
check("clean_lead junk name", lead["contact_name"], "")
check("clean_lead bad email", lead["email"], "")
check("clean_lead junk phone", lead["phone"], "")
check("clean_lead keeps city", lead["city"], "Berlin")
check("clean_lead '+@p.ti'", sl.clean_lead({"company_name": "S", "email": "+@p.ti"})["email"], "")
check(
    "clean_lead 'PromptCloud Inc' as contact",
    sl.clean_lead({"company_name": "PromptCloud", "contact_name": "PromptCloud Inc"})["contact_name"],
    "",
)

# company_name migration: scrape_page maps legacy business_name answers
check("company_name in schema", "company_name" in sl.LEAD_FIELDS, True)
check("business_name gone", "business_name" in sl.LEAD_FIELDS, False)

# =========================================================================
# Verified contact data policy (LLM email/phone can never reach output)
# =========================================================================
check("LLM_ALLOWED_FIELDS excludes email", "email" in sl.LLM_ALLOWED_FIELDS, False)
check("LLM_ALLOWED_FIELDS excludes phone", "phone" in sl.LLM_ALLOWED_FIELDS, False)

# 1. Hallucinated LLM email, nothing harvested -> empty email
lead = sl.build_lead(
    {"company_name": "Apify", "email": "pb.dlzmt@uw.ur", "phone": ""},
    {"emails": [], "phones": []},
    "https://apify.com",
)
check("policy: hallucinated email dropped", lead["email"], "")

# 2. LLM email vs harvested email -> harvested wins
lead = sl.build_lead(
    {"company_name": "Acme", "email": "fake@company.com", "phone": ""},
    {"emails": [cand("hello@company.com")], "phones": []},
    "https://company.com",
)
check("policy: harvested email wins", lead["email"], "hello@company.com")

# 3. LLM phone, nothing harvested -> empty phone
lead = sl.build_lead(
    {"company_name": "Acme", "email": "", "phone": "1234567890"},
    {"emails": [], "phones": []},
    "https://company.com",
)
check("policy: LLM phone dropped", lead["phone"], "")

# 4. Harvested phone preserved, with provenance
lead = sl.build_lead(
    {"company_name": "Hir Infotech", "email": "", "phone": ""},
    {"emails": [], "phones": [cand("+919909990610", "tel", "https://hirinfotech.com")]},
    "https://hirinfotech.com",
)
check("policy: harvested phone kept", lead["phone"], "+919909990610")
check("policy: phone prov type", lead["_provenance"]["phone"]["source_type"], "tel")
check(
    "policy: phone prov page",
    lead["_provenance"]["phone"]["source_page"],
    "https://hirinfotech.com",
)

# 5. Email priority: sales@ > hello@ > contact@ > info@ > other
check(
    "policy: sales@ priority",
    sl.select_email([cand("info@company.com"), cand("hello@company.com"), cand("sales@company.com")])["value"],
    "sales@company.com",
)
check(
    "policy: hello@ over info@",
    sl.select_email([cand("info@company.com"), cand("hello@company.com")])["value"],
    "hello@company.com",
)
check(
    "policy: fallback to first",
    sl.select_email([cand("team@x.com"), cand("jobs@x.com")])["value"],
    "team@x.com",
)

# =========================================================================
# Harvesting: script/style stripped, provenance, source trust
# =========================================================================
html_hidden = """<html><head>
<style>.x{content:"style@company.com"}</style>
<script>var e="fake@random.xyz";</script>
</head><body>
<noscript>ns@company.com</noscript>
<p>Contact us at hello@company.com</p>
</body></html>"""
found = sl.harvest_contacts(html_hidden, source_page="https://c.com/contact")
values = [c["value"] for c in found["emails"]]
check("script email not harvested", "fake@random.xyz" in values, False)
check("style email not harvested", "style@company.com" in values, False)
check("noscript email not harvested", "ns@company.com" in values, False)
check("visible text email harvested", values, ["hello@company.com"])
check("visible prov type", found["emails"][0]["source_type"], "visible_text")
check("visible prov page", found["emails"][0]["source_page"], "https://c.com/contact")

found = sl.harvest_contacts('<a href="mailto:sales@company.com">Sales</a>', "https://c.com")
check("mailto prov type", found["emails"][0]["source_type"], "mailto")
check("mailto prov value", found["emails"][0]["value"], "sales@company.com")

pick = sl.select_email([
    cand("random.person@somewhere.com", "visible_text"),
    cand("team@company.com", "mailto"),
])
check("mailto beats visible_text", pick["value"], "team@company.com")
pick = sl.select_email([
    cand("sales@company.com", "visible_text"),
    cand("team@company.com", "mailto"),
])
check("mailto beats visible_text even vs sales@", pick["value"], "team@company.com")

check("suspicious: pb.dlzmt@uw.ur", sl.suspicious_visible_email("pb.dlzmt@uw.ur"), True)
check("suspicious: normal ok", sl.suspicious_visible_email("hello@apify.com"), False)
check("suspicious: person ok", sl.suspicious_visible_email("john.smith@company.co.uk"), False)
found = sl.harvest_contacts("<p>pb.dlzmt@uw.ur</p>", "https://x.com")
check("gibberish visible-text rejected", found["emails"], [])
found = sl.harvest_contacts('<a href="mailto:pb.dlzmt@uw.ur">e</a>', "https://x.com")
check("same value via mailto kept", [c["value"] for c in found["emails"]], ["pb.dlzmt@uw.ur"])

html_contacts = """<html><body>
<a href="mailto:info@acme.com">Email</a>
<a href="mailto:noreply@acme.com">No</a>
<a href="mailto:sales@acme.com">Sales</a>
<a href="tel:+1 (555) 123-4567">Call</a>
<a href="tel:CallNow">Bad</a>
<p>support@acme.com</p>
</body></html>"""
found = sl.harvest_contacts(html_contacts, source_page="https://acme.com")
check(
    "harvest emails",
    [c["value"] for c in found["emails"]],
    ["info@acme.com", "sales@acme.com", "support@acme.com"],
)
check("harvest phones", [c["value"] for c in found["phones"]], ["+1 (555) 123-4567"])
check("harvest+select email", sl.select_email(found["emails"])["value"], "sales@acme.com")

# =========================================================================
# Website canonicalization (Phase 4)
# =========================================================================
check(
    "website: hallucinated domain rejected",
    sl.canonical_website("https://scrapegraphai.com/", "https://scrapograph.ai/"),
    "https://scrapegraphai.com/",
)
check(
    "website: promptcloud unchanged",
    sl.canonical_website("https://www.promptcloud.com/", ""),
    "https://www.promptcloud.com/",
)
check(
    "website: same-domain subpage ok",
    sl.canonical_website("https://apify.com/", "https://console.apify.com/"),
    "https://console.apify.com/",
)
check(
    "website: www variant ok",
    sl.canonical_website("https://promptcloud.com/", "https://www.promptcloud.com/"),
    "https://www.promptcloud.com/",
)
check(
    "website: unrelated domain rejected",
    sl.canonical_website("https://acme.com/", "https://facebook.com/acme"),
    "https://acme.com/",
)
check(
    "website: scheme added before compare",
    sl.canonical_website("https://acme.com/", "acme.com/about"),
    "https://acme.com/about",
)

# build_lead applies canonicalization
lead = sl.build_lead(
    {"company_name": "ScrapeGraphAI", "website": "https://scrapograph.ai/"},
    {"emails": [], "phones": []},
    "https://scrapegraphai.com/",
)
check("build_lead canonical website", lead["website"], "https://scrapegraphai.com/")

# =========================================================================
# source_pages persistence (Phase 4)
# =========================================================================
lead = sl.build_lead(
    {"company_name": "Acme"},
    {"emails": [cand("info@acme.com", "mailto", "https://acme.com/contact")], "phones": []},
    "https://acme.com/",
    source_pages=["https://acme.com/", "https://acme.com/contact"],
)
row = sl.make_row("https://acme.com/", lead, None)
check("source_pages serialized", row["source_pages"], "https://acme.com/|https://acme.com/contact")
check("email prov page in CSV", row["email_source_page"], "https://acme.com/contact")
check("email prov type in CSV", row["email_source_type"], "mailto")
check("phone prov empty when none", row["phone_source_page"], "")
check("phone prov type empty when none", row["phone_source_type"], "")

# =========================================================================
# Quality scoring (Phase 4, deterministic)
# =========================================================================
full_lead = {
    "company_name": "Acme", "industry": "SaaS", "company_description": "Does things.",
    "contact_name": "John Smith", "contact_role": "CEO",
    "email": "sales@acme.com", "phone": "+15551234567",
    "website": "https://acme.com", "city": "Berlin", "country": "Germany",
}
check("score full lead", sl.quality_score(full_lead), 100)
check("score email only", sl.quality_score({"email": "a@b.com"}), 30)
check("score phone only", sl.quality_score({"phone": "+15551234567"}), 20)
check("score name+role", sl.quality_score({"contact_name": "J S", "contact_role": "CEO"}), 25)
check("score company only", sl.quality_score({"company_name": "Acme"}), 10)
check("score city+country counted once", sl.quality_score({"city": "Berlin", "country": "DE"}), 5)
check("score website contributes nothing", sl.quality_score({"website": "https://a.com"}), 0)
check(
    "score email+phone+name",
    sl.quality_score({"email": "a@b.com", "phone": "+15551234567", "contact_name": "J S"}),
    65,
)

# data_quality mapping
check("quality HIGH at 75", sl.data_quality(75, "success"), "HIGH")
check("quality HIGH at 100", sl.data_quality(100, "success"), "HIGH")
check("quality MEDIUM at 50", sl.data_quality(50, "success"), "MEDIUM")
check("quality MEDIUM at 74", sl.data_quality(74, "success"), "MEDIUM")
check("quality LOW at 20", sl.data_quality(20, "success"), "LOW")
check("quality LOW at 49", sl.data_quality(49, "success"), "LOW")
check("quality NONE at 19", sl.data_quality(19, "no_data"), "NONE")
check("quality NONE at 0", sl.data_quality(0, "no_data"), "NONE")
check("failed always NONE", sl.data_quality(90, "failed"), "NONE")

# make_row wires score + quality in
row = sl.make_row("https://acme.com/", sl.build_lead(
    full_lead, {"emails": [cand("sales@acme.com")], "phones": [cand("+15551234567", "tel")]},
    "https://acme.com/",
), None)
check("row quality_score", row["quality_score"], 100)
check("row data_quality", row["data_quality"], "HIGH")
check("row status success", row["status"], "success")

# failed row -> score 0, NONE
row = sl.make_row("https://x.com", None, "boom")
check("failed row status", row["status"], "failed")
check("failed row score", row["quality_score"], 0)
check("failed row quality", row["data_quality"], "NONE")

# website alone -> no_data, score 0, NONE
lead = sl.build_lead({}, {"emails": [], "phones": []}, "https://x.com")
row = sl.make_row("https://x.com", lead, None)
check("website-only status", row["status"], "no_data")
check("website-only score", row["quality_score"], 0)
check("website-only quality", row["data_quality"], "NONE")

# =========================================================================
# CSV schema (Phase 4)
# =========================================================================
EXPECTED_COLUMNS = [
    "company_name", "industry", "company_description", "contact_name",
    "contact_role", "email", "phone", "website", "city", "country",
    "source_url", "source_pages",
    "email_source_page", "email_source_type",
    "phone_source_page", "phone_source_type",
    "scraped_at", "status", "quality_score", "data_quality", "error",
]
check("CSV_COLUMNS exact", sl.CSV_COLUMNS, EXPECTED_COLUMNS)
row = sl.make_row("u", sl.build_lead({}, {"emails": [], "phones": []}, "u"), None)
check("row keys exactly schema", list(row.keys()), EXPECTED_COLUMNS)
check("no _provenance in row", "_provenance" in row, False)
check("no _source_pages in row", "_source_pages" in row, False)

# =========================================================================
# CSV schema compatibility guard (Phase 4)
# =========================================================================
import csv as _csv
import tempfile

with tempfile.TemporaryDirectory() as td:
    old = Path(td) / "old.csv"
    with old.open("w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["business_name", "contact_name", "email"])  # old schema
        w.writerow(["Acme", "", ""])
    check("old schema detected", sl.csv_schema_ok(old), False)

    new = Path(td) / "new.csv"
    with new.open("w", newline="", encoding="utf-8") as f:
        _csv.writer(f).writerow(sl.CSV_COLUMNS)
    check("new schema accepted", sl.csv_schema_ok(new), True)

    missing = Path(td) / "missing.csv"
    check("missing file ok", sl.csv_schema_ok(missing), True)

# =========================================================================
# Discovery ranking (unchanged behavior)
# =========================================================================
html = """<html><body>
<a href="/contact-database">Contact Database</a>
<a href="/contact-enrichment-services">Contact Enrichment</a>
<a href="/contact">Contact</a>
<a href="/about-us">About Us</a>
<a href="/team">Team</a>
</body></html>"""
pages = sl.discover_pages("https://example.org/", html)
check("discovery top is /contact", pages[0], "https://example.org/contact")
check(
    "discovery prefers exact slugs",
    pages[:3],
    ["https://example.org/contact",
     "https://example.org/about-us",
     "https://example.org/team"],
)

# =========================================================================
if failures:
    print("\n".join(failures))
    print(f"\n{len(failures)} test(s) FAILED")
    sys.exit(1)
print("All Phase 4 offline tests passed.")
# ---------- Phase 5 regression tests ----------
check("reserved .example", sl.valid_email("hello@theloremfactory.nimbuspages.example"), False)
check("reserved .invalid", sl.valid_email("test@company.invalid"), False)
check("reserved .test", sl.valid_email("test@company.test"), False)
check("reserved localhost", sl.valid_email("test@localhost"), False)
check("valid scrapegraphai", sl.valid_email("support@scrapegraphai.com"), True)
check("valid apify", sl.valid_email("hello@apify.com"), True)
check("valid promptcloud", sl.valid_email("sales@promptcloud.com"), True)
check("valid hirinfotech", sl.valid_email("info@hirinfotech.com"), True)
html_bad = '<p>contact at hello@theloremfactory.nimbuspages.example</p>'
found = sl.harvest_contacts(html_bad, source_page="https://example.com")
check("harvest filtered .example", found["emails"], [])

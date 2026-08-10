# API Documentation

Complete REST API reference for AI Lead Scraper CRM.

**Base URL:** `http://localhost:5000`
**Content-Type:** `application/json`
**CORS:** Enabled for all origins (development)

---

## Table of Contents

1. [Health Check](#health-check)
2. [Leads API](#leads-api)
3. [Discovery API](#discovery-api)
4. [Enrichment & Intelligence API](#enrichment--intelligence-api)
5. [Analytics API](#analytics-api)
6. [Recommendations API](#recommendations-api)
7. [Outreach Queue API](#outreach-queue-api)
8. [Opportunities API](#opportunities-api)
9. [Dashboard API](#dashboard-api)
10. [Scrape Jobs API](#scrape-jobs-api)
11. [Error Responses](#error-responses)

---

## Health Check

### GET /api/health

Check service health.

**Response:**
```json
{
  "status": "ok"
}
```

---

## Leads API

### GET /api/leads

List leads with filtering, sorting, and pagination.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | — | Filter by scraper status |
| `data_quality` | string | — | Filter by quality tier (HIGH/MEDIUM/LOW/NONE) |
| `lead_status` | string | — | Filter by CRM status (NEW/QUALIFIED/CONTACTED/INTERESTED/CONVERTED/REJECTED) |
| `source` | string | — | Filter by source (Apollo, Google Maps, Upwork, Google Search) |
| `sort` | string | `id` | Sort field (see valid fields below) |
| `order` | string | `desc` | `asc` or `desc` |
| `limit` | integer | `50` | Max results (max 500) |
| `offset` | integer | `0` | Pagination offset |

**Valid Sort Fields:** `id`, `company_name`, `contact_name`, `email`, `phone`, `website`, `country`, `city`, `company_size_estimate`, `source`, `opportunity_score`, `quality_score`, `data_quality`, `lead_status`, `status`, `scraped_at`, `created_at`, `updated_at`

**Response:**
```json
{
  "leads": [
    {
      "id": 1,
      "company_name": "Acme Corp",
      "contact_name": "John Doe",
      "email": "john@acme.com",
      "phone": "+1-555-0123",
      "website": "https://acme.com",
      "city": "San Francisco",
      "country": "USA",
      "source": "Google Maps",
      "opportunity_score": 78,
      "quality_score": 85,
      "data_quality": "HIGH",
      "lead_status": "NEW",
      "status": "success",
      "scraped_at": "2026-01-15T10:30:00",
      "created_at": "2026-01-15T10:30:00",
      "updated_at": "2026-01-15T10:30:00",
      "ai_summary": "Acme Corp provides...",
      "pain_points": ["Scaling infrastructure", "Hiring engineers"],
      "recommended_service": "Custom Software Development",
      "decision_maker_guess": "CTO",
      "buying_signals": ["Recent funding", "Hiring spree"],
      "outreach_strategy": "Target decision maker: CTO. Lead with BilvaLeaf Custom Software Development. Address pain point: Scaling infrastructure. Angle: Recent funding indicates budget for tools.",
      "ai_confidence": 0.85,
      "company_size_estimate": "Estimated: 50-200 employees, 127 reviews"
    }
  ],
  "count": 1
}
```

### GET /api/leads/<int:lead_id>

Get single lead by ID.

**Response:** Lead object (same as above) or 404.

### POST /api/leads

Create a new lead.

**Request Body:**
```json
{
  "source_url": "https://example.com",
  "company_name": "Example Corp",
  "website": "https://example.com",
  "email": "contact@example.com",
  "phone": "+1-555-0123",
  "city": "New York",
  "country": "USA",
  "industry": "Software",
  "company_description": "We build software...",
  "contact_name": "Jane Smith",
  "contact_role": "CEO",
  "source": "Manual"
}
```

**Required:** `source_url`

**Response:** 201 Created with lead object.

### PUT /api/leads/<int:lead_id>

Update a lead.

**Request Body:** Partial lead object (any fields except `source_url`)

**Response:** 200 OK with updated lead.

### PATCH /api/leads/<int:lead_id>/status

Update CRM lead_status.

**Request Body:**
```json
{
  "lead_status": "QUALIFIED"
}
```

**Valid Statuses:** `NEW`, `QUALIFIED`, `CONTACTED`, `INTERESTED`, `CONVERTED`, `REJECTED`

**Response:** 200 OK with updated lead.

### PATCH /api/leads/<int:lead_id>/lifecycle

Update lifecycle with validation (enforces valid transitions).

**Request Body:**
```json
{
  "lead_status": "CONTACTED"
}
```

**Valid Transitions:**
- `NEW` → `QUALIFIED`, `REJECTED`
- `QUALIFIED` → `CONTACTED`, `REJECTED`
- `CONTACTED` → `INTERESTED`, `REJECTED`
- `INTERESTED` → `CONVERTED`, `REJECTED`
- `CONVERTED` → (terminal)
- `REJECTED` → (terminal)

**Response:** 200 OK with updated lead or 400 for invalid transition.

### DELETE /api/leads/<int:lead_id>

Delete a lead.

**Response:** 200 OK with `{"deleted": true}` or 404.

### POST /api/leads/bulk

Create multiple leads.

**Request Body:**
```json
{
  "leads": [
    { "source_url": "https://a.com", "company_name": "A" },
    { "source_url": "https://b.com", "company_name": "B" }
  ]
}
```

**Response:** 201 Created with `{"lead_ids": [1,2], "count": 2}`.

### DELETE /api/leads/bulk

Delete multiple leads.

**Request Body:**
```json
{
  "lead_ids": [1, 2, 3]
}
```

**Response:** 200 OK with `{"deleted_count": 3}`.

### GET /api/leads/search

Advanced search with flexible filters.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Free text search (company, contact, website, email) |
| `company` | string | Company name filter |
| `website` | string | Website filter |
| `country` | string | Country filter |
| `city` | string | City filter |
| `min_score` | integer | Minimum opportunity_score |
| `max_score` | integer | Maximum opportunity_score |
| `quality_tier` | string | excellent/good/average |
| `source` | string | Source filter |
| `status` | string | Scraper status filter |
| `lead_status` | string | CRM status filter |
| `sort_by` | string | Sort field |
| `sort_desc` | boolean | `true`/`false` |
| `limit` | integer | Default 50 |
| `offset` | integer | Default 0 |

**Response:**
```json
{
  "leads": [...],
  "count": 10,
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

### GET /api/leads/filter

Alias for `/api/leads/search` with same functionality.

### GET /api/leads/statistics

Get lead statistics.

**Response:**
```json
{
  "total": 1500,
  "by_status": {"success": 1200, "no_data": 200, "failed": 100},
  "by_quality": {"excellent": 300, "good": 600, "average": 600},
  "by_source": {"Google Maps": 500, "Upwork": 400, "Apollo": 300, "Google Search": 300},
  "by_lifecycle": {"NEW": 800, "QUALIFIED": 300, "CONTACTED": 200, "INTERESTED": 100, "CONVERTED": 50, "REJECTED": 50},
  "avg_score": 52.3,
  "high_score_count": 180
}
```

### GET /api/leads/cities

Get unique cities for filter dropdown.

**Response:**
```json
{
  "cities": ["San Francisco", "New York", "London", "Tokyo"],
  "count": 4
}
```

---

## Discovery API

### POST /api/discover

Run full discovery pipeline using orchestrator.

**Request Body:**
```json
{
  "industry": "software development",
  "location": "San Francisco, CA",
  "max_results": 10
}
```

**Parameters:**
- `industry` (required): Industry keyword
- `location` (required): Location string
- `max_results` (optional, default 10): 1-50

**Response:**
```json
{
  "results": [
    {"title": "Acme Corp", "url": "https://acme.com", "description": "..."}
  ],
  "count": 10,
  "industry": "software development",
  "location": "San Francisco, CA"
}
```

**Process:** Creates DiscoveryQuery → DiscoveryOrchestrator → Normalization → Deduplication → Scoring → Persistence → Returns scored leads.

### POST /api/discover/google-maps

Google Maps specific discovery via Gosom scraper.

**Request Body:** Same as `/api/discover`

**Response:** Same format, source is "Google Maps".

**Note:** Requires Gosom scraper running on `http://localhost:8080`.

### POST /api/discover/free

Free web discovery (DDGS backend).

**Request Body:** Same as `/api/discover`

**Response:**
```json
{
  "results": [...],
  "count": 10,
  "industry": "...",
  "location": "...",
  "source": "free_web"
}
```

### POST /api/discover/free-and-enrich

Free discovery + immediate enrichment.

**Request Body:** Same as `/api/discover`

**Response:** Enriched leads with contact info, AI insights.

### POST /api/leads/enrich

Enrich a list of leads (website scraping).

**Request Body:**
```json
{
  "leads": [
    {"website": "https://acme.com"},
    {"website": "https://beta.com"}
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "website": "https://acme.com",
      "emails": ["contact@acme.com"],
      "phones": ["+1-555-0123"],
      "company_summary": "Acme Corp provides...",
      "services": ["Custom Software", "Consulting"],
      "socials": {"linkedin": "https://linkedin.com/company/acme"}
    }
  ],
  "count": 2
}
```

### POST /api/leads/extract-emails

Extract emails from lead websites.

**Request Body:**
```json
{
  "leads": [
    {"website": "https://acme.com"}
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "website": "https://acme.com",
      "emails": ["contact@acme.com", "support@acme.com"]
    }
  ],
  "count": 1
}
```

---

## Enrichment & Intelligence API

### POST /api/enrich/<int:lead_id>

Enrich a single lead via UnifiedEnrichmentEngine.

**Response:**
```json
{
  "status": "success",
  "profile": {
    "lead_id": 1,
    "company_name": "Acme Corp",
    "website": "https://acme.com",
    "business_details": {
      "description": "Acme Corp provides...",
      "services": ["Custom Software", "DevOps"],
      "size": "51-200"
    },
    "contact_info": {
      "emails": ["contact@acme.com"],
      "phones": ["+1-555-0123"],
      "social_links": ["https://linkedin.com/company/acme"]
    },
    "technical_signals": {
      "cms": "wordpress",
      "analytics": ["google_analytics"],
      "framework": "react"
    }
  }
}
```

### GET /api/enrich/profile/<int:lead_id>

Get stored enrichment profile.

**Response:**
```json
{
  "lead_id": 1,
  "profile": {...}
}
```

### GET /api/intelligence/<int:lead_id>

Get AI insights for a lead.

**Response:**
```json
{
  "lead_id": 1,
  "insights": {
    "company_summary": "Acme Corp is a...",
    "services_offered": ["Custom Software", "DevOps"],
    "target_customers": ["SaaS companies", "Fintech"],
    "business_model": "SaaS",
    "industry_category": "Software Development",
    "technologies_used": ["React", "Python", "AWS"],
    "pain_points": ["Scaling", "Hiring"],
    "sales_opportunities": ["Infrastructure automation", "Team augmentation"]
  }
}
```

### POST /api/intelligence/generate/<int:lead_id>

Generate AI intelligence (runs enrichment if needed).

**Response:**
```json
{
  "status": "success",
  "insights": {...}
}
```

---

## Analytics API

### GET /api/analytics/overview

Dashboard overview KPIs.

**Response:**
```json
{
  "total_leads": 1500,
  "scored_leads": 1200,
  "avg_score": 52.3,
  "high_quality_count": 300,
  "by_source": {"Google Maps": 500, "Upwork": 400, "Apollo": 300, "Google Search": 300},
  "by_quality": {"excellent": 300, "good": 600, "average": 600},
  "by_lifecycle": {"NEW": 800, "QUALIFIED": 300, "CONTACTED": 200, "INTERESTED": 100, "CONVERTED": 50, "REJECTED": 50}
}
```

### GET /api/analytics/trends

Discovery trends over time.

**Response:**
```json
{
  "daily": [
    {"date": "2026-01-10", "count": 45},
    {"date": "2026-01-11", "count": 52}
  ],
  "weekly": [
    {"week": "2026-W01", "count": 320}
  ],
  "monthly": [
    {"month": "2026-01", "count": 1250}
  ]
}
```

### GET /api/analytics/providers

Provider performance analytics.

**Response:**
```json
[
  {
    "source": "Google Maps",
    "total": 500,
    "avg_score": 58.2,
    "quality_distribution": {"excellent": 150, "good": 200, "average": 150},
    "contact_rate": 0.75
  },
  {
    "source": "Upwork",
    "total": 400,
    "avg_score": 45.1,
    "quality_distribution": {"excellent": 50, "good": 150, "average": 200},
    "contact_rate": 0.35
  }
]
```

### GET /api/analytics/quality

Quality tier breakdown.

**Response:**
```json
{
  "distribution": {"excellent": 300, "good": 600, "average": 600},
  "by_source": {
    "Google Maps": {"excellent": 150, "good": 200, "average": 150},
    "Upwork": {"excellent": 50, "good": 150, "average": 200}
  }
}
```

### GET /api/analytics/lifecycle

Lead lifecycle funnel.

**Response:**
```json
{
  "NEW": 800,
  "QUALIFIED": 300,
  "CONTACTED": 200,
  "INTERESTED": 100,
  "CONVERTED": 50,
  "REJECTED": 50
}
```

### GET /api/analytics/insights

AI-generated insights.

**Response:**
```json
{
  "top_opportunities": [
    {"lead_id": 1, "company": "Acme Corp", "score": 85, "service": "Custom Software"}
  ],
  "common_pain_points": [
    {"pain_point": "Scaling infrastructure", "count": 45},
    {"pain_point": "Hiring engineers", "count": 38}
  ],
  "recommended_services": [
    {"service": "Custom Software Development", "count": 120},
    {"service": "Cloud/DevOps", "count": 85}
  ],
  "high_confidence_leads": [
    {"lead_id": 1, "company": "Acme Corp", "confidence": 0.92}
  ]
}
```

---

## Recommendations API

### GET /api/recommendations

Get recommendations for all leads.

**Response:**
```json
[
  {
    "lead_id": 1,
    "company_name": "Acme Corp",
    "next_action": "Send personalized email referencing recent funding",
    "priority": "HIGH",
    "reasoning": "Lead has HIGH score (85), recent funding signal, decision maker identified",
    "suggested_channel": "EMAIL",
    "talking_points": ["Recent Series B funding", "Scaling challenges mentioned in blog"]
  }
]
```

### GET /api/recommendations/<int:lead_id>

Get recommendation for specific lead.

**Response:** Single recommendation object.

### GET /api/recommendations/summary

Get recommendations summary.

**Response:**
```json
{
  "total": 150,
  "by_priority": {"HIGH": 45, "MEDIUM": 65, "LOW": 40},
  "by_action": {"Email": 80, "Call": 40, "LinkedIn": 30}
}
```

---

## Outreach Queue API

### GET /api/outreach

List outreach queue entries.

**Query Parameters:**
- `lead_id` (integer) - Filter by lead
- `outreach_channel` (string) - EMAIL/WHATSAPP/CALL
- `outreach_status` (string) - PENDING/PROCESSING/SENT/FAILED/COMPLETED

**Response:**
```json
{
  "outreach": [
    {
      "id": 1,
      "lead_id": 1,
      "company_name": "Acme Corp",
      "email": "john@acme.com",
      "phone": "+1-555-0123",
      "outreach_channel": "EMAIL",
      "outreach_status": "PENDING",
      "attempt_count": 0,
      "next_follow_up_at": "2026-01-20T10:00:00",
      "created_at": "2026-01-15T10:30:00",
      "updated_at": "2026-01-15T10:30:00"
    }
  ],
  "count": 1
}
```

### POST /api/outreach

Create outreach queue entry.

**Request Body:**
```json
{
  "lead_id": 1,
  "outreach_channel": "EMAIL",
  "next_follow_up_at": "2026-01-20T10:00:00"
}
```

**Validations:**
- Lead must exist
- Lead status must be QUALIFIED or INTERESTED
- EMAIL requires lead email
- WHATSAPP/CALL requires lead phone
- No duplicate active entry for same lead+channel

**Response:** 201 Created with entry object.

### PATCH /api/outreach/<int:queue_id>

Update outreach entry.

**Request Body:**
```json
{
  "outreach_status": "SENT",
  "next_follow_up_at": "2026-01-25T10:00:00",
  "error_message": null
}
```

**Mutable Fields:** `outreach_status`, `next_follow_up_at`, `error_message`

**Response:** 200 OK with updated entry.

### DELETE /api/outreach/<int:queue_id>

Delete outreach entry (only PENDING or FAILED).

**Response:** 200 OK with `{"deleted": true}` or 400 if not deletable.

### POST /api/outreach/<int:queue_id>/dispatch

Dispatch outreach via webhook (calls OUTREACH_WEBHOOK_URL).

**Response:** Updated entry with `outreach_status: "SENT"` or error.

### POST /api/outreach/process

Process outreach batch (called by scheduler).

**Configuration (app config):**
- `OUTREACH_BATCH_LIMIT` (default 10)
- `OUTREACH_MAX_RETRY` (default 3)
- `OUTREACH_WEBHOOK_URL` (required)

**Response:**
```json
{
  "processed": 5,
  "sent": 4,
  "failed": 1,
  "errors": ["Webhook timeout for queue_id=3"]
}
```

---

## Opportunities API

### GET /api/opportunities

List opportunities with filters.

**Query Parameters:**
- `provider` - upwork/freelancer/guru/peopleperhour
- `category` - Filter by category
- `min_budget` - Minimum budget
- `max_budget` - Maximum budget
- `skills` - Comma-separated skills
- `limit` - Default 50
- `offset` - Default 0

**Response:**
```json
{
  "opportunities": [
    {
      "id": "job_123",
      "provider": "upwork",
      "project_title": "Build React Dashboard",
      "description": "We need a dashboard...",
      "budget_min": 3000,
      "budget_max": 5000,
      "currency": "USD",
      "category": "Web Development",
      "skills": ["React", "TypeScript"],
      "experience_level": "EXPERT",
      "posted_time": "2026-01-15T10:30:00",
      "client_country": "US",
      "url": "https://upwork.com/jobs/123"
    }
  ],
  "count": 1,
  "total": 500
}
```

### GET /api/opportunities/<string:opportunity_id>

Get single opportunity.

### POST /api/opportunities

Create opportunity.

### PUT /api/opportunities/<string:opportunity_id>

Update opportunity.

### DELETE /api/opportunities/<string:opportunity_id>

Delete opportunity.

---

## Dashboard API

### GET /api/dashboard/summary

Dashboard summary stats.

**Response:**
```json
{
  "total_leads": 1500,
  "new_this_week": 45,
  "qualified": 300,
  "contacted": 200,
  "converted": 50,
  "avg_score": 52.3,
  "top_sources": [
    {"source": "Google Maps", "count": 500},
    {"source": "Upwork", "count": 400}
  ],
  "recent_leads": [...]
}
```

---

## Scrape Jobs API

### GET /api/jobs

List scrape jobs.

**Response:**
```json
{
  "jobs": [
    {
      "id": 1,
      "status": "completed",
      "total_urls": 10,
      "completed_urls": 10,
      "successful_urls": 8,
      "no_data_urls": 1,
      "failed_urls": 1,
      "created_at": "2026-01-15T10:00:00",
      "started_at": "2026-01-15T10:00:05",
      "completed_at": "2026-01-15T10:05:00"
    }
  ],
  "count": 1
}
```

### POST /api/jobs

Create scrape job.

**Request Body:**
```json
{
  "urls": [
    "https://acme.com",
    "https://beta.com"
  ]
}
```

**Response:** 202 Accepted with `{"job_id": 1, "status": "queued"}`.

### GET /api/jobs/<int:job_id>

Get job status.

### GET /api/jobs/<int:job_id>/items

Get job item details.

### POST /api/discover-and-scrape

Discover leads then create scrape job.

**Request Body:**
```json
{
  "industry": "software",
  "location": "San Francisco",
  "max_results": 10
}
```

**Response:** 202 Accepted with job_id and discovered URLs.

---

## Error Responses

All errors follow this format:

```json
{
  "error": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async job) |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 405 | Method Not Allowed |
| 500 | Internal Server Error |
| 502 | Bad Gateway (webhook failure) |

### Common Error Examples

**Validation Error (400):**
```json
{"error": "Missing 'industry' field"}
```

**Not Found (404):**
```json
{"error": "Lead not found"}
```

**Invalid Transition (400):**
```json
{"error": "Invalid lifecycle transition from 'NEW' to 'CONVERTED'"}
```

**Webhook Failure (502):**
```json
{"error": "Webhook dispatch failed: Connection refused"}
```

---

## Rate Limits

No enforced rate limits in development. For production, implement:
- Flask-Limiter or similar
- Recommended: 100 req/min per IP for reads, 20 req/min for writes

---

## Authentication

**Currently:** No authentication (development mode)

**Planned for production:**
- JWT Bearer tokens
- API key header: `X-API-Key`
- Role-based access (admin, user, readonly)

---

## Webhooks

### Outreach Webhook (CRM → n8n)

**Endpoint:** `OUTREACH_WEBHOOK_URL` (configured in .env)

**Trigger:** `POST /api/outreach/<id>/dispatch` or batch processor

**Payload:**
```json
{
  "queue_id": 1,
  "lead_id": 1,
  "company_name": "Acme Corp",
  "contact_name": "John Doe",
  "contact_role": "CTO",
  "email": "john@acme.com",
  "phone": "+1-555-0123",
  "website": "https://acme.com",
  "outreach_channel": "EMAIL",
  "outreach_status": "PROCESSING"
}
```

**Expected Response:** 2xx within 10 seconds

**Retry:** Up to `OUTREACH_MAX_RETRY` times (default 3)

---

## Versioning

Current version: v1 (no version prefix in URL)

Future: `/api/v1/` prefix when breaking changes introduced.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v1 | 2026-01 | Initial API with full CRM features |

---

*API documentation generated from source code. Keep updated with implementation changes.*
# n8n Integration Handoff

**Version:** 1.0  
**Date:** 2026-08-10  
**Status:** For n8n Outreach Developer

---

## Overview

This document describes the integration between the **AI Lead Scraper CRM** (this repository) and **n8n** for outreach automation.

### Responsibility Split

| System | Owns |
|--------|------|
| **CRM (this repo)** | Lead discovery, storage, enrichment, AI scoring, quality tiering, analytics, CRM UI, lead lifecycle management |
| **n8n** | Outreach automation (Email, WhatsApp, future: LinkedIn, SMS), workflow orchestration, campaign management, delivery tracking |

---

## Current Integration State

### ✅ Implemented (CRM Side)

The CRM exposes a **complete REST API** that n8n can consume today:

| Endpoint | Method | Purpose | n8n Use Case |
|----------|--------|---------|--------------|
| `/api/leads` | GET | List leads with filters, pagination, sorting | Pull qualified leads for campaigns |
| `/api/leads/:id` | GET | Full lead details including AI insights | Get contact info, AI summary, pain points, outreach strategy for personalization |
| `/api/leads/statistics` | GET | Aggregate lead stats | Dashboard KPIs in n8n |
| `/api/leads/search` | POST | Advanced search with flexible filters | Build targeted outreach lists |
| `/api/leads/cities` | GET | Unique cities for filter dropdown | Location-based campaign segmentation |
| `/api/analytics/overview` | GET | Dashboard KPIs | Monitor lead pool health |
| `/api/analytics/providers` | GET | Provider performance | Understand lead source quality |
| `/api/outreach` | POST | Create outreach queue entry | n8n creates entries when starting campaign |
| `/api/outreach/process` | POST | Process outreach batch (calls webhook) | **CRM calls n8n webhook** — n8n implements receiver |
| `/api/outreach` | GET | List outreach entries | Sync status back to CRM |
| `/api/outreach/:id` | PATCH | Update outreach status | n8n updates SENT/FAILED/COMPLETED |
| `/api/leads/:id/lifecycle` | PATCH | Update CRM lifecycle (validated transitions) | Mark CONTACTED/INTERESTED after outreach |
| `/api/opportunities` | GET/POST | Upwork/freelance opportunities | Alternative lead source |

### 🔄 Partially Implemented (Needs n8n Side)

| Feature | CRM Status | n8n Action Required |
|---------|------------|---------------------|
| **Webhook Dispatch** | `POST /api/outreach/process` calls `OUTREACH_WEBHOOK_URL` | **Implement webhook receiver** at this URL |
| **Status Callback** | n8n can call `PATCH /api/outreach/:id` | Call after send/delivery/failure |
| **Lifecycle Sync** | n8n can call `PATCH /api/leads/:id/lifecycle` | Call when lead responds (CONTACTED→INTERESTED) |

### 📋 Future Work (Not Implemented)

| Feature | Description |
|---------|-------------|
| Campaign Management UI | CRM UI for creating/managing campaigns (backend partial) |
| Multi-channel Orchestration | Email + WhatsApp + LinkedIn sequences in n8n |
| A/B Testing | CRM doesn't track variants; n8n would manage |
| Delivery Analytics | Open/click tracking requires n8n + email provider webhooks |
| Unsubscribe Handling | CRM has no unsubscribe model yet |

---

## CRM API Endpoints for n8n

### 1. Pull Qualified Leads for Outreach

```http
GET /api/leads?lead_status=QUALIFIED&data_quality=HIGH&limit=50
```

**Response:**
```json
{
  "leads": [
    {
      "id": 123,
      "company_name": "Acme Corp",
      "contact_name": "John Doe",
      "contact_role": "CTO",
      "email": "john@acme.com",
      "phone": "+1-555-0123",
      "website": "https://acme.com",
      "city": "San Francisco",
      "country": "USA",
      "source": "Google Maps",
      "opportunity_score": 78,
      "quality_tier": "excellent",
      "ai_score": 82,
      "ai_summary": "Acme Corp provides custom software...",
      "pain_points": ["Scaling infrastructure", "Hiring engineers"],
      "buying_signals": ["Recent Series B funding", "Hiring spree"],
      "recommended_service": "Custom Software Development",
      "decision_maker_guess": "CTO",
      "outreach_strategy": "Target decision maker: CTO. Lead with BilvaLeaf Custom Software Development. Address pain point: Scaling infrastructure. Angle: Recent funding indicates budget for tools.",
      "ai_confidence": 0.85,
      "company_size_estimate": "Estimated: 50-200 employees, 127 reviews",
      "lead_status": "QUALIFIED",
      "status": "success"
    }
  ],
  "count": 1
}
```

**Recommended n8n Filter:** `lead_status=QUALIFIED` AND `data_quality in (HIGH, MEDIUM)` AND `opportunity_score >= 50`

---

### 2. Get Full Lead Details for Personalization

```http
GET /api/leads/123
```

Returns all fields above plus:
- `score_breakdown_json` — Detailed scoring explanation
- `ai_insights` — Full AI intelligence (services, target customers, tech stack, opportunities)
- `business_profile` — Website enrichment data (emails, phones, socials, tech signals)

---

### 3. Create Outreach Queue Entry

```http
POST /api/outreach
Content-Type: application/json

{
  "lead_id": 123,
  "outreach_channel": "EMAIL",
  "next_follow_up_at": "2026-08-15T10:00:00"
}
```

**Validations:**
- Lead must exist
- Lead `lead_status` must be `QUALIFIED` or `INTERESTED`
- EMAIL channel requires lead to have `email`
- WHATSAPP/CALL requires lead to have `phone`
- No duplicate active entry for same `lead_id` + `outreach_channel`

**Response:** 201 Created with queue entry including `id` (queue_id)

---

### 4. Process Outreach Batch (CRM → n8n Webhook)

**This is the primary integration point.**

```http
POST /api/outreach/process
```

**Configuration (`.env`):**
```bash
OUTREACH_WEBHOOK_URL=https://your-n8n-instance/webhook/outreach
OUTREACH_BATCH_LIMIT=10
OUTREACH_MAX_RETRY=3
```

**Behavior:**
1. CRM queries `OUTREACH_QUEUE` for entries with `outreach_status = 'PENDING'` (up to `OUTREACH_BATCH_LIMIT`)
2. For each entry, CRM sends POST to `OUTREACH_WEBHOOK_URL` with payload (see below)
3. On 2xx response: updates entry `outreach_status = 'SENT'`, increments `attempt_count`, sets `last_contacted_at`
4. On failure: increments `attempt_count`, sets `error_message`, retries up to `OUTREACH_MAX_RETRY`
5. Returns summary: `{ "processed": 5, "sent": 4, "failed": 1, "errors": [...] }`

**Trigger:** Called by:
- Manual API call from n8n (n8n calls this to start batch)
- Scheduled job (future: cron in CRM)
- Frontend "Send Outreach" button

---

### 5. Webhook Payload (CRM → n8n)

```json
{
  "queue_id": 456,
  "lead_id": 123,
  "company_name": "Acme Corp",
  "contact_name": "John Doe",
  "contact_role": "CTO",
  "email": "john@acme.com",
  "phone": "+1-555-0123",
  "website": "https://acme.com",
  "city": "San Francisco",
  "country": "USA",
  "source": "Google Maps",
  "opportunity_score": 78,
  "quality_tier": "excellent",
  "ai_score": 82,
  "ai_summary": "Acme Corp provides custom software development...",
  "pain_points": ["Scaling infrastructure", "Hiring engineers"],
  "buying_signals": ["Recent Series B funding", "Hiring spree"],
  "recommended_service": "Custom Software Development",
  "decision_maker_guess": "CTO",
  "outreach_strategy": "Target decision maker: CTO. Lead with BilvaLeaf Custom Software Development. Address pain point: Scaling infrastructure. Angle: Recent funding indicates budget for tools.",
  "ai_confidence": 0.85,
  "company_size_estimate": "Estimated: 50-200 employees, 127 reviews",
  "outreach_channel": "EMAIL",
  "outreach_status": "PROCESSING"
}
```

**n8n Must:**
- Respond 2xx within 10 seconds (configurable timeout)
- Process asynchronously if sending takes longer
- Return minimal response: `{ "success": true }` or `{ "message_id": "..." }`

---

### 6. Update Outreach Status (n8n → CRM)

After sending (or failure), n8n calls:

```http
PATCH /api/outreach/456
Content-Type: application/json

{
  "outreach_status": "SENT",
  "next_follow_up_at": "2026-08-20T10:00:00",
  "error_message": null
}
```

**Valid `outreach_status` values:** `PENDING`, `PROCESSING`, `SENT`, `FAILED`, `COMPLETED`

---

### 7. Update Lead Lifecycle (n8n → CRM)

When lead responds positively:

```http
PATCH /api/leads/123/lifecycle
Content-Type: application/json

{
  "lead_status": "CONTACTED"
}
```

**Valid Transitions (enforced by CRM):**
```
NEW → QUALIFIED, REJECTED
QUALIFIED → CONTACTED, REJECTED
CONTACTED → INTERESTED, REJECTED
INTERESTED → CONVERTED, REJECTED
CONVERTED → (terminal)
REJECTED → (terminal)
```

**Next step:** After reply → `PATCH /api/leads/123/lifecycle` with `"lead_status": "INTERESTED"`

---

### 8. Search Leads for Campaign Building

```http
POST /api/leads/search
Content-Type: application/json

{
  "search": "software",
  "quality_tier": "excellent",
  "min_score": 60,
  "source": "Google Maps",
  "country": "USA",
  "sort_by": "opportunity_score",
  "sort_desc": true,
  "limit": 100
}
```

---

## Lead Fields Available to n8n

### Core Identification
| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `id` | integer | 123 | Primary key |
| `company_name` | string | "Acme Corp" | |
| `contact_name` | string | "John Doe" | May be null |
| `contact_role` | string | "CTO" | May be null |
| `email` | string | "john@acme.com" | Business email preferred |
| `phone` | string | "+1-555-0123" | May be multiple, comma-separated |
| `website` | string | "https://acme.com" | |
| `source_url` | string | "https://maps.google.com/..." | Original discovery URL |

### Location & Source
| Field | Type | Example |
|-------|------|---------|
| `city` | string | "San Francisco" |
| `country` | string | "USA" |
| `source` | string | "Google Maps", "Apollo", "Upwork", "Google Search" |
| `discovery_date` | ISO8601 | "2026-01-15T10:30:00" |

### Scoring & Quality
| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `opportunity_score` | integer | 0-100 | Weighted composite score |
| `ai_score` | integer | 0-100 | AI enrichment quality score |
| `quality_score` | integer | 0-100 | Data completeness score |
| `quality_tier` | string | `excellent`/`good`/`average` | Three-tier model |
| `data_quality` | string | `HIGH`/`MEDIUM`/`LOW`/`NONE` | Legacy 4-tier |
| `ai_confidence` | float | 0.0-1.0 | AI insight confidence |

### AI Intelligence (Best for Personalization)
| Field | Type | Example |
|-------|------|---------|
| `ai_summary` | string | "Acme Corp provides custom software..." |
| `pain_points` | string[] | `["Scaling infrastructure", "Hiring engineers"]` |
| `buying_signals` | string[] | `["Recent Series B funding", "Hiring spree"]` |
| `recommended_service` | string | "Custom Software Development" |
| `decision_maker_guess` | string | "CTO" |
| `outreach_strategy` | string | "Target decision maker: CTO. Lead with..." |
| `company_size_estimate` | string | "Estimated: 50-200 employees, 127 reviews" |
| `technologies_used` | string[] | `["React", "Python", "AWS"]` |
| `services_offered` | string[] | `["Custom Software", "DevOps"]` |
| `target_customers` | string[] | `["SaaS companies", "Fintech"]` |
| `business_model` | string | "SaaS" |
| `industry_category` | string | "Software Development" |

### Scoring Breakdown (Advanced)
```json
{
  "score_explanation_json": "{\"breakdowns\":[{\"feature\":\"website_exists\",\"label\":\"Website\",\"weight\":15,\"quality_ratio\":1.0,\"contribution\":15.0,\"detail\":\"Has website: https://acme.com\"},...]}"
}
```

---

## Webhook Implementation Guide for n8n

### n8n Webhook Node Configuration

1. **Create Webhook Node** in n8n
2. **Webhook URL:** `https://your-n8n/webhook/outreach`
3. **HTTP Method:** POST
4. **Response Mode:** "On Received" (respond immediately)
5. **Authentication:** Add header check if needed (e.g., `X-CRM-Secret`)

### Minimal n8n Workflow

```
Webhook (POST /webhook/outreach)
  → Set: Extract lead data from webhook payload
  → IF: outreach_channel = "EMAIL"
     → Send Email (Gmail/SMTP/Mailgun node)
     → On Success: HTTP Request PATCH /api/outreach/:id {outreach_status: "SENT"}
     → On Error: HTTP Request PATCH /api/outreach/:id {outreach_status: "FAILED", error_message: "..."}
  → IF: outreach_channel = "WHATSAPP"
     → Send WhatsApp (Twilio/WA Business API node)
     → Update CRM status
  → Respond to Webhook: { "success": true }
```

### Required n8n Credentials

| Service | Credentials Needed |
|---------|-------------------|
| **Email** | SMTP/Gmail/Mailgun/SendGrid API |
| **WhatsApp** | Twilio Account SID + Auth Token, or Meta WhatsApp Business API |
| **CRM API** | None (public API, but consider adding API key header) |

### Error Handling in n8n

- **Webhook timeout:** CRM retries up to `OUTREACH_MAX_RETRY` (default 3)
- **Failed send:** n8n should catch errors, update CRM with `outreach_status: "FAILED"` and `error_message`
- **Partial success:** n8n can update individual queue entries as they complete

---

## Testing the Integration

### 1. Test Webhook Endpoint

```bash
# From CRM server (or any machine with access to n8n)
curl -X POST https://your-n8n/webhook/outreach \
  -H "Content-Type: application/json" \
  -d '{
    "queue_id": 999,
    "lead_id": 123,
    "company_name": "Test Corp",
    "contact_name": "Jane Test",
    "email": "jane@test.com",
    "outreach_channel": "EMAIL",
    "outreach_status": "PROCESSING"
  }'
```

**Expected:** 2xx response within 10s

### 2. Test Full Flow

1. Ensure CRM has leads with `lead_status=QUALIFIED` and email
2. Create outreach entry:
   ```bash
   curl -X POST http://localhost:5000/api/outreach \
     -H "Content-Type: application/json" \
     -d '{"lead_id": 123, "outreach_channel": "EMAIL"}'
   ```
3. Call batch process:
   ```bash
   curl -X POST http://localhost:5000/api/outreach/process
   ```
4. Verify n8n received webhook
5. n8n updates status via PATCH
6. Check CRM: `GET /api/outreach` shows `SENT`

### 3. Verify Lead Data Structure

```bash
curl http://localhost:5000/api/leads/123 | jq .
```

---

## Configuration Checklist

### CRM Side (`.env`)

```bash
# Required for n8n integration
OUTREACH_WEBHOOK_URL=https://your-n8n-instance/webhook/outreach
OUTREACH_BATCH_LIMIT=10
OUTREACH_MAX_RETRY=3

# Optional: Add shared secret for webhook auth
# OUTREACH_WEBHOOK_SECRET=shared-secret-here
```

### n8n Side

- [ ] Webhook URL configured and accessible from CRM network
- [ ] Webhook responds 2xx within 10 seconds
- [ ] Email/WhatsApp credentials configured
- [ ] Workflow updates CRM via PATCH `/api/outreach/:id`
- [ ] Workflow updates lead lifecycle via PATCH `/api/leads/:id/lifecycle` on reply
- [ ] Error handling returns proper status to CRM

---

## API Reference Summary

| Operation | CRM Endpoint | n8n Action |
|-----------|--------------|------------|
| Get leads for campaign | `GET /api/leads?lead_status=QUALIFIED` | Poll or trigger |
| Get lead details | `GET /api/leads/:id` | Fetch for personalization |
| Create outreach task | `POST /api/outreach` | n8n creates when campaign starts |
| Dispatch batch | `POST /api/outreach/process` | **CRM calls n8n webhook** |
| Update send status | `PATCH /api/outreach/:id` | **n8n calls CRM** |
| Update lead lifecycle | `PATCH /api/leads/:id/lifecycle` | **n8n calls CRM** on reply |
| Search/filter leads | `POST /api/leads/search` | Build targeted lists |

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Webhook 404 | Wrong URL in `.env` | Check `OUTREACH_WEBHOOK_URL` |
| Webhook timeout | n8n takes >10s | Increase CRM timeout or make n8n async |
| 401/403 from CRM | Future auth not implemented | Currently no auth; will need API key later |
| Duplicate outreach | n8n creates multiple entries | CRM prevents duplicate PENDING for same lead+channel |
| Invalid lifecycle | n8n sends wrong transition | CRM enforces valid transitions; check docs |

---

## Future Enhancements (Roadmap)

| Priority | Feature | Owner |
|----------|---------|-------|
| High | Campaign management UI in CRM | CRM Team |
| High | Webhook authentication (HMAC/API key) | Both |
| Medium | Delivery tracking (open/click) via n8n webhooks | n8n Team |
| Medium | Multi-step sequences in n8n | n8n Team |
| Low | A/B test variant tracking | Both |
| Low | Unsubscribe handling in CRM | CRM Team |

---

## Contact

- **CRM Repository:** This codebase
- **CRM API Docs:** `docs/API.md`
- **Architecture:** `docs/ARCHITECTURE.md`
- **Setup:** `docs/SETUP.md`

**Last Updated:** 2026-08-10  
**For:** n8n Outreach Automation Developer
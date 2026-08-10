# Database Handoff Document

## Overview
This document describes the complete portable backup of the AI Lead Scraper CRM database, enabling another team member to set up the project on another PC and see the EXACT SAME leads and AI-generated enrichment.

---

## Database Information

| Property | Value |
|----------|-------|
| **Database Engine** | SQLite 3 |
| **Database File** | `data/leads.db` |
| **Schema Version** | Current (no migrations needed - SQLite handles schema automatically) |
| **Backup Date** | 2026-08-10 |
| **Backup Method** | SQLite Online Backup API (consistent point-in-time snapshot) |

---

## Backup Files Created

| File | Size | SHA-256 | Description |
|------|------|---------|-------------|
| `backups/leads_backup_20260810_161421.db` | 13.16 MB (13,795,328 bytes) | `2cc683fc1b152d67a31047b6d955e09e5c719706d5824c674ea3f5f4f93a72ad` | Complete SQLite database backup |
| `backups/opportunities_backup_20260810_161421.json` | 1.7 MB | *See verification* | Opportunities/analytics data |

---

## Database Statistics (Original)

### Core Lead Data
| Metric | Count |
|--------|-------|
| **Total Leads** | 1,887 |
| **AI Enriched (ai_score > 0)** | 1,887 (100%) |
| **AI Summary Present** | 1,344 |
| **Scored Leads (quality_score > 0)** | 1,887 (100%) |
| **Opportunity Scored (opportunity_score > 0)** | 1,887 (100%) |

### Source Distribution
| Source | Count | Percentage |
|--------|-------|------------|
| Google Maps | 1,146 | 60.7% |
| Upwork | 524 | 27.8% |
| Apollo | 189 | 10.0% |
| (empty) | 20 | 1.1% |
| Google Search | 8 | 0.4% |

### Quality Tier Distribution
| Tier | Count | Percentage |
|------|-------|------------|
| Average | 1,289 | 68.3% |
| Good | 590 | 31.3% |
| Excellent | 8 | 0.4% |

### Lead Status Distribution
| Status | Count |
|--------|-------|
| NEW | 1,887 (100%) |

### Enrichment Data
| Data Type | Count |
|-----------|-------|
| Google Maps Rating | 1,174 |
| Google Maps Review Count | 1,174 |
| Social Profiles | 1,239 |
| AI Insights (separate table) | 258 |
| Business Profiles | 112 |
| Enrichment Raw Data | 173 |

### Opportunities
| Metric | Count |
|--------|-------|
| Opportunity Records (JSON) | 515 |

---

## Preserved Fields (Complete Schema)

### `leads` Table - All 42 Columns
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `company_name` | TEXT | Company name |
| `industry` | TEXT | Industry/category |
| `company_description` | TEXT | Company description |
| `contact_name` | TEXT | Contact person name |
| `contact_role` | TEXT | Contact role/title |
| `email` | TEXT | Email address |
| `phone` | TEXT | Phone number |
| `website` | TEXT | Company website |
| `city` | TEXT | City |
| `country` | TEXT | Country |
| `source_url` | TEXT | Source URL |
| `source_pages` | TEXT | Source pages JSON |
| `email_source_page` | TEXT | Email source page |
| `email_source_type` | TEXT | Email source type |
| `phone_source_page` | TEXT | Phone source page |
| `phone_source_type` | TEXT | Phone source type |
| `scraped_at` | TEXT | Scraped timestamp |
| `status` | TEXT | Scraping status |
| `quality_score` | INTEGER | Quality score (0-100) |
| `data_quality` | TEXT | Quality label (Poor/Average/Good/Excellent) |
| `error` | TEXT | Error message if any |
| `lead_status` | TEXT | Lead lifecycle status |
| `created_at` | TEXT | Creation timestamp |
| `updated_at` | TEXT | Last update timestamp |
| `quality_tier` | TEXT | Quality tier (poor/average/good/excellent) |
| `score_breakdown_json` | TEXT | Detailed score breakdown |
| `google_rating` | REAL | Google Maps rating (0-5) |
| `maps_review_count` | INTEGER | Google Maps review count |
| `categories` | TEXT | Business categories |
| `socials_json` | TEXT | Social media profiles JSON |
| `address` | TEXT | Full address |
| `source` | TEXT | Data source (Google Maps/Upwork/Apollo/Google Search) |
| `discovery_date` | TEXT | Discovery timestamp |
| `ai_score` | INTEGER | AI enrichment score |
| `ai_summary` | TEXT | AI-generated company summary |
| `recommended_service` | TEXT | AI-recommended service |
| `pain_points` | TEXT | AI-identified pain points (JSON array) |
| `company_size_estimate` | TEXT | AI-estimated company size |
| `decision_maker_guess` | TEXT | AI-guessed decision maker role |
| `ai_confidence` | REAL | AI confidence score (0-1) |
| `opportunity_score` | INTEGER | Opportunity score (0-100) |
| `score_explanation_json` | TEXT | Opportunity score explanation |
| `company_logo` | TEXT | Company logo URL |
| `buying_signals` | TEXT | AI-identified buying signals (JSON array) |
| `outreach_strategy` | TEXT | AI-generated outreach strategy |

### Related Tables
| Table | Rows | Key Fields |
|-------|------|------------|
| `ai_insights` | 258 | company_summary, services_offered, target_customers, business_model, industry_category, technologies_used, pain_points, sales_opportunities, generated_at, llm_provider |
| `business_profiles` | 112 | profile_json (full business profile), updated_at |
| `enrichment_raw_data` | 173 | provider_name, raw_payload, created_at |
| `scrape_jobs` | 0 | Job tracking (empty) |
| `scrape_job_items` | 0 | Job items (empty) |
| `outreach_queue` | 0 | Outreach tracking (empty) |

---

## AI Enrichment Fields Preserved

All AI-generated fields are preserved exactly as-is:

1. **AI Summary** (`ai_summary`) - 1,344 leads
2. **Pain Points** (`pain_points`) - JSON array of identified pain points
3. **Buying Signals** (`buying_signals`) - JSON array of buying signals
4. **Recommended Service** (`recommended_service`) - Service recommendation
5. **Decision Maker** (`decision_maker_guess`) - Guessed decision maker role
6. **Company Size** (`company_size_estimate`) - Estimated company size
7. **Technologies** (`technologies`) - Detected technologies
8. **Outreach Strategy** (`outreach_strategy`) - Custom outreach strategy
9. **AI Confidence** (`ai_confidence`) - Confidence score (0.0-1.0)
10. **AI Score** (`ai_score`) - Overall AI enrichment score
11. **Opportunity Score** (`opportunity_score`) - Opportunity scoring
12. **Score Explanation** (`score_explanation_json`) - Detailed breakdown
13. **AI Insights** (table) - 258 detailed AI analyses with services, customers, business model, etc.

---

## Restore Instructions

### Prerequisites
- Python 3.8+
- SQLite 3 (included with Python)
- Project dependencies (`pip install -r requirements.txt`)

### Method 1: Using the Restore Script (Windows PowerShell)
```powershell
# Basic restore
.\restore_database.ps1 -BackupFile "backups\leads_backup_20260810_161421.db"

# Force restore without confirmation
.\restore_database.ps1 -BackupFile "backups\leads_backup_20260810_161421.db" -Force

# Restore to custom location
.\restore_database.ps1 -BackupFile "backups\leads_backup_20260810_161421.db" -TargetPath "data\leads.db"
```

### Method 2: Manual Restore (Cross-platform)
```bash
# Backup current database (if exists)
cp data/leads.db data/leads.db.backup.$(date +%Y%m%d_%H%M%S)

# Restore from backup
cp backups/leads_backup_20260810_161421.db data/leads.db

# Restore opportunities.json
cp backups/opportunities_backup_20260810_161421.json data/opportunities.json
```

### Method 3: Using Python (Programmatic)
```python
import sqlite3
import shutil

# Using SQLite backup API for consistent restore
src = sqlite3.connect('backups/leads_backup_20260810_161421.db')
dst = sqlite3.connect('data/leads.db')
src.backup(dst)
src.close()
dst.close()
```

---

## Verification Instructions

### Automated Verification
```bash
# Verify backup matches original
python verify_database_backup.py data/leads.db backups/leads_backup_20260810_161421.db data/opportunities.json backups/opportunities_backup_20260810_161421.json
```

Expected output: **ALL CHECKS PASSED**

### Manual Verification Checklist
After restore, verify:

- [ ] Total lead count: **1,887**
- [ ] AI enriched leads: **1,887** (100%)
- [ ] AI summary present: **1,344**
- [ ] Scored leads: **1,887** (100%)
- [ ] Google Maps leads: **1,146**
- [ ] Upwork leads: **524**
- [ ] Apollo leads: **189**
- [ ] Quality tiers: Excellent=8, Good=590, Average=1289
- [ ] Google ratings: **1,174**
- [ ] Google reviews: **1,174**
- [ ] Social profiles: **1,239**
- [ ] AI insights: **258**
- [ ] Business profiles: **112**
- [ ] Enrichment raw data: **173**
- [ ] Opportunities: **515**

### Spot-Check Specific Leads
Query the restored database to verify AI fields:

```sql
-- Check AI enrichment on sample leads
SELECT id, company_name, ai_summary, ai_score, pain_points, 
       buying_signals, recommended_service, decision_maker_guess,
       company_size_estimate, ai_confidence, opportunity_score
FROM leads 
WHERE ai_summary IS NOT NULL AND ai_summary != ''
LIMIT 5;
```

---

## File Locations Summary

```
G:\ai-lead-scraper\
├── data/
│   ├── leads.db                           # Original database (13.16 MB)
│   ├── opportunities.json                 # Original opportunities (1.7 MB)
│   └── *.csv                              # Various CSV exports
├── backups/
│   ├── leads_backup_20260810_161421.db   # DATABASE BACKUP (13.16 MB)
│   └── opportunities_backup_20260810_161421.json  # OPPORTUNITIES BACKUP
├── restore_database.ps1                   # PowerShell restore script
├── verify_database_backup.py             # Python verification script
└── docs/
    └── DATABASE_HANDOFF.md               # This document
```

---

## Integrity Verification

### SHA-256 Checksums
```
leads_backup_20260810_161421.db:
2cc683fc1b152d67a31047b6d955e09e5c719706d5824c674ea3f5f4f93a72ad

opportunities_backup_20260810_161421.json:
[Run: sha256sum backups/opportunities_backup_20260810_161421.json]
```

### Verification Results
```
✓ TABLE COUNTS: All 7 tables match
✓ LEAD STATISTICS: All 7 metrics match
✓ SOURCE DISTRIBUTION: All 5 sources match
✓ QUALITY TIER DISTRIBUTION: All 3 tiers match
✓ LEAD STATUS DISTRIBUTION: All 1 status matches
✓ SAMPLE LEAD VERIFICATION: All 18 AI fields match on 5 sample leads
✓ OPPORTUNITIES.JSON: 515 records match
```

---

## Important Notes

1. **NO DATA WAS MODIFIED** - This is a pure backup/export. The production database at `data/leads.db` remains untouched.

2. **NO GITHUB COMMIT** - Backup files are in `backups/` which should be in `.gitignore`. Do NOT commit database files to GitHub.

3. **SQLITE BACKUP API** - Used SQLite's online backup API for a consistent point-in-time snapshot without locking the database.

4. **COMPLETE PRESERVATION** - All 42 columns in `leads` table + 4 related tables + opportunities.json preserved.

5. **PORTABLE** - Backup is a standard SQLite 3 database file, readable on Windows, macOS, Linux.

6. **NO MIGRATIONS NEEDED** - SQLite schema is self-contained. Just copy the `.db` file and run the application.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Database locked" | Ensure no other process is using the database. Close the application before restore. |
| "Table doesn't exist" | Run the application once to initialize schema, then restore. |
| "Permission denied" | Run PowerShell as Administrator or check file permissions. |
| "Verification fails" | Ensure you're comparing against the correct original database. |
| "AI fields empty" | Check that `ai_summary` column has data. Run verification script for details. |

---

## Support

For issues with restore or verification:
1. Run `python verify_database_backup.py` with both database paths
2. Check the detailed output for specific mismatches
3. Ensure both original and backup files exist and are accessible

---

*Generated: 2026-08-10*
*Backup ID: leads_backup_20260810_161421*
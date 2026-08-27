# 🗺️ System Architecture & 3-Tiered Extraction Diagrams

This document contains the official **Mermaid Architecture Diagrams** for the AI Lead Scraper CRM platform.

---

## 1. 🌐 Multi-Platform Lead Discovery Flowchart

```mermaid
flowchart TD
    subgraph FRONTEND ["💻 User Discovery Interface (/discover)"]
        UI["User Input: Keyword/Industry + Location"]
        PSELECT["Select Platform Providers"]
        UI --> PSELECT
    end

    subgraph ENGINE ["⚙️ Orchestration & Universal Lead Engine"]
        ROUTER{"Provider Router"}
        PSELECT --> ROUTER
    end

    subgraph PROVIDERS ["🌐 Multi-Platform Extraction Engines"]
        FL["⚡ Freelancer REST API\n- Live Projects\n- Real Budgets & Proposals\n- Must-Have Skills & Tech Stack"]
        UP["💼 Upwork Engine\n- site:upwork.com/freelance-jobs/apply\n- Individual Job Apply Links\n- Verified Budgets"]
        GU["🎯 Guru.com Engine\n- site:guru.com/jobs\n- Individual Job Posts\n- Client Project Details"]
        LK["👔 LinkedIn Jobs Engine\n- site:linkedin.com/jobs/view\n- Active Company Job Listings\n- Hiring Manager Context"]
        GM["📍 Google Maps Engine\n- Tier 1: Google Places API\n- Tier 2: SerpAPI Engine\n- Tier 3: Free Web Scraper"]
        GS["🔍 Google Web Search Engine\n- DuckDuckGo HTML Backend\n- Organic Business Websites"]
    end

    ROUTER -->|"source: freelancer"| FL
    ROUTER -->|"source: upwork"| UP
    ROUTER -->|"source: guru"| GU
    ROUTER -->|"source: linkedin"| LK
    ROUTER -->|"source: google_maps"| GM
    ROUTER -->|"source: google"| GS

    subgraph PIPELINE ["🔄 Data Standardization & Processing"]
        NORM["📐 Platform Normalizers\nConverts raw API/HTML payload to\nCanonical UnifiedLead Model"]
        AI["🤖 AI Overview & Pitch Generator\n- Pain Points\n- Recommended Pitch Angle\n- Buying Signals"]
        DEDUP{"🛡️ Deduplication Engine\nUnique constraint on\nWebsite / Source URL"}
    end

    FL --> NORM
    UP --> NORM
    GU --> NORM
    LK --> NORM
    GM --> NORM
    GS --> NORM

    NORM --> AI
    AI --> DEDUP

    subgraph STORAGE ["💾 SQLite Database & CRM Presentation"]
        DB[(data/leads.db\n'leads' Table)]
        CARDS["🎴 Discover Cards UI\n- Must-Have Skills Badges\n- Direct Job Apply Links\n- 👤 Assign Work Dropdown"]
        TABLE["📊 Prospect Database UI (/leads)\nDefault Sort: scraped_at DESC"]
    end

    DEDUP -->|"New Unique Lead"| DB
    DB --> CARDS
    DB --> TABLE

    classDef frontend fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff;
    classDef engine fill:#0f172a,stroke:#6366f1,stroke-width:2px,color:#fff;
    classDef provider fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff;
    classDef pipeline fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef storage fill:#312e81,stroke:#a855f7,stroke-width:2px,color:#fff;

    class UI,PSELECT frontend;
    class ROUTER engine;
    class FL,UP,GU,LK,GM,GS provider;
    class NORM,AI,DEDUP pipeline;
    class DB,CARDS,TABLE storage;
```

---

## 2. 📍 3-Tiered Hybrid Extraction Pipeline

```mermaid
flowchart TD
    START(["🔍 User Query: Industry + Location"]) --> CHECK1{"API Key Check:\nIs GOOGLE_PLACES_API_KEY\npresent in .env?"}

    subgraph TIER1 ["🥇 TIER 1: Official Google Places API (Highest Precision)"]
        T1_REQ["HTTP GET maps.googleapis.com/maps/api/place/textsearch"]
        T1_DET["HTTP GET /place/details (Fetch Phone & Website)"]
        T1_RES["Extract Name, Address, Phone, Website & Rating"]
        T1_REQ --> T1_DET --> T1_RES
    end

    CHECK1 -->|"YES (Key Available)"| T1_REQ
    CHECK1 -->|"NO (No Key)"| CHECK2{"API Key Check:\nIs SERPAPI_KEY\npresent in .env?"}

    T1_RES --> SUCCESS{"Leads Extracted\n> 0?"}
    SUCCESS -->|"YES"| NORM["📐 Normalize to UnifiedLead"]
    SUCCESS -->|"NO (Quota Exhausted / Error)"| CHECK2

    subgraph TIER2 ["🥈 TIER 2: SerpAPI Google Maps Engine (Secondary Fallback)"]
        T2_REQ["HTTP GET serpapi.com/search.json?engine=google_maps"]
        T2_RES["Parse local_results (Title, Address, Phone, Website)"]
        T2_REQ --> T2_RES
    end

    CHECK2 -->|"YES (Key Available)"| T2_REQ
    CHECK2 -->|"NO (No Key)"| TIER3

    T2_RES --> SUCCESS2{"Leads Extracted\n> 0?"}
    SUCCESS2 -->|"YES"| NORM
    SUCCESS2 -->|"NO (Error)"| TIER3

    subgraph TIER3 ["🥉 TIER 3: Free Native Web Scraper (Zero API Key Required - 100% Free)"]
        T3_REQ["SearchService Query:\n'{service} {location} contact phone website address'"]
        T3_FILTER["Filter Directory Noise\n(Block Yelp, YellowPages, JustDial, TripAdvisor)"]
        T3_PARSE["Regex Extraction:\n- Phone Regex (+91 / +1 / 10-digit)\n- Email Regex"]
        T3_REQ --> T3_FILTER --> T3_PARSE
    end

    T3_PARSE --> NORM
    NORM --> DB[(💾 Save to data/leads.db)]

    classDef t1 fill:#065f46,stroke:#34d399,stroke-width:2px,color:#fff;
    classDef t2 fill:#1e3a8a,stroke:#60a5fa,stroke-width:2px,color:#fff;
    classDef t3 fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#fff;
    classDef decision fill:#334155,stroke:#94a3b8,stroke-width:2px,color:#fff;
    classDef output fill:#431407,stroke:#fb923c,stroke-width:2px,color:#fff;

    class T1_REQ,T1_DET,T1_RES t1;
    class T2_REQ,T2_RES t2;
    class T3_REQ,T3_FILTER,T3_PARSE t3;
    class CHECK1,CHECK2,SUCCESS,SUCCESS2 decision;
    class START,NORM,DB output;
```

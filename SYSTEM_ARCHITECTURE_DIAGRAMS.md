# Portfolio Navigator Wizard - System Architecture Diagrams

## 1. Ticker Store Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        TICKER STORE SYSTEM                     │
└─────────────────────────────────────────────────────────────────┘

Data Sources Hierarchy:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Wikipedia     │    │   Fallback      │    │   Intelligent   │
│   Scraping      │───▶│   Lists         │───▶│   Deduplication │
│                 │    │                 │    │                 │
│ • S&P 500       │    │ • 500+ S&P      │    │ • Keep all S&P  │
│ • NASDAQ 100    │    │ • 100+ NASDAQ   │    │ • Add unique    │
│ • Dow 30        │    │ • 30+ Dow       │    │   NASDAQ/Dow    │
│ • ETFs          │    │ • 15+ ETFs      │    │ • Final: ~600   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDATION & CACHING                        │
│ • Format validation (≤6 chars, alphanumeric)                   │
│ • Special char handling (BRK.B → BRK-B)                        │
│ • LRU caching with @lru_cache()                                │
│ • Error handling with multiple retry attempts                  │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Enhanced Data Fetcher Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENHANCED DATA FETCHER                       │
└─────────────────────────────────────────────────────────────────┘

Request Flow:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Request   │───▶│ Cache Check │───▶│ Cache Hit   │───▶│   Response  │
│             │    │             │    │ (instant)   │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
                   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                   │ Cache Miss  │───▶│ API Fetch   │───▶│ Cache Store │
                   │             │    │             │    │             │
                   └─────────────┘    └─────────────┘    └─────────────┘

API Fetching Process:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Daily Quota    │───▶│  Rate Limiting  │───▶│ Yahoo Finance   │
│  Check (2000)   │    │ (1.2-2.5s)      │    │ API Call        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Data Validation│    │ Company Info    │    │  Cache Storage  │
│ • Min 12 months │    │ Fetch           │    │ • Gzip compress │
│ • No zero prices│    │ • Sector        │    │ • 28-day TTL    │
│ • <20% missing  │    │ • Industry      │    │ • Auto-metrics  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 3. Full-Dev Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FULL-DEV WORKFLOW                       │
└─────────────────────────────────────────────────────────────────┘

Phase 1: Pre-Startup
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  make check-    │───▶│ RedisFirstData  │───▶│ Cache Status    │
│  cache          │    │ Service         │    │ Validation      │
└─────────────────┘    └─────────────────┘    └─────────────────┘

Phase 2: Backend Startup (Port 8000)
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND SERVICES                            │
│                                                                 │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│ │Application  │  │RedisFirst   │  │Portfolio    │  │Enhanced │ │
│ │Lifespan     │  │DataService  │  │Analytics    │  │Generator│ │
│ │Manager      │  │(Global)     │  │             │  │         │ │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
│                                                                 │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│ │Redis        │  │Strategy     │  │Auto         │  │Auto     │ │
│ │Portfolio    │  │Portfolio    │  │Regeneration │  │Refresh  │ │
│ │Manager      │  │Optimizer    │  │Service      │  │Service  │ │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘

Phase 3: Frontend Startup (Port 8080)
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ React Frontend  │───▶│ Vite Dev Server │───▶│ API Integration │
│                 │    │                 │    │ (Backend:8000)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘

Phase 4: Optional Ticker Table (Port 8081)
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Ticker Table    │───▶│ Consolidated    │───▶│ Enhanced Data   │
│ Server          │    │ Table Server    │    │ Fetcher         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 4. System Interconnections

```
┌─────────────────────────────────────────────────────────────────┐
│                    SYSTEM INTERCONNECTIONS                     │
└─────────────────────────────────────────────────────────────────┘

Direct Connections:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Frontend   │◄──►│   Backend   │◄──►│    Redis    │
│  (8080)     │    │   API       │    │  Database   │
│             │    │   (8000)    │    │   (6379)    │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Ticker Table│◄──►│ Enhanced    │◄──►│ Data        │
│ (8081)      │    │ Data Fetcher│    │ Validation  │
└─────────────┘    └─────────────┘    └─────────────┘

Data Flow:
User Request → Portfolio Router → Enhanced Portfolio Generator →
Portfolio Stock Selector → Enhanced Data Fetcher → Portfolio Analytics →
Response Generation → Frontend Update

Cache Strategy:
Request → Redis Cache Check → Cache Hit (instant) OR Cache Miss (API fetch) → Cache Storage
```

## 5. Rate Limiting System

```
┌─────────────────────────────────────────────────────────────────┐
│                      RATE LIMITING SYSTEM                     │
└─────────────────────────────────────────────────────────────────┘

Yahoo Finance:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Request     │───▶│ Random      │───▶│ API Call    │
│             │    │ Delay       │    │             │
│             │    │ (1.2-2.5s)  │    │             │
└─────────────┘    └─────────────┘    └─────────────┘

Alpha Vantage:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Request     │───▶│ Fixed       │───▶│ API Call    │
│             │    │ Delay       │    │             │
│             │    │ (12s)       │    │             │
└─────────────┘    └─────────────┘    └─────────────┘

Daily Quota Management:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Daily       │───▶│ Request     │───▶│ Quota       │
│ Counter     │    │ Tracking    │    │ Check       │
│ (2000 max)  │    │             │    │ (2000/day)  │
└─────────────┘    └─────────────┘    └─────────────┘
```

## 6. Data Quality Validation

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA QUALITY VALIDATION                     │
└─────────────────────────────────────────────────────────────────┘

Validation Steps:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Min Data    │───▶│ Price       │───▶│ Missing     │───▶│ Price       │
│ Points      │    │ Validation  │    │ Values      │    │ Variation   │
│ (≥12 months)│    │ (>0)        │    │ (<20%)      │    │ Check       │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
         │                   │                   │                   │
         ▼                   ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDATION RESULT                           │
│ • Pass: Data cached and metrics calculated                     │
│ • Fail: Data rejected, error logged                           │
└─────────────────────────────────────────────────────────────────┘
```

## 7. Performance Improvements

```
┌─────────────────────────────────────────────────────────────────┐
│                    PERFORMANCE IMPROVEMENTS                    │
└─────────────────────────────────────────────────────────────────┘

Before vs After:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Startup     │    │ Data        │    │ Cache       │
│ Time        │    │ Loading     │    │ Strategy    │
│ 5-10 min    │───▶│ On-demand   │───▶│ Redis-first │
│             │    │ Lazy init   │    │ Sub-5ms     │
└─────────────┘    └─────────────┘    └─────────────┘

Key Optimizations:
• Lazy Stock Selection: Data loads only when needed
• Cache-First Strategy: Redis check before API calls
• Intelligent Fallbacks: Multiple data sources
• Rate Limiting: Prevents API blocks
• Data Validation: Ensures quality
• Compression: Gzip for storage efficiency
```

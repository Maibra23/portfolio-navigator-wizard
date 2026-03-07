# Documentation Review & Cleanup Recommendations

**Date:** 2026-03-06
**Total Files Reviewed:** 40 markdown files

---

## Accuracy of doc mentions

Verified 2026-03-06: All file paths in this review exist. Root PORTFOLIOS_IN_REDIS.md is the latest (mtime) and is the one written by backend/utils/redis_portfolio_manager.py (project_root). backend/ and backend/scripts/ copies are older duplicates. .claude file is "project overview.md" (space in name; cleanup command uses escaped space). Frontend paths: frontend/src/components/wizard/ for API-DOCUMENTATION.md and SPRINT-2-INTEGRATION-VERIFICATION.md.

---

## Summary

| Category | Count | Action |
|----------|-------|--------|
| Essential - Keep | 12 | Maintain and update |
| Reference - Keep | 7 | Keep (incl. BACKEND_PERFORMANCE_INVESTIGATION, REDIS_MEMORY_ANALYSIS) |
| Outdated - Remove | 11 | Delete (superseded or completed) |
| Duplicates - Remove | 2 | Delete backend + backend/scripts copies only |
| One-time Analysis - Remove | 4 | Delete or archive |
| Feature Docs - Review | 5 | See recommendations below |

---

## KEEP - Essential Documentation (12 files)

These files are critical for understanding and operating the project.

| File | Location | Purpose | Status |
|------|----------|---------|--------|
| README.md | root | Project overview | Current |
| RISK_PROFILE_SYSTEM.md | root | Core feature documentation | Current |
| RISK_PROFILING_QUESTIONNAIRE_AND_LOGIC.md | root | Scoring logic documentation | Current |
| DEPLOYMENT_OPERATIONS.md | docs/ | Operations runbook | Current |
| SEARCH_OPTIMIZATION.md | docs/ | Search performance docs | **Updated 2026-03-06** |
| INFRASTRUCTURE_AND_COSTS.md | docs/ | Cost analysis | **New 2026-03-06** |
| REDIS_ARCHITECTURE.md | docs/ | Redis data flow | Current |
| DATA_DICTIONARY.md | docs/ | Redis key reference | Current |
| DATA_SOURCES_AND_METHODOLOGY.md | docs/ | Data provenance | Current |
| BACKEND_UTILS_REFERENCE.md | docs/ | Developer reference | Current |
| TICKER_UPDATE_WORKFLOW.md | root | Operations reference | Current |
| backend/scripts/README.md | backend/scripts/ | Scripts documentation | Current |

---

## KEEP - Reference Documentation (5 files)

Useful for specific features or edge cases.

| File | Location | Purpose | Notes |
|------|----------|---------|-------|
| DECISION_FRAMEWORK_FLOW.md | root | User journey flowchart | Keep for UX reference |
| OPTIMIZE_BUTTON_FLOW.md | root | Feature documentation | Keep for feature reference |
| THEME_SWITCHING_GUIDE.md | root | Theme system docs | Keep if using themes |
| MOBILE_LANDSCAPE_HINT_IMPLEMENTATION.md | docs/ | Mobile UX feature | Keep for feature reference |
| PURE_STRATEGY_PORTFOLIOS.md | docs/ | Strategy logic docs | Keep for feature reference |
| BACKEND_PERFORMANCE_INVESTIGATION.md | docs/ | Health check, Fly config, Redis latency | Keep for ops/troubleshooting |
| REDIS_MEMORY_ANALYSIS.md | docs/ | Key namespaces, size estimates | Keep; add caveat re Redis Cloud vs 256MB local |

---

## REMOVE - Outdated Documentation (11 files)

These files reference old infrastructure or completed migrations.

| File | Location | Reason | Action |
|------|----------|--------|--------|
| RAILWAY_DEPLOYMENT_GUIDE.md | root | **Now using Fly.io** | DELETE |
| PRE_DEPLOYMENT_CHECKLIST.md | root | Railway-specific | DELETE |
| TESTING_SUMMARY.md | root | Old testing summary | DELETE |
| REDIS_CONFIGURATION_GUIDE.md | root | Outdated Redis config | DELETE |
| REDIS_SECURITY_ASSESSMENT.md | root | Old security review | DELETE |
| PROMETHEUS_GRAFANA_SETUP.md | root | Not currently in use | DELETE |
| SUPABASE_INTEGRATION_PLAN.md | root | Plan not implemented | DELETE |
| Upstash-to-redis.md | root | Migration completed | DELETE |
| docs/Upstash-console.md | docs/ | Migration completed | DELETE |
| QUICK_REFERENCE.md | root | Theme sprint reference | DELETE |
| .claude/project overview.md | .claude/ | Outdated project overview | DELETE |

---

## REMOVE - Duplicate Files (2 files to delete)

Same content in multiple locations. Root is the canonical location: backend/utils/redis_portfolio_manager.py writes to project root.

| File | Location | Action |
|------|----------|--------|
| PORTFOLIOS_IN_REDIS.md | root | **KEEP** (latest; code writes here) |
| PORTFOLIOS_IN_REDIS.md | backend/ | DELETE (duplicate) |
| PORTFOLIOS_IN_REDIS.md | backend/scripts/ | DELETE (duplicate) |

**Note:** Keep only root. Delete backend/ and backend/scripts/ copies. Regenerate on-demand via backend if needed.

---

## REMOVE - One-time Analysis (4 files)

Historical investigation/analysis with limited ongoing value.

| File | Location | Reason |
|------|----------|--------|
| BACKEND-UPGRADE-REPORT.md | root | Historical upgrade report |
| PROJECT_COMPLETE_ANALYSIS.md | docs/ | One-time analysis |
| RISK_PROFILE_CONSTRAINTS_ANALYSIS.md | root | Analysis complete, issues fixed |
| PORTFOLIO_POSITION_ANALYSIS.md | root | One-time analysis |

**Keep:** BACKEND_PERFORMANCE_INVESTIGATION.md (docs/) — operational value: health check config, Fly.toml, Redis latency, mobile UX; useful for troubleshooting and tuning.

---

## REVIEW - Feature/Sprint Documentation (5 files)

| File | Location | Recommendation |
|------|----------|-----------------|
| API-DOCUMENTATION.md | frontend/src/components/wizard/ | Keep if API docs are maintained; else remove |
| SPRINT-2-INTEGRATION-VERIFICATION.md | frontend/src/components/wizard/ | Remove (sprint completed) |
| REDIS_MEMORY_ANALYSIS.md | docs/ | Keep for key-namespace and size reference; note: written for 256MB local Redis; project uses Redis Cloud (30MB) — update or add caveat if kept |
| flymcp/README.md | flymcp/ | Keep (MCP in use) |
| mcp-redis-cloud/README.md | mcp-redis-cloud/ | Keep (MCP in use) |

---

## Recommended File Structure After Cleanup

```
portfolio-navigator-wizard/
├── README.md                              # Project overview
├── RISK_PROFILE_SYSTEM.md                 # Core feature
├── RISK_PROFILING_QUESTIONNAIRE_AND_LOGIC.md  # Core feature
├── DECISION_FRAMEWORK_FLOW.md             # UX reference
├── OPTIMIZE_BUTTON_FLOW.md                # Feature reference
├── THEME_SWITCHING_GUIDE.md               # Theme docs
├── TICKER_UPDATE_WORKFLOW.md              # Operations
├── PORTFOLIOS_IN_REDIS.md                 # Auto-generated; keep root copy only
│
├── docs/
│   ├── DEPLOYMENT_OPERATIONS.md           # Operations runbook
│   ├── INFRASTRUCTURE_AND_COSTS.md        # Cost analysis (NEW)
│   ├── SEARCH_OPTIMIZATION.md             # Search performance
│   ├── REDIS_ARCHITECTURE.md              # Redis docs
│   ├── DATA_DICTIONARY.md                 # Data reference
│   ├── DATA_SOURCES_AND_METHODOLOGY.md    # Data provenance
│   ├── BACKEND_UTILS_REFERENCE.md         # Developer reference
│   ├── BACKEND_PERFORMANCE_INVESTIGATION.md # Ops/troubleshooting
│   ├── PURE_STRATEGY_PORTFOLIOS.md        # Strategy docs
│   ├── MOBILE_LANDSCAPE_HINT_IMPLEMENTATION.md  # Mobile UX
│   └── REDIS_MEMORY_ANALYSIS.md           # Key namespaces (caveat: Redis Cloud vs 256MB local)
│
└── backend/scripts/
    └── README.md                          # Scripts docs
```

**Result:** ~19–20 files (root + docs + backend/scripts + optional frontend/flymcp/mcp READMEs). PORTFOLIOS_IN_REDIS.md kept at root only.

---

## Cleanup Commands

After approval, run these commands to remove outdated files:

```bash
# Outdated infrastructure docs
rm RAILWAY_DEPLOYMENT_GUIDE.md
rm PRE_DEPLOYMENT_CHECKLIST.md
rm TESTING_SUMMARY.md
rm REDIS_CONFIGURATION_GUIDE.md
rm REDIS_SECURITY_ASSESSMENT.md
rm PROMETHEUS_GRAFANA_SETUP.md
rm SUPABASE_INTEGRATION_PLAN.md
rm Upstash-to-redis.md
rm QUICK_REFERENCE.md
rm docs/Upstash-console.md

# Duplicates (keep root PORTFOLIOS_IN_REDIS.md; code writes there)
rm backend/PORTFOLIOS_IN_REDIS.md
rm backend/scripts/PORTFOLIOS_IN_REDIS.md

# One-time analysis (BACKEND_PERFORMANCE_INVESTIGATION kept for ops value)
rm BACKEND-UPGRADE-REPORT.md
rm docs/PROJECT_COMPLETE_ANALYSIS.md
rm RISK_PROFILE_CONSTRAINTS_ANALYSIS.md
rm PORTFOLIO_POSITION_ANALYSIS.md

# Sprint docs (after review)
rm frontend/src/components/wizard/SPRINT-2-INTEGRATION-VERIFICATION.md
rm .claude/project\ overview.md
```

# Documentation Review & Cleanup Recommendations

**Date:** 2026-03-06
**Total Files Reviewed:** 40 markdown files

---

## Summary

| Category | Count | Action |
|----------|-------|--------|
| Essential - Keep | 12 | Maintain and update |
| Reference - Keep | 5 | Keep for developer reference |
| Outdated - Remove | 11 | Delete (superseded or completed) |
| Duplicates - Remove | 3 | Delete (consolidate) |
| One-time Analysis - Remove | 5 | Delete or archive |
| Feature Docs - Review | 4 | Check if still relevant |

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

## REMOVE - Duplicate Files (3 files)

Same content in multiple locations.

| File | Location | Keep Instead |
|------|----------|--------------|
| PORTFOLIOS_IN_REDIS.md | root | Auto-generated, can be regenerated |
| PORTFOLIOS_IN_REDIS.md | backend/ | Duplicate |
| PORTFOLIOS_IN_REDIS.md | backend/scripts/ | Duplicate |

**Note:** These are auto-generated snapshots. Delete all three; regenerate on-demand if needed.

---

## REMOVE - One-time Analysis (5 files)

Historical investigation/analysis documents with limited ongoing value.

| File | Location | Reason |
|------|----------|--------|
| BACKEND-UPGRADE-REPORT.md | root | Historical upgrade report |
| BACKEND_PERFORMANCE_INVESTIGATION.md | docs/ | Investigation complete |
| PROJECT_COMPLETE_ANALYSIS.md | docs/ | One-time analysis |
| RISK_PROFILE_CONSTRAINTS_ANALYSIS.md | root | Analysis complete, issues fixed |
| PORTFOLIO_POSITION_ANALYSIS.md | root | One-time analysis |

---

## REVIEW - Feature/Sprint Documentation (4 files)

Check if still relevant to current implementation.

| File | Location | Review Notes |
|------|----------|--------------|
| API-DOCUMENTATION.md | frontend/.../wizard/ | Check if API docs are current |
| SPRINT-2-INTEGRATION-VERIFICATION.md | frontend/.../wizard/ | Sprint completed, likely delete |
| REDIS_MEMORY_ANALYSIS.md | docs/ | May be outdated, review |
| flymcp/README.md | flymcp/ | Check if flymcp is still used |
| mcp-redis-cloud/README.md | mcp-redis-cloud/ | Check if still used |

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
│
├── docs/
│   ├── DEPLOYMENT_OPERATIONS.md           # Operations runbook
│   ├── INFRASTRUCTURE_AND_COSTS.md        # Cost analysis (NEW)
│   ├── SEARCH_OPTIMIZATION.md             # Search performance
│   ├── REDIS_ARCHITECTURE.md              # Redis docs
│   ├── DATA_DICTIONARY.md                 # Data reference
│   ├── DATA_SOURCES_AND_METHODOLOGY.md    # Data provenance
│   ├── BACKEND_UTILS_REFERENCE.md         # Developer reference
│   ├── PURE_STRATEGY_PORTFOLIOS.md        # Strategy docs
│   └── MOBILE_LANDSCAPE_HINT_IMPLEMENTATION.md  # Mobile UX
│
└── backend/scripts/
    └── README.md                          # Scripts docs
```

**Result:** 17 files instead of 40 (57% reduction)

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

# Duplicates
rm PORTFOLIOS_IN_REDIS.md
rm backend/PORTFOLIOS_IN_REDIS.md
rm backend/scripts/PORTFOLIOS_IN_REDIS.md

# One-time analysis
rm BACKEND-UPGRADE-REPORT.md
rm docs/BACKEND_PERFORMANCE_INVESTIGATION.md
rm docs/PROJECT_COMPLETE_ANALYSIS.md
rm RISK_PROFILE_CONSTRAINTS_ANALYSIS.md
rm PORTFOLIO_POSITION_ANALYSIS.md

# Sprint docs (after review)
rm frontend/src/components/wizard/SPRINT-2-INTEGRATION-VERIFICATION.md
rm .claude/project\ overview.md
```

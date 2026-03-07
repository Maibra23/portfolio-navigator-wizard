# Scripts Directory

This directory contains utility scripts for managing portfolios, tickers, and system maintenance.

## Strategy Portfolio Scripts (NEW)

### `regenerate_strategy_portfolios.py`
**Status: KEEP - Production Script**
- Regenerates all strategy portfolios (pure + personalized)
- Clears existing portfolios before regeneration
- Generates 108 portfolios total (18 pure + 90 personalized)
- **Usage**: `python3 backend/scripts/regenerate_strategy_portfolios.py`

### `clear_strategy_portfolios.py`
**Status: KEEP - Utility Script**
- Clears all strategy portfolio keys from Redis
- Useful for cleanup before regeneration
- **Usage**: `python3 backend/scripts/clear_strategy_portfolios.py`

### `audit_strategy_portfolios.py`
**Status: KEEP - Maintenance Script**
- Comprehensive audit of all strategy portfolios in Redis
- Validates allocations, checks for issues/warnings
- Generates JSON reports in `reports/` directory
- **Usage**: `python3 backend/scripts/audit_strategy_portfolios.py`

## Regular Portfolio Scripts

### `regenerate_all_portfolios.py`
**Status: KEEP - Production Script**
- Regenerates regular portfolios for all risk profiles
- Uses parallel processing for efficiency
- Clears moderate profile first, then regenerates all
- **Usage**: `python3 backend/scripts/regenerate_all_portfolios.py`

### `scheduled_regen.py`
**Status: KEEP - Production Script (Cron/Systemd)**
- Scheduled regeneration entrypoint
- Generates 12 portfolios per risk profile
- Stores stats in Redis
- Intended for cron/systemd timer (every 7 days)
- **Usage**: `python3 backend/scripts/scheduled_regen.py`

### `generate_all_portfolios.py`
**Status: REMOVE - Duplicate Script**
- Similar to `regenerate_all_portfolios.py` but less complete
- Uses `use_parallel=False` (slower)
- No clearing logic
- **Recommendation**: Remove - use `regenerate_all_portfolios.py` instead

## Analysis & Verification Scripts

### `verify_portfolios.py`
**Status: KEEP - Maintenance Script**
- Verifies portfolio uniqueness and constraints
- Checks risk profile compliance
- Referenced in Makefile
- **Usage**: `make verify-portfolios`

### `comprehensive_ticker_analysis.py`
**Status: REMOVE - One-Time Analysis Script**
- One-time analysis for ticker data coverage
- 15-year data coverage analysis
- Exchange filtering analysis
- **Recommendation**: Remove - was for initial analysis only

### `monitor_smart_refresh.py`
**Status: KEEP - Debugging/Monitoring Tool**
- Monitors smart-refresh status
- Useful for debugging refresh operations
- Referenced in Makefile
- **Usage**: `python3 backend/scripts/monitor_smart_refresh.py`

## Documentation

### `optionality.mdc`
**Status: KEEP - Documentation**
- Analysis document comparing original vs improved portfolios
- Not a script, but useful reference
- **Recommendation**: Keep for historical reference

## Reports Directory

All audit JSON files are saved to `backend/scripts/reports/` directory.
Old audit files can be safely deleted if no longer needed.


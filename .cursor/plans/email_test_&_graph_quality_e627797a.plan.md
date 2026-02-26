---
name: Email Test & Graph Quality
overview: Test the email notification system with a simple script, diagnose and fix the crisis impact graph data extraction issue in the PDF export, and upgrade all chart/table rendering to high-quality SVG (with PNG fallback at 300 DPI) for professional PDF reports.
todos:
  - id: email-test
    content: Create test_email_notification.py script with progress bar, send test email to stay.away202@gmail.com, verify delivery
    status: pending
  - id: crisis-graph-diagnose
    content: Fix _extract_stress_impact() to consistently use max_drawdown, update chart labels to clarify 'Peak-to-Trough Drawdown'
    status: pending
  - id: chart-quality-dpi
    content: Upgrade _generate_plot() and _generate_plot_base64() to 300 DPI with proper font/anti-aliasing settings
    status: pending
  - id: chart-quality-svg
    content: Add SVG output to generate_report_plots() for ZIP exports
    status: pending
  - id: chart-quality-lineweights
    content: Ensure all linewidths >= 1pt across all chart code and table borders
    status: pending
  - id: chart-quality-fonts
    content: Set Arial/Helvetica as default font family in matplotlib rcParams for all charts
    status: pending
  - id: verify-changes
    content: Run the PDF/export generation to verify improved chart quality and correct crisis impact graph
    status: pending
isProject: false
---

# Email Notification Test, Crisis Impact Graph Fix, and Chart Quality Upgrade

## Task 1: Email Notification Test Script

The email system lives in `[backend/utils/email_notifier.py](backend/utils/email_notifier.py)`. It uses Python's `smtplib` with SMTP/TLS (port 587), gated by environment variables:

- `TTL_EMAIL_NOTIFICATIONS=true`
- `TTL_NOTIFICATION_EMAIL=stay.away202@gmail.com`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`

**Plan:**

- Create `backend/scripts/test_email_notification.py` that:
  - Temporarily sets `TTL_EMAIL_NOTIFICATIONS=true` and `TTL_NOTIFICATION_EMAIL=stay.away202@gmail.com`
  - Reads SMTP credentials from `.env` (or prompts if missing)
  - Sends a test `NotificationMessage` with severity=INFO
  - Reports success/failure with clear error messages
  - Includes a progress indicator
- **Note:** This requires valid SMTP credentials (Gmail app password) in `.env`. The script will tell you exactly what's missing if it fails.
- Delete the test script after verifying it works.

---

## Task 2: Crisis Impact Graph Diagnosis

The "Crisis Impact" bar chart in the PDF export is generated at lines 1574-1601 of `[backend/utils/pdf_report_generator.py](backend/utils/pdf_report_generator.py)`. The data extraction uses `_extract_stress_impact()` (lines 655-670).

**Root cause analysis - why the graph appears "off":**

The `_extract_stress_impact()` method searches scenario results in this priority order:

1. Top-level keys: `portfolio_impact`, `impact`, `value_change`, `value_change_pct` (none of these exist in the actual stress test output)
2. Falls through to `metrics` dict and grabs the **first match** among: `max_drawdown`, `total_return`, `worst_month_return`

The problem is that `max_drawdown` is checked first and is always present. This value represents the **peak-to-trough drawdown** (e.g., -0.35), which only captures the worst dip during the crisis window. Meanwhile, `total_return` captures the **full period return** including recovery, which can be positive even in severe crisis scenarios (like 2008 where the analysis window extends to 2011).

This creates two issues:

- **Inconsistent metric**: Some scenarios might have `portfolio_impact` at top level while others don't, causing different metrics to be compared on the same chart
- **Misleading representation**: `max_drawdown` is the most severe point, but the graph is labeled "Crisis Impact" which users interpret as "how much did I lose overall"

**Fix plan:**

- Modify `_extract_stress_impact()` to consistently use `max_drawdown` (the most meaningful crisis-impact metric) and document this clearly
- Add a note/label on the chart clarifying it shows "Peak-to-Trough Drawdown" not total period return
- Ensure the values are presented correctly (max_drawdown is already negative, then multiplied by 100)

---

## Task 3: High-Quality Charts and Tables

Currently all charts use **PNG at 150 DPI** (lines 678, 694 of `pdf_report_generator.py`). The user wants SVG or 300 DPI PNG with professional rendering.

**Approach: SVG-first with PNG fallback**

For ReportLab PDF embedding, the best path is:

1. **Primary: High-resolution PNG at 300 DPI** -- ReportLab natively supports PNG via `Image()` and this avoids adding `svglib` dependency. At 300 DPI with proper settings, PNG renders crisply in PDFs.
2. **For ZIP exports: SVG format** -- The `generate_report_plots()` method (used for ZIP downloads) can output SVG files alongside/instead of PNG.

**Specific changes to `_generate_plot()` and `_generate_plot_base64()`:**

- Increase DPI from 150 to 300
- Set matplotlib `rcParams` for:
  - Font family: `Arial` or `Helvetica` (web-safe)
  - Minimum line width: 1pt (`lines.linewidth: 1.0`)
  - Anti-aliasing OFF for text: `text.antialiased: False`
  - Anti-aliasing OFF for lines at small widths
- Set `savefig` params: `dpi=300`, `format='png'`, `pad_inches=0.1`
- For ZIP exports (`generate_report_plots`): add SVG output using `format='svg'` alongside PNG

**Changes to individual chart code:**

- Ensure all `linewidth` params are >= 1.0 throughout the file
- Use `fontname='Arial'` or `fontname='Helvetica'` explicitly on all text elements
- Adjust `figsize` proportionally since higher DPI means more pixels

**Table quality:** Tables are already vector-based in ReportLab (drawn directly as PDF primitives), so they're already sharp. We'll ensure minimum line weights of 1pt in table borders.

**Files to modify:**

- `[backend/utils/pdf_report_generator.py](backend/utils/pdf_report_generator.py)`: `_generate_plot()`, `_generate_plot_base64()`, `generate_report_plots()`, matplotlib rcParams setup, all chart-generating methods, table line widths


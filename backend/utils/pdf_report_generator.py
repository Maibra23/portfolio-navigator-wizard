#!/usr/bin/env python3
"""
PDF Report Generator
Generates comprehensive PDF reports for portfolios using reportlab.
Includes: Executive Summary, Portfolio, Tax, Optimization summary, Stress Test, Costs, 5-Year Projection, Metrics.

CAPTION MAP:
  exec_summary_table  → "Expected Return = annualized historical gain..."
  portfolio_table     → "Concentration above 20–25% in a single holding..."
  sector_pie_chart    → "Sector Breakdown: Each slice shows the combined allocation..."
  tax_table           → "ISK/KF: Schablonbeskattning — a flat annual tax..."
  account_comp_table  → "★ = lowest annual tax for this portfolio size..."
  optimization_table  → "Current = your portfolio as built..."
  frontier_chart      → "Efficient Frontier: The blue curve shows the optimal risk/return boundary..."
  costs_table         → "Setup cost is one-time. Annual cost recurs..."
  projection_table    → "Base: +X% | Pessimistic: +X% over 5 years..."
  projection_chart    → "Projection Trajectory: Green = Optimistic, Blue = Base Case..."
  risk_table          → "Diversification above 70 = strong resistance..."
"""

import logging
import base64
from typing import Dict, List, Optional, Any
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors

logger = logging.getLogger(__name__)

try:
    from .five_year_projection import run_five_year_projection
except ImportError:
    run_five_year_projection = None
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # No GUI backend for server environments
    MPL_AVAILABLE = True
    logger.info("Matplotlib available for PDF report generation.")
except ImportError:
    MPL_AVAILABLE = False
    logger.warning("Matplotlib not found. PDF reports will be text-only.")

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, KeepTogether, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas


class PageNumCanvas(canvas.Canvas):
    """Canvas that adds page numbers and footer/header to each page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_page_info(page_count)
            super().showPage()
        super().save()

    def draw_page_info(self, page_count):
        self.setFont("Helvetica", 7)
        self.setStrokeColor(colors.HexColor('#e2e8f0'))
        self.setLineWidth(0.5)
        self.line(40, 38, 555, 38)
        self.line(40, 805, 555, 805)
        self.setFillColor(colors.HexColor('#718096'))
        self.drawRightString(555, 25, f"Page {self._pageNumber} of {page_count}")
        self.drawString(40, 25, "Portfolio Analysis Report")
        self.drawString(40, 812, "Portfolio Navigator Wizard")
        report_date = datetime.now().strftime("%Y-%m-%d")
        self.drawRightString(555, 812, report_date)


class PDFReportGenerator:
    """
    Generates comprehensive PDF reports for portfolios.

    Spacing contract:
    - ALL spacing is routed through _sp() — no raw Spacer(1, x*inch) anywhere.
    - ALL ParagraphStyle definitions have spaceAfter=0 and spaceBefore=0.
    - Section transitions use _section_break() (natural) or PageBreak() (data-heavy).
    - Every chart+caption pair is wrapped in KeepTogether.
    """

    # Page margins (inches)
    MARGIN_LEFT = 0.6
    MARGIN_RIGHT = 0.6
    MARGIN_TOP = 0.55
    MARGIN_BOTTOM = 0.55

    # ── Spacing Tier System (6 levels + title special) ────────────────────────
    # 'section'   : Space before a new numbered section heading
    SPACE_BEFORE_SECTION = 0.22
    # 'header'    : Space after a section/subsection heading, before first content
    SPACE_AFTER_SECTION_HEADER = 0.10
    # 'table'     : Breathing room after a complete table block (table + note)
    SPACE_AFTER_TABLE = 0.14
    # 'chart'     : Breathing room after a complete chart block (chart + caption)
    SPACE_AFTER_CHART = 0.10
    # 'caption'   : After a standalone caption/note before the next content block
    SPACE_CAPTION_TO_NEXT = 0.18
    # 'tight'     : Between tightly coupled elements (table→note, chart→caption)
    SPACE_TIGHT = 0.04
    # 'title_top' : Top padding on the title page (design constant)
    SPACE_TITLE_TOP = 0.90

    # Chart dimensions (inches)
    CHART_WIDTH = 6.2
    CHART_HEIGHT = 2.8
    CHART_HEIGHT_LARGE = 3.2
    CHART_WIDTH_COMPACT = 5.5
    CHART_HEIGHT_COMPACT = 2.3

    # Usable page width (A4 minus margins, approximate)
    PAGE_WIDTH_INCH = 7.07

    def __init__(self):
        self.page_size = A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    # ── Spacing helpers ───────────────────────────────────────────────────────

    def _sp(self, space_type: str) -> Spacer:
        """
        Return a Spacer for the given context type.
        ALWAYS use this method — never call Spacer() directly anywhere in the story.

        Types:
            'section'   – 0.22 in  – before a numbered section heading
            'header'    – 0.10 in  – after a heading, before content
            'table'     – 0.14 in  – after a complete table block
            'chart'     – 0.10 in  – after a complete chart block
            'caption'   – 0.18 in  – after a caption/note before new content
            'tight'     – 0.04 in  – between tightly coupled elements
            'title_top' – 0.90 in  – title page top padding (design constant)
        """
        mapping = {
            'section':   self.SPACE_BEFORE_SECTION * inch,
            'header':    self.SPACE_AFTER_SECTION_HEADER * inch,
            'table':     self.SPACE_AFTER_TABLE * inch,
            'chart':     self.SPACE_AFTER_CHART * inch,
            'caption':   self.SPACE_CAPTION_TO_NEXT * inch,
            'tight':     self.SPACE_TIGHT * inch,
            'title_top': self.SPACE_TITLE_TOP * inch,
        }
        return Spacer(1, mapping.get(space_type, self.SPACE_AFTER_CHART * inch))

    def _section_break(self, story: list) -> None:
        """
        Visual section break — spacing + HRFlowable divider.
        Use between naturally flowing sections (1→2, 2→3, 3→4, etc.).
        Use PageBreak() directly for data-heavy sections (Optimization, Projection).
        """
        story.append(self._sp('section'))
        story.append(HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.HexColor('#e2e8f0'),
            spaceAfter=6,
        ))
        story.append(self._sp('tight'))

    def _section_heading(self, story: list, number: str, title: str) -> None:
        """Add a numbered section heading, then 'header' spacing."""
        story.append(Paragraph(f"{number}. {title}", self.styles['SectionHeading']))
        story.append(self._sp('header'))

    def _subsection_heading(self, story: list, title: str) -> None:
        """Add a subsection heading, then 'tight' spacing."""
        story.append(Paragraph(title, self.styles['SubsectionHeading']))
        story.append(self._sp('tight'))

    # ── Style setup ───────────────────────────────────────────────────────────

    def _setup_custom_styles(self):
        """
        Paragraph styles — ALL have spaceAfter=0 and spaceBefore=0.
        All spacing is controlled exclusively via _sp() in the story.
        """
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=0,
            spaceBefore=0,
            alignment=TA_CENTER,
            leading=26,
        ))
        self.styles.add(ParagraphStyle(
            name='TitleSubheading',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=0,
            spaceBefore=0,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            leading=18,
        ))
        self.styles.add(ParagraphStyle(
            name='TitleDate',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#718096'),
            spaceAfter=0,
            spaceBefore=0,
            alignment=TA_CENTER,
            leading=12,
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=0,
            spaceBefore=0,
            fontName='Helvetica-Bold',
            leading=16,
        ))
        self.styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=self.styles['Heading3'],
            fontSize=10,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=0,
            spaceBefore=0,
            fontName='Helvetica-Bold',
            leading=13,
        ))
        self.styles.add(ParagraphStyle(
            name='ReportBody',
            parent=self.styles['Normal'],
            fontSize=8.5,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=0,
            spaceBefore=0,
            leading=11,
            firstLineIndent=0,
        ))
        self.styles.add(ParagraphStyle(
            name='CompactBody',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=0,
            spaceBefore=0,
            leading=10,
        ))
        # Text-heavy sections (Methodology, Risk Analysis) — slight indent
        # simulates wider content margins for better readability.
        self.styles.add(ParagraphStyle(
            name='MethodologyBody',
            parent=self.styles['Normal'],
            fontSize=8.5,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=0,
            spaceBefore=0,
            leading=11,
            leftIndent=8,
            rightIndent=8,
        ))
        self.styles.add(ParagraphStyle(
            name='Disclaimer',
            parent=self.styles['Normal'],
            fontSize=7.5,
            textColor=colors.HexColor('#718096'),
            alignment=TA_CENTER,
            spaceAfter=0,
            spaceBefore=0,
            fontName='Helvetica-Oblique',
            leading=10,
        ))
        self.styles.add(ParagraphStyle(
            name='ChartExplanation',
            parent=self.styles['Normal'],
            fontSize=7.5,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=0,
            spaceBefore=0,
            fontName='Helvetica-Oblique',
            leading=9.5,
            leftIndent=4,
            rightIndent=4,
        ))
        self.styles.add(ParagraphStyle(
            name='InsightCallout',
            parent=self.styles['Normal'],
            fontSize=8.5,
            textColor=colors.HexColor('#2b6cb0'),
            spaceAfter=0,
            spaceBefore=0,
            leftIndent=6,
            leading=11,
        ))
        self.styles.add(ParagraphStyle(
            name='TableNote',
            parent=self.styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#718096'),
            spaceAfter=0,
            spaceBefore=0,
            leading=8.5,
        ))
        self.styles.add(ParagraphStyle(
            name='InlineMetric',
            parent=self.styles['Normal'],
            fontSize=8.5,
            leading=10,
            spaceAfter=0,
            spaceBefore=0,
        ))

    # ── Table helper ──────────────────────────────────────────────────────────

    def _create_table(self, data: List[List[str]], col_widths: Optional[List[float]] = None,
                      compact: bool = True, ultra_compact: bool = False) -> Table:
        """Create a styled table. compact=True standard density; ultra_compact=True max density."""
        if col_widths is None and data:
            col_widths = self._calculate_optimal_column_widths(data)
        if col_widths is None:
            col_widths = [self.PAGE_WIDTH_INCH * inch / max(1, len(data[0]))] * len(data[0]) if data else []
        table = Table(data, colWidths=col_widths)

        if ultra_compact:
            header_pad, data_pad = 4, 3
            font_size_header, font_size_data = 8, 7.5
        elif compact:
            header_pad, data_pad = 5, 4
            font_size_header, font_size_data = 8.5, 8
        else:
            header_pad, data_pad = 6, 5
            font_size_header, font_size_data = 9, 8.5

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), font_size_header),
            ('BOTTOMPADDING', (0, 0), (-1, 0), header_pad),
            ('TOPPADDING', (0, 0), (-1, 0), header_pad),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2d3748')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), font_size_data),
            ('BOTTOMPADDING', (0, 1), (-1, -1), data_pad),
            ('TOPPADDING', (0, 1), (-1, -1), data_pad),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#2d3748')),
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor('#cbd5e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        return table

    def _calculate_optimal_column_widths(self, data: List[List[str]], max_width: float = None) -> List[float]:
        """Calculate proportional column widths from content length."""
        if not data:
            return []
        max_width = (max_width or self.PAGE_WIDTH_INCH) * inch
        ncols = len(data[0])
        col_max_chars = [0] * ncols
        for row in data:
            for c, cell in enumerate(row):
                if c < ncols:
                    col_max_chars[c] = max(col_max_chars[c], len(str(cell)))
        total_chars = sum(col_max_chars) or 1
        return [max_width * (col_max_chars[c] / total_chars) for c in range(ncols)]

    # ── Formatting helpers ────────────────────────────────────────────────────

    def _format_number(self, value: float, decimals: int = 2, currency: bool = False) -> str:
        if value is None:
            return "N/A"
        formatted = f"{value:,.{decimals}f}"
        if currency:
            formatted = f"{formatted} SEK"
        return formatted

    def _format_percentage(self, value: float, decimals: int = 2) -> str:
        """Values in (0, 1] treated as decimals (e.g. 0.12 → 12%)."""
        if value is None:
            return "N/A"
        display_val = value
        if isinstance(value, (int, float)) and 0 < abs(value) <= 1 and value != 0:
            display_val = value * 100
        return f"{display_val:.{decimals}f}%"

    # ── Plot helpers ──────────────────────────────────────────────────────────

    def _generate_plot(self, plt_obj, width: float = None, height: float = None,
                       compact: bool = False, large: bool = False) -> Image:
        """Convert matplotlib plot to reportlab Image."""
        img_buffer = BytesIO()
        plt_obj.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150,
                        facecolor='white', edgecolor='none', pad_inches=0.5)
        img_buffer.seek(0)
        plt_obj.close()
        if compact:
            w, h = self.CHART_WIDTH_COMPACT * inch, self.CHART_HEIGHT_COMPACT * inch
        elif large:
            w, h = self.CHART_WIDTH * inch, self.CHART_HEIGHT_LARGE * inch
        else:
            w = (width or self.CHART_WIDTH) * inch
            h = (height or self.CHART_HEIGHT) * inch
        return Image(img_buffer, width=w, height=h)

    def _generate_plot_base64(self, plt_obj) -> str:
        """Convert a matplotlib plot to a base64 encoded PNG string."""
        img_buffer = BytesIO()
        plt_obj.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
        img_buffer.seek(0)
        plt_obj.close()
        return base64.b64encode(img_buffer.getvalue()).decode('utf-8')

    # ── ZIP plot export ───────────────────────────────────────────────────────

    def generate_report_plots(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate all report plots as base64 encoded images for ZIP exports."""
        if not MPL_AVAILABLE:
            return []

        plots = []
        portfolio = data.get('portfolio', [])
        portfolio_value = data.get('portfolioValue', 0.0)
        opt = data.get('optimizationResults')
        stress_results = data.get('stressTestResults')

        # 1. Sector Allocation
        try:
            sector_weights = {}
            for pos in portfolio:
                weight = pos.get('allocation', 0.0)
                if weight > 1:
                    weight = weight / 100.0
                sector = pos.get('sector', 'Unknown')
                sector_weights[sector] = sector_weights.get(sector, 0.0) + weight
            if sector_weights and any(s != 'Unknown' for s in sector_weights.keys()):
                plt.figure(figsize=(10, 6))
                labels = list(sector_weights.keys())
                sizes = list(sector_weights.values())
                plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140,
                        colors=plt.cm.Paired(range(len(labels))))
                plt.title('Portfolio Sector Allocation')
                plt.axis('equal')
                content = self._generate_plot_base64(plt)
                plots.append({"filename": "sector_allocation.png", "content": content, "size": len(content)})
        except Exception as e:
            logger.warning(f"Failed to generate sector plot for ZIP: {e}")

        # 2. Efficient Frontier
        if opt:
            try:
                plt.figure(figsize=(10, 6))
                random_portfolios = (
                    opt.get('market_optimized_portfolio', {}).get('random_portfolios') or
                    opt.get('weights_optimized_portfolio', {}).get('random_portfolios')
                )
                if random_portfolios:
                    plt.scatter([p['risk'] for p in random_portfolios],
                                [p['return'] for p in random_portfolios],
                                c='lightgrey', s=10, alpha=0.5, label='Random Portfolios')
                frontier = (
                    opt.get('market_optimized_portfolio', {}).get('efficient_frontier') or
                    opt.get('weights_optimized_portfolio', {}).get('efficient_frontier')
                )
                if frontier:
                    plt.plot([p['risk'] for p in frontier], [p['return'] for p in frontier],
                             'b-', linewidth=2, label='Efficient Frontier')
                current = (opt.get('current_portfolio') or {}).get('metrics', {})
                if current:
                    plt.scatter(current.get('risk', 0), current.get('expected_return', 0),
                                c='red', s=100, marker='*', label='Current')
                weights_opt = (opt.get('weights_optimized_portfolio') or {}).get('optimized_portfolio', {}).get('metrics', {})
                if weights_opt:
                    plt.scatter(weights_opt.get('risk', 0), weights_opt.get('expected_return', 0),
                                c='blue', s=80, marker='D', label='Weights Optimized')
                market_opt = (opt.get('market_optimized_portfolio') or {}).get('optimized_portfolio', {}).get('metrics', {})
                if market_opt:
                    plt.scatter(market_opt.get('risk', 0), market_opt.get('expected_return', 0),
                                c='green', s=80, marker='s', label='Market Optimized')
                plt.title('Portfolio Optimization: Risk vs Return')
                plt.xlabel('Risk (Volatility)')
                plt.ylabel('Expected Return')
                plt.legend()
                plt.grid(True, linestyle='--', alpha=0.7)
                content = self._generate_plot_base64(plt)
                plots.append({"filename": "optimization_frontier.png", "content": content, "size": len(content)})
            except Exception as e:
                logger.warning(f"Failed to generate optimization plot for ZIP: {e}")

        # 3. Stress Test
        if stress_results:
            try:
                scenarios = stress_results.get('scenarios') or stress_results.get('scenario_results') or {}
                if scenarios:
                    names, impacts = [], []
                    for name, res in scenarios.items():
                        if isinstance(res, dict):
                            impact = res.get('portfolio_impact') or res.get('impact')
                            if impact is not None:
                                names.append(name.replace('_', ' ').title())
                                impacts.append(impact * 100)
                    if names:
                        plt.figure(figsize=(10, 6))
                        sorted_indices = sorted(range(len(impacts)), key=lambda k: impacts[k])
                        names = [names[i] for i in sorted_indices]
                        impacts = [impacts[i] for i in sorted_indices]
                        plt.barh(names, impacts, color=['red' if x < 0 else 'green' for x in impacts])
                        plt.title('Stress Test: Potential Impact')
                        plt.xlabel('Impact (%)')
                        plt.grid(True, axis='x', linestyle='--', alpha=0.7)
                        content = self._generate_plot_base64(plt)
                        plots.append({"filename": "stress_test_impact.png", "content": content, "size": len(content)})
            except Exception as e:
                logger.warning(f"Failed to generate stress test plot for ZIP: {e}")

        # 4. 5-Year Projection
        projection_metrics = data.get('projectionMetrics') or {}
        weights = projection_metrics.get('weights') or (data.get('portfolio') or {}).get('weights') or {}
        if not weights and (data.get('portfolio') or {}).get('allocations'):
            weights = {
                a.get('symbol', a.get('ticker', '')): (a.get('allocation', 0) / 100.0)
                for a in (data.get('portfolio') or {}).get('allocations', [])
                if a.get('symbol') or a.get('ticker')
            }
        if run_five_year_projection and portfolio_value and weights:
            try:
                metrics = data.get('metrics', {})
                proj = run_five_year_projection(
                    initial_capital=float(portfolio_value),
                    weights={k: float(v) for k, v in weights.items() if v and k},
                    expected_return=float(projection_metrics.get('expectedReturn', metrics.get('expectedReturn', 0.08))),
                    risk=float(projection_metrics.get('risk', metrics.get('risk', 0.15))),
                    account_type=str(data.get('accountType', 'isk')),
                    tax_year=int(data.get('taxYear', datetime.now().year)),
                    courtage_class=(data.get('costData', {}).get('courtageClass') or 'medium').lower(),
                    rebalancing_frequency='quarterly',
                )
                plt.figure(figsize=(10, 6))
                plt.plot(proj['years'], proj['optimistic'], 'g-', marker='o', label='Optimistic')
                plt.plot(proj['years'], proj['base'], 'b-', marker='o', label='Base Case')
                plt.plot(proj['years'], proj['pessimistic'], 'r-', marker='o', label='Pessimistic')
                plt.title('5-Year Portfolio Projection')
                plt.xlabel('Year')
                plt.ylabel('Value (SEK)')
                plt.grid(True, alpha=0.3)
                plt.legend()
                from matplotlib.ticker import FuncFormatter
                def format_sek(x, pos):
                    if x >= 1e6: return f'{x/1e6:.1f}M'
                    if x >= 1e3: return f'{x/1e3:.0f}k'
                    return f'{x:.0f}'
                plt.gca().yaxis.set_major_formatter(FuncFormatter(format_sek))
                content = self._generate_plot_base64(plt)
                plots.append({"filename": "five_year_projection.png", "content": content, "size": len(content)})
            except Exception as e:
                logger.warning(f"Failed to generate projection plot for ZIP: {e}")

        return plots

    # ── Main report ───────────────────────────────────────────────────────────

    def generate_portfolio_report(self, data: Dict[str, Any]) -> bytes:
        """Generate comprehensive PDF report."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=self.page_size,
            leftMargin=self.MARGIN_LEFT * inch,
            rightMargin=self.MARGIN_RIGHT * inch,
            topMargin=self.MARGIN_TOP * inch,
            bottomMargin=self.MARGIN_BOTTOM * inch,
        )
        story = []

        portfolio_name = data.get('portfolioName') or "Investment Portfolio"
        portfolio_value = data.get('portfolioValue', 0.0)
        account_type = data.get('accountType', 'N/A')
        tax_year = data.get('taxYear', datetime.now().year)
        metrics = data.get('metrics') or {}

        # ── Resolve dynamic section numbers ──────────────────────────────────
        sec_num = 5
        if data.get('includeSections', {}).get('optimization', False) and data.get('optimizationResults'):
            opt_sec_num = sec_num
            sec_num += 1
        else:
            opt_sec_num = None
        if data.get('includeSections', {}).get('stressTest', False) and data.get('stressTestResults'):
            stress_sec_num = sec_num
            sec_num += 1
        else:
            stress_sec_num = None
        cost_sec_num = sec_num; sec_num += 1
        proj_sec_num = sec_num; sec_num += 1
        risk_sec_num = sec_num

        # ── PAGE 1: Title block + TOC + Disclaimer (nothing else shares this page) ──
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        disclaimer_text = (
            "DISCLAIMER: This report is for informational and educational purposes only. "
            "It does not constitute financial, investment, or tax advice. "
            "Historical performance is not indicative of future results. "
            "Consult a qualified financial advisor before making investment decisions."
        )

        # Title block — sits in upper ~40% of the page
        story.append(self._sp('title_top'))
        story.append(Paragraph("Portfolio Analysis Report", self.styles['CustomTitle']))
        story.append(self._sp('tight'))
        story.append(Paragraph(portfolio_name, self.styles['TitleSubheading']))
        story.append(self._sp('tight'))
        story.append(Paragraph(f"Report Date: {report_date}", self.styles['TitleDate']))
        story.append(self._sp('chart'))

        # Divider above TOC
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#cbd5e0')))
        story.append(self._sp('tight'))

        # TOC heading
        story.append(Paragraph("Table of Contents", self.styles['SubsectionHeading']))
        story.append(self._sp('tight'))

        # Build TOC entries
        toc_fixed = [
            "1. Executive Summary",
            "2. Methodology & Assumptions",
            "3. Portfolio Composition",
            "4. Swedish Tax Analysis",
        ]
        toc_dynamic = []
        if opt_sec_num:
            toc_dynamic.append(f"{opt_sec_num}. Optimization Results")
        if stress_sec_num:
            toc_dynamic.append(f"{stress_sec_num}. Stress Test Analysis")
        toc_dynamic.append(f"{cost_sec_num}. Transaction Costs")
        toc_dynamic.append(f"{proj_sec_num}. 5-Year Projection")
        toc_dynamic.append(f"{risk_sec_num}. Risk Analysis")

        all_toc = toc_fixed + toc_dynamic
        half = (len(all_toc) + 1) // 2
        toc_rows = []
        for i in range(half):
            left_text = all_toc[i] if i < len(all_toc) else ""
            right_text = all_toc[half + i] if (half + i) < len(all_toc) else ""
            toc_rows.append([
                Paragraph(left_text, self.styles['ReportBody']),
                Paragraph(right_text, self.styles['ReportBody']),
            ])

        toc_table = Table(toc_rows, colWidths=[3.5 * inch, 3.5 * inch])
        toc_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(toc_table)

        # Divider below TOC
        story.append(self._sp('tight'))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#cbd5e0')))
        story.append(self._sp('tight'))

        # Disclaimer at bottom of page 1
        story.append(Paragraph(disclaimer_text, self.styles['Disclaimer']))

        # Force new page — nothing else shares page 1
        story.append(PageBreak())

        # ── SECTION 1: EXECUTIVE SUMMARY ─────────────────────────────────────
        self._section_heading(story, "1", "Executive Summary")

        exp_ret = data.get('expectedReturn') if 'expectedReturn' in data else metrics.get('expectedReturn')
        risk_val = data.get('risk') if 'risk' in data else metrics.get('risk')
        sharpe_val = data.get('sharpeRatio') if 'sharpeRatio' in data else metrics.get('sharpeRatio')

        # exec_summary_table
        summary_data = [
            ['Portfolio Value', self._format_number(portfolio_value, currency=True), 'Account Type', account_type],
            ['Tax Year', str(tax_year), 'Expected Return',
             self._format_percentage(exp_ret) if exp_ret is not None else 'N/A'],
            ['Risk (Vol)', self._format_percentage(risk_val) if risk_val is not None else 'N/A',
             'Sharpe Ratio', self._format_number(sharpe_val, decimals=3) if sharpe_val is not None else 'N/A'],
        ]
        story.append(self._create_table(
            summary_data,
            col_widths=[1.6 * inch, 1.8 * inch, 1.4 * inch, 1.8 * inch],
            ultra_compact=True,
        ))
        story.append(self._sp('tight'))
        # Caption: exec_summary_table
        story.append(Paragraph(
            "Expected Return = annualized historical gain. "
            "Risk (Volatility) = typical annual price swing. "
            "Sharpe Ratio: above 1.0 = good risk-adjusted return, above 1.5 = excellent.",
            self.styles['CompactBody'],
        ))
        story.append(self._sp('table'))

        # ── SECTION 2: METHODOLOGY & ASSUMPTIONS ─────────────────────────────
        self._section_break(story)
        self._section_heading(story, "2", "Methodology & Assumptions")

        self._subsection_heading(story, "Data Sources")
        data_sources = [
            ['Source', 'Description'],
            ['Historical Prices', '3–5 years daily data → expected returns and risk metrics'],
            ['Tax Rates', 'Skatteverket official rates (schablonränta for ISK/KF, 30% gains for AF)'],
            ['Transaction Costs', 'Broker courtage schedules (Start, Mini, Small, Medium, Fixed Price tiers)'],
        ]
        story.append(self._create_table(data_sources, col_widths=[1.6 * inch, 5.2 * inch], ultra_compact=True))
        story.append(self._sp('tight'))
        story.append(Paragraph(
            "All projections use end-of-day historical prices. Tax rates reflect current legislation "
            "and may change. Consult your broker's fee schedule for accurate cost estimates.",
            self.styles['MethodologyBody'],
        ))
        story.append(self._sp('table'))

        self._subsection_heading(story, "Projection Scenarios")
        proj_method_data = [
            ['Scenario', 'Calculation', 'Use Case'],
            ['Optimistic', 'Return + Volatility', 'Upper bound — plan upside potential'],
            ['Base Case', 'Expected Return', 'Most likely — central planning figure'],
            ['Pessimistic', 'Return − 50% Vol', 'Conservative — stress test goals'],
        ]
        story.append(self._create_table(
            proj_method_data,
            col_widths=[1.2 * inch, 1.6 * inch, 4.0 * inch],
            ultra_compact=True,
        ))
        story.append(self._sp('tight'))
        story.append(Paragraph(
            "Each year deducts tax and costs, then compounds net return for realistic wealth projection.",
            self.styles['MethodologyBody'],
        ))
        story.append(self._sp('table'))

        self._subsection_heading(story, "Limitations")
        limitations_data = [
            ['Limitation', 'Impact'],
            ['Historical ≠ Future', 'Past returns do not guarantee future performance'],
            ['Static Assumptions', 'Current holdings maintained; trading changes outcomes'],
            ['Tax Law Changes', 'Rates based on current legislation; subject to revision'],
            ['Estimation Only', 'Educational purposes; consult a financial advisor'],
        ]
        story.append(self._create_table(limitations_data, col_widths=[1.6 * inch, 5.2 * inch], ultra_compact=True))
        story.append(self._sp('table'))

        # ── SECTION 3: PORTFOLIO COMPOSITION ─────────────────────────────────
        self._section_break(story)
        self._section_heading(story, "3", "Portfolio Composition")
        story.append(Paragraph(
            "Holdings breakdown. A well-diversified portfolio spreads risk across multiple assets and sectors.",
            self.styles['CompactBody'],
        ))
        story.append(self._sp('tight'))

        portfolio = data.get('portfolio', [])
        if portfolio:
            comp_data = [['Ticker', 'Allocation', 'Value (SEK)']]
            sector_weights = {}
            for pos in portfolio:
                ticker = pos.get('ticker', pos.get('symbol', 'N/A'))
                allocation = pos.get('allocation', 0.0)
                if allocation > 1:
                    allocation = allocation / 100.0
                value = portfolio_value * allocation if portfolio_value else 0.0
                comp_data.append([
                    ticker,
                    self._format_percentage(allocation * 100),
                    self._format_number(value, currency=True),
                ])
                sector = pos.get('sector', 'Unknown')
                sector_weights[sector] = sector_weights.get(sector, 0.0) + allocation

            # portfolio_table
            story.append(self._create_table(comp_data, compact=True))
            story.append(self._sp('tight'))
            # Caption: portfolio_table
            story.append(Paragraph(
                "Concentration above 20–25% in a single holding increases single-stock risk. "
                "Review positions with outsized weight relative to conviction.",
                self.styles['TableNote'],
            ))
            story.append(self._sp('table'))

            # sector_pie_chart
            if MPL_AVAILABLE and sector_weights:
                try:
                    has_real_sectors = any(s != 'Unknown' for s in sector_weights.keys())
                    if has_real_sectors:
                        plt.figure(figsize=(6, 3.2))
                        labels = list(sector_weights.keys())
                        sizes = list(sector_weights.values())
                        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140,
                                colors=plt.cm.Paired(range(len(labels))), textprops={'fontsize': 7})
                        plt.title('Sector Allocation', fontsize=9, fontweight='bold')
                        plt.axis('equal')
                        plt.tight_layout(pad=0.5)
                        chart_img = self._generate_plot(plt, compact=True)
                        # Caption: sector_pie_chart
                        sector_caption = Paragraph(
                            "<b>Sector Breakdown:</b> Each slice shows the combined allocation to that industry. "
                            "Exposure above 40% in one sector creates industry-specific concentration risk. "
                            "A spread of 10–25% per sector generally improves stability across market cycles.",
                            self.styles['ChartExplanation'],
                        )
                        story.append(KeepTogether([chart_img, self._sp('tight'), sector_caption]))
                        story.append(self._sp('chart'))
                except Exception as plot_e:
                    logger.warning(f"Failed to generate sector pie chart: {plot_e}")
        else:
            story.append(Paragraph("No portfolio data available.", self.styles['CompactBody']))
            story.append(self._sp('table'))

        # ── SECTION 4: SWEDISH TAX ANALYSIS ──────────────────────────────────
        self._section_break(story)
        self._section_heading(story, "4", "Swedish Tax Analysis")

        tax_data = data.get('taxData', {}) or {}
        if tax_data:
            tax_table_data = [['Component', 'Value', 'Meaning']]
            annual_tax = tax_data.get('annualTax') or tax_data.get('annual_tax')
            eff_rate = tax_data.get('effectiveTaxRate') or tax_data.get('effective_tax_rate')
            tax_free = tax_data.get('taxFreeLevel') or tax_data.get('tax_free_level')
            taxable_cap = tax_data.get('taxableCapital') or tax_data.get('taxable_capital')
            if annual_tax is not None:
                tax_table_data.append(['Annual Tax', self._format_number(float(annual_tax), currency=True),
                                       'Yearly deduction from returns'])
            if eff_rate is not None:
                tax_table_data.append(['Effective Rate', self._format_percentage(float(eff_rate)),
                                       'Tax as % of portfolio'])
            if tax_free is not None:
                tax_table_data.append(['Tax-Free Level', self._format_number(float(tax_free), currency=True),
                                       'Zero tax below this (ISK/KF)'])
            if taxable_cap is not None:
                tax_table_data.append(['Taxable Capital', self._format_number(float(taxable_cap), currency=True),
                                       'Amount subject to tax'])

            # tax_table
            story.append(self._create_table(
                tax_table_data,
                col_widths=[1.6 * inch, 2.0 * inch, 3.2 * inch],
                ultra_compact=True,
            ))
            story.append(self._sp('tight'))
            # Caption: tax_table
            story.append(Paragraph(
                "ISK/KF: Schablonbeskattning — a flat annual tax on capital, regardless of whether "
                "gains are realized. AF: 30% tax applies only when assets are sold.",
                self.styles['TableNote'],
            ))
            story.append(self._sp('table'))
        else:
            story.append(Paragraph("No tax data available.", self.styles['CompactBody']))
            story.append(self._sp('table'))

        # Account type comparison
        tax_comparison = data.get('taxComparison')
        if tax_comparison and len(tax_comparison) > 0:
            self._subsection_heading(story, "Account Type Comparison")
            comp_table_data = [['Account', 'Annual Tax', 'Eff. Rate', 'After-Tax']]
            lowest_tax = min(tc.get('annualTax', float('inf')) for tc in tax_comparison)
            for tc in tax_comparison:
                act_type = tc.get('accountType', 'N/A')
                annual_tax_val = tc.get('annualTax', 0)
                label = act_type + (" ★" if annual_tax_val == lowest_tax else "")
                comp_table_data.append([
                    label,
                    self._format_number(float(annual_tax_val), currency=True),
                    self._format_percentage(float(tc.get('effectiveRate', 0))),
                    self._format_percentage(float(tc.get('afterTaxReturn', 0))),
                ])

            # account_comp_table
            story.append(self._create_table(
                comp_table_data,
                col_widths=[1.4 * inch, 1.9 * inch, 1.6 * inch, 1.9 * inch],
                ultra_compact=True,
            ))
            story.append(self._sp('tight'))
            # Caption: account_comp_table
            story.append(Paragraph(
                "★ = lowest annual tax for this portfolio size and return. "
                "Switching account types involves transfer friction; factor in time horizon before moving.",
                self.styles['TableNote'],
            ))
            story.append(self._sp('table'))

        # Tax-free breakdown
        tax_free_data = data.get('taxFreeData')
        if tax_free_data and account_type in ('ISK', 'KF'):
            self._subsection_heading(story, "Tax-Free Breakdown")
            tax_free_level = tax_free_data.get('taxFreeLevel', 0)
            tax_free_amount = tax_free_data.get('taxFreeAmount', 0)
            taxable_amount = tax_free_data.get('taxableAmount', 0)
            is_tax_free = tax_free_data.get('isTaxFree', False)
            if is_tax_free:
                story.append(Paragraph(
                    f"<b>Zero Tax:</b> Portfolio ({self._format_number(portfolio_value, currency=True)}) "
                    f"is below the {tax_year} tax-free level ({self._format_number(tax_free_level, currency=True)}).",
                    self.styles['InsightCallout'],
                ))
                story.append(self._sp('table'))
            else:
                breakdown_table = [
                    ['Component', 'Amount', 'Share'],
                    ['Tax-Free', self._format_number(tax_free_amount, currency=True),
                     self._format_percentage(tax_free_data.get('taxFreePercentage', 0))],
                    ['Taxable', self._format_number(taxable_amount, currency=True),
                     self._format_percentage(tax_free_data.get('taxablePercentage', 0))],
                ]
                story.append(self._create_table(
                    breakdown_table,
                    col_widths=[1.4 * inch, 2.5 * inch, 1.4 * inch],
                    ultra_compact=True,
                ))
                story.append(self._sp('tight'))
                story.append(Paragraph(
                    f"Tax-free level {tax_year}: {self._format_number(tax_free_level, currency=True)}",
                    self.styles['TableNote'],
                ))
                story.append(self._sp('table'))

        # Recommendations
        recommendations = data.get('recommendations')
        if recommendations and len(recommendations) > 0:
            self._subsection_heading(story, "Recommendations")
            for rec in recommendations:
                rec_text = rec.replace('💡', '').replace('💰', '').replace('✅', '').replace('🎉', '').strip()
                story.append(Paragraph(f"• {rec_text}", self.styles['CompactBody']))
                story.append(self._sp('tight'))
            story.append(self._sp('table'))

        # ── SECTION 5: OPTIMIZATION RESULTS (force page break — large chart) ─
        if opt_sec_num:
            story.append(PageBreak())
            self._section_heading(story, str(opt_sec_num), "Optimization Results")
            opt = data['optimizationResults']
            rec = (opt.get('optimization_metadata') or {}).get('recommendation', 'weights')
            story.append(Paragraph(
                f"Strategy: {rec.replace('_', ' ').title()} — "
                "Modern Portfolio Theory to maximize return per unit of risk.",
                self.styles['CompactBody'],
            ))
            story.append(self._sp('tight'))

            current = (opt.get('current_portfolio') or {}).get('metrics', {})
            weights_opt = (opt.get('weights_optimized_portfolio') or {}).get('optimized_portfolio', {})
            wo_metrics = weights_opt.get('metrics', {})
            market_opt = (opt.get('market_optimized_portfolio') or {}).get('optimized_portfolio', {})
            mo_metrics = market_opt.get('metrics', {}) if market_opt else {}
            has_market = bool(mo_metrics)

            if current or wo_metrics or mo_metrics:
                headers = ['Metric', 'Current', 'Weights-Opt']
                if has_market:
                    headers.append('Market-Opt')
                opt_table = [headers]
                opt_table.append(
                    ['Exp. Return',
                     self._format_percentage(current.get('expected_return', 0)),
                     self._format_percentage(wo_metrics.get('expected_return', 0))]
                    + ([self._format_percentage(mo_metrics.get('expected_return', 0))] if has_market else [])
                )
                opt_table.append(
                    ['Risk (Vol)',
                     self._format_percentage(current.get('risk', 0)),
                     self._format_percentage(wo_metrics.get('risk', 0))]
                    + ([self._format_percentage(mo_metrics.get('risk', 0))] if has_market else [])
                )
                opt_table.append(
                    ['Sharpe',
                     self._format_number(current.get('sharpe_ratio', 0), decimals=3),
                     self._format_number(wo_metrics.get('sharpe_ratio', 0), decimals=3)]
                    + ([self._format_number(mo_metrics.get('sharpe_ratio', 0), decimals=3)] if has_market else [])
                )

                # optimization_table
                story.append(self._create_table(opt_table, ultra_compact=True))
                story.append(self._sp('tight'))
                # Caption: optimization_table
                story.append(Paragraph(
                    "Current = your portfolio as built. Weights-Opt = same assets, rebalanced for "
                    "better risk/return. Market-Opt = assets selected by the optimizer. "
                    "Higher Sharpe ratio means more return earned per unit of risk taken.",
                    self.styles['TableNote'],
                ))
                story.append(self._sp('table'))

            if MPL_AVAILABLE:
                try:
                    fig, ax = plt.subplots(figsize=(6.5, 3.8))
                    random_portfolios = (
                        opt.get('market_optimized_portfolio', {}).get('random_portfolios') or
                        opt.get('weights_optimized_portfolio', {}).get('random_portfolios')
                    )
                    if random_portfolios:
                        # Compute Sharpe for each random portfolio to drive the colormap
                        rp_risks = [p['risk'] for p in random_portfolios]
                        rp_rets = [p['return'] for p in random_portfolios]
                        rp_sharpes = [
                            p.get('sharpe', p.get('sharpe_ratio',
                                  r / max(rk, 1e-6)))
                            for p, r, rk in zip(random_portfolios, rp_rets, rp_risks)
                        ]
                        sc = ax.scatter(
                            rp_risks, rp_rets,
                            c=rp_sharpes, cmap='RdYlGn',
                            s=18, alpha=0.65, zorder=1,
                            vmin=min(rp_sharpes), vmax=max(rp_sharpes),
                        )
                        cbar = fig.colorbar(sc, ax=ax, shrink=0.8, pad=0.02)
                        cbar.set_label('Sharpe Ratio', fontsize=6)
                        cbar.ax.tick_params(labelsize=5)
                    frontier = (
                        opt.get('market_optimized_portfolio', {}).get('efficient_frontier') or
                        opt.get('weights_optimized_portfolio', {}).get('efficient_frontier')
                    )
                    if frontier:
                        ax.plot([p['risk'] for p in frontier], [p['return'] for p in frontier],
                                color='#2b6cb0', linewidth=2.2, zorder=2, label='Frontier')
                    if current:
                        ax.scatter(
                            current.get('risk', 0), current.get('expected_return', 0),
                            c='#e53e3e', s=220, marker='*',
                            edgecolors='white', linewidths=1.2, zorder=5, label='Current',
                        )
                    if wo_metrics:
                        ax.scatter(
                            wo_metrics.get('risk', 0), wo_metrics.get('expected_return', 0),
                            c='#3182ce', s=130, marker='D',
                            edgecolors='white', linewidths=1.0, zorder=5, label='Weights Opt',
                        )
                    if mo_metrics:
                        ax.scatter(
                            mo_metrics.get('risk', 0), mo_metrics.get('expected_return', 0),
                            c='#38a169', s=130, marker='s',
                            edgecolors='white', linewidths=1.0, zorder=5, label='Market Opt',
                        )
                    ax.set_title('Risk vs Return', fontsize=9, fontweight='bold')
                    ax.set_xlabel('Risk (Volatility)', fontsize=7)
                    ax.set_ylabel('Expected Return', fontsize=7)
                    ax.tick_params(axis='both', labelsize=6)
                    ax.grid(True, linestyle='--', alpha=0.35, zorder=0)
                    ax.legend(fontsize=6, loc='upper left', framealpha=0.85)
                    plt.tight_layout(pad=0.5)
                    chart_img = self._generate_plot(plt, width=6.5, height=3.8)
                    # Caption: frontier_chart
                    ef_caption = Paragraph(
                        "<b>Efficient Frontier:</b> The blue curve shows the optimal risk/return boundary. "
                        "Portfolios below the curve are inefficient — the same return is available with less risk. "
                        "The red star is your current position; markers show optimized alternatives.",
                        self.styles['ChartExplanation'],
                    )
                    story.append(KeepTogether([chart_img, self._sp('tight'), ef_caption]))
                    story.append(self._sp('chart'))
                except Exception as plot_e:
                    logger.warning(f"Failed to generate optimization plot: {plot_e}")

        # ── SECTION 6: STRESS TEST ANALYSIS ──────────────────────────────────
        if stress_sec_num:
            self._section_break(story)
            self._section_heading(story, str(stress_sec_num), "Stress Test Analysis")
            stress = data['stressTestResults']
            resilience = stress.get('resilience_score')
            if resilience is not None:
                resilience_label = (
                    "Excellent" if resilience >= 80 else
                    "Good" if resilience >= 60 else
                    "Fair" if resilience >= 40 else "Weak"
                )
                story.append(Paragraph(
                    f"<b>Resilience Score:</b> {self._format_number(resilience, decimals=0)}/100 ({resilience_label})",
                    self.styles['InsightCallout'],
                ))
                story.append(self._sp('tight'))

            scenarios = stress.get('scenarios') or stress.get('scenario_results') or {}
            if scenarios and MPL_AVAILABLE:
                try:
                    plt.figure(figsize=(6, 2.8))
                    names, impacts = [], []
                    for name, res in scenarios.items():
                        if isinstance(res, dict):
                            impact = res.get('portfolio_impact') or res.get('impact')
                            if impact is not None:
                                names.append(name.replace('_', ' ').title()[:20])
                                impacts.append(impact * 100)
                    if names:
                        sorted_indices = sorted(range(len(impacts)), key=lambda k: impacts[k])
                        names = [names[i] for i in sorted_indices]
                        impacts = [impacts[i] for i in sorted_indices]
                        plt.barh(names, impacts,
                                 color=['#e53e3e' if x < 0 else '#38a169' for x in impacts], height=0.55)
                        plt.title('Crisis Impact', fontsize=9, fontweight='bold')
                        plt.xlabel('Value Change (%)', fontsize=7)
                        plt.tick_params(axis='both', labelsize=6)
                        plt.grid(True, axis='x', linestyle='--', alpha=0.5)
                        plt.tight_layout(pad=0.5)
                        chart_img = self._generate_plot(plt, compact=True)
                        # Caption: stress_chart
                        stress_caption = Paragraph(
                            "<b>Scenario Impact:</b> Each bar shows the estimated change in portfolio value "
                            "under that historical crisis scenario. Red = potential loss, Green = gain. "
                            "A large red bar indicates high sensitivity to that type of market event.",
                            self.styles['ChartExplanation'],
                        )
                        story.append(KeepTogether([chart_img, self._sp('tight'), stress_caption]))
                        story.append(self._sp('chart'))
                except Exception as plot_e:
                    logger.warning(f"Failed to generate stress test plot: {plot_e}")

        # ── SECTION 7: TRANSACTION COSTS ─────────────────────────────────────
        self._section_break(story)
        self._section_heading(story, str(cost_sec_num), "Transaction Costs")

        cost_data = data.get('costData', {}) or {}
        if cost_data:
            cost_table_data = [['Component', 'Value', 'Impact']]
            setup = cost_data.get('setupCost') or cost_data.get('setup_cost')
            annual = cost_data.get('annualRebalancingCost') or cost_data.get('annual_rebalancing_cost')
            total_first = cost_data.get('totalFirstYearCost') or cost_data.get('total_first_year_cost')
            courtage = cost_data.get('courtageClass') or cost_data.get('courtage_class')
            if setup is not None:
                setup_pct = (float(setup) / portfolio_value * 100) if portfolio_value else 0
                cost_table_data.append(['Setup', self._format_number(float(setup), currency=True),
                                        f'{setup_pct:.2f}% (one-time)'])
            if annual is not None:
                annual_pct = (float(annual) / portfolio_value * 100) if portfolio_value else 0
                cost_table_data.append(['Annual Est.', self._format_number(float(annual), currency=True),
                                        f'{annual_pct:.2f}%/year'])
            if total_first is not None:
                first_pct = (float(total_first) / portfolio_value * 100) if portfolio_value else 0
                cost_table_data.append(['Year 1 Total', self._format_number(float(total_first), currency=True),
                                        f'{first_pct:.2f}% drag'])
            if courtage:
                cost_table_data.append(['Courtage Tier', str(courtage).capitalize(), 'Selected fee tier'])

            # costs_table
            story.append(self._create_table(
                cost_table_data,
                col_widths=[1.4 * inch, 2.2 * inch, 3.2 * inch],
                ultra_compact=True,
            ))
            story.append(self._sp('tight'))
            # Caption: costs_table
            story.append(Paragraph(
                "Setup cost is one-time. Annual cost recurs with each rebalance cycle. "
                "Annual costs above 1% compound meaningfully over time. "
                "Consider a lower courtage tier or reducing rebalancing frequency.",
                self.styles['TableNote'],
            ))
            story.append(self._sp('table'))
        else:
            story.append(Paragraph("No cost data available.", self.styles['CompactBody']))
            story.append(self._sp('table'))

        # ── SECTION 8: 5-YEAR PROJECTION (force page break — table + large chart) ──
        story.append(PageBreak())
        self._section_heading(story, str(proj_sec_num), "5-Year Projection")
        story.append(Paragraph(
            "Net growth after Swedish taxes and costs. Base Case = realistic planning; "
            "Pessimistic = stress-test your goals.",
            self.styles['MethodologyBody'],
        ))
        story.append(self._sp('tight'))

        projection_metrics = data.get('projectionMetrics') or {}
        portfolio_data = data.get('portfolio')

        # Resolve weights from various data structures
        weights = projection_metrics.get('weights') or {}
        if not weights and isinstance(portfolio_data, dict):
            weights = portfolio_data.get('weights') or {}
            if not weights and portfolio_data.get('allocations'):
                weights = {
                    a.get('symbol', a.get('ticker', '')): (a.get('allocation', 0) / 100.0)
                    for a in portfolio_data.get('allocations', [])
                    if a.get('symbol') or a.get('ticker')
                }
        if not weights and isinstance(portfolio_data, list):
            weights = {
                p.get('ticker', p.get('symbol', '')): p.get('allocation', 0)
                for p in portfolio_data if p.get('ticker') or p.get('symbol')
            }

        if run_five_year_projection and portfolio_value and weights:
            try:
                proj = run_five_year_projection(
                    initial_capital=float(portfolio_value),
                    weights={k: float(v) for k, v in weights.items() if v and k},
                    expected_return=float(projection_metrics.get('expectedReturn', metrics.get('expectedReturn', 0.08))),
                    risk=float(projection_metrics.get('risk', metrics.get('risk', 0.15))),
                    account_type=str(data.get('accountType', 'isk')),
                    tax_year=int(data.get('taxYear', datetime.now().year)),
                    courtage_class=(cost_data.get('courtageClass') or 'medium').lower(),
                    rebalancing_frequency='quarterly',
                )

                proj_table_data = [['Year', 'Optimistic', 'Base Case', 'Pessimistic']]
                for i, year in enumerate(proj.get('years', [])):
                    proj_table_data.append([
                        str(year),
                        self._format_number(proj['optimistic'][i], decimals=0, currency=True),
                        self._format_number(proj['base'][i], decimals=0, currency=True),
                        self._format_number(proj['pessimistic'][i], decimals=0, currency=True),
                    ])

                final_base = proj['base'][-1] if proj.get('base') else portfolio_value
                final_pess = proj['pessimistic'][-1] if proj.get('pessimistic') else portfolio_value
                base_growth = ((final_base / portfolio_value) - 1) * 100 if portfolio_value else 0
                pess_growth = ((final_pess / portfolio_value) - 1) * 100 if portfolio_value else 0

                # projection_table
                story.append(self._create_table(proj_table_data, ultra_compact=True))
                story.append(self._sp('tight'))
                # Caption: projection_table
                story.append(Paragraph(
                    f"Base: +{base_growth:.0f}% | Pessimistic: +{pess_growth:.0f}% over 5 years, "
                    "net of taxes and costs. If the pessimistic scenario falls short of your goal, "
                    "increase contributions or extend the time horizon.",
                    self.styles['TableNote'],
                ))
                story.append(self._sp('table'))

                if MPL_AVAILABLE:
                    plt.figure(figsize=(6, 2.6))
                    plt.plot(proj['years'], proj['optimistic'], '#38a169', linewidth=1.8, label='Optimistic')
                    plt.plot(proj['years'], proj['base'], '#3182ce', linewidth=2.2, label='Base')
                    plt.plot(proj['years'], proj['pessimistic'], '#e53e3e', linewidth=1.8, label='Pessimistic')
                    plt.title('5-Year Projection', fontsize=9, fontweight='bold')
                    plt.ylabel('Value (SEK)', fontsize=7)
                    plt.xlabel('Year', fontsize=7)
                    plt.tick_params(axis='both', labelsize=6)
                    plt.legend(fontsize=6)
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout(pad=0.5)
                    from matplotlib.ticker import FuncFormatter
                    def format_sek(x, pos):
                        if x >= 1e6: return f'{x/1e6:.1f}M'
                        if x >= 1e3: return f'{x/1e3:.0f}k'
                        return f'{x:.0f}'
                    plt.gca().yaxis.set_major_formatter(FuncFormatter(format_sek))
                    chart_img = self._generate_plot(plt, compact=True)
                    # Caption: projection_chart
                    proj_caption = Paragraph(
                        "<b>Projection Trajectory:</b> Green = Optimistic, Blue = Base Case, "
                        "Red = Pessimistic. The spread between scenarios reflects portfolio volatility. "
                        "All values are NET after Swedish taxes and estimated transaction costs each year.",
                        self.styles['ChartExplanation'],
                    )
                    story.append(KeepTogether([chart_img, self._sp('tight'), proj_caption]))
                    story.append(self._sp('chart'))
            except Exception as e:
                logger.warning(f"Could not add 5-year projection: {e}")

        # ── SECTION 9: RISK ANALYSIS ──────────────────────────────────────────
        self._section_break(story)
        self._section_heading(story, str(risk_sec_num), "Risk Analysis")

        if metrics:
            risk_table = [['Metric', 'Value', 'Rating']]
            if 'diversificationScore' in metrics:
                div_score = metrics['diversificationScore']
                div_rating = (
                    "Excellent" if div_score >= 80 else
                    "Good" if div_score >= 60 else
                    "Moderate" if div_score >= 40 else "Low"
                )
                risk_table.append(['Diversification', self._format_number(div_score, decimals=0), div_rating])
            if 'sharpeRatio' in metrics:
                sharpe = metrics['sharpeRatio']
                sharpe_rating = (
                    "Excellent" if sharpe >= 1.5 else
                    "Good" if sharpe >= 1.0 else
                    "Fair" if sharpe >= 0.5 else "Low"
                )
                risk_table.append(['Sharpe Ratio', self._format_number(sharpe, decimals=3), sharpe_rating])
            if 'risk' in metrics:
                risk_v = metrics['risk']
                risk_pct = risk_v * 100 if risk_v < 1 else risk_v
                risk_rating = (
                    "Low" if risk_pct < 10 else
                    "Moderate" if risk_pct < 20 else
                    "High" if risk_pct < 30 else "Very High"
                )
                risk_table.append(['Volatility', self._format_percentage(risk_v), risk_rating])

            # risk_table
            story.append(self._create_table(
                risk_table,
                col_widths=[2.0 * inch, 1.5 * inch, 2.0 * inch],
                ultra_compact=True,
            ))
            story.append(self._sp('tight'))
            # Caption: risk_table
            story.append(Paragraph(
                "Diversification above 70 = strong resistance to single-asset turbulence. "
                "Sharpe above 1.0 = good, above 1.5 = excellent. "
                "Volatility of 20% means the portfolio typically swings ±20% in a given year.",
                self.styles['MethodologyBody'],
            ))
            story.append(self._sp('table'))

        # Final build
        doc.build(story, canvasmaker=PageNumCanvas)
        buffer.seek(0)
        return buffer.getvalue()

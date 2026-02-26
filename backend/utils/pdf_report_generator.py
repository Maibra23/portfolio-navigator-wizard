#!/usr/bin/env python3
"""
PDF Report Generator
Generates academic-standard PDF reports for portfolios using reportlab.
Front matter: title page (i), TOC + List of Figures/Tables (ii), disclaimer/definitions (iii).
Body: sections 1–8 with numbered tables (Table 1–8) and figures (Figure 1–3).

CAPTION MAP (numbered):
  Table 1: Executive Summary    Table 2: Portfolio Holdings    Table 3: Tax Analysis
  Table 4: Account Comparison  Table 5: Optimization Metrics Table 6: Transaction Costs
  Table 7: Projection Values   Table 8: Risk Metrics
  Figure 1: Sector Allocation  Figure 2: Efficient Frontier  Figure 3: Five-Year Projection
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
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas

FRONT_MATTER_PAGES = 3


class PageNumCanvas(canvas.Canvas):
    """Minimal professional header (report name + date) and clean footer (Page X of Y)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        report_date = datetime.now().strftime("%Y-%m-%d")
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_page_info(page_count, report_date)
            super().showPage()
        super().save()

    def draw_page_info(self, page_count: int, report_date: str):
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor('#374151'))
        self.drawString(40, 802, "Portfolio Analysis Report")
        self.drawRightString(555, 802, report_date)
        self.setStrokeColor(colors.HexColor('#e5e7eb'))
        self.setLineWidth(0.5)
        self.line(40, 798, 555, 798)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor('#6b7280'))
        if self._pageNumber <= FRONT_MATTER_PAGES:
            roman_num = ['i', 'ii', 'iii'][self._pageNumber - 1]
            self.drawRightString(555, 22, roman_num)
        else:
            body_num = self._pageNumber - FRONT_MATTER_PAGES
            body_total = page_count - FRONT_MATTER_PAGES
            self.drawRightString(555, 22, f"Page {body_num} of {body_total}")
        self.line(40, 42, 555, 42)


class PDFReportGenerator:
    """
    Academic-standard PDF report generator (university thesis / institutional formatting).
    Front matter: title (i), TOC (ii), disclaimer/definitions (iii). Body: sections 1–8.
    """

    # Academic margins (inches) — 1.0" all sides
    MARGIN_LEFT = 1.0
    MARGIN_RIGHT = 1.0
    MARGIN_TOP = 1.0
    MARGIN_BOTTOM = 1.0

    # Academic spacing (inches) — APA 7th / IEEE style
    SPACE_BEFORE_SECTION = 0.40
    SPACE_AFTER_SECTION_HEADER = 0.20
    SPACE_AFTER_PARAGRAPH = 0.12
    SPACE_BEFORE_TABLE = 0.18
    SPACE_AFTER_TABLE = 0.18
    SPACE_BEFORE_FIGURE = 0.20
    SPACE_AFTER_FIGURE = 0.14
    SPACE_AFTER_CAPTION = 0.22
    SPACE_BEFORE_SUBSECTION = 0.25
    SPACE_AFTER_SUBSECTION_HEADER = 0.12
    SPACE_TIGHT = 0.06

    # Legacy _sp() mapping (chart/caption/section/header/table/tight)
    SPACE_AFTER_CHART = 0.10
    SPACE_CAPTION_TO_NEXT = 0.18

    # Chart dimensions (inches)
    CHART_WIDTH = 6.2
    CHART_HEIGHT = 2.8
    CHART_HEIGHT_LARGE = 3.2
    CHART_WIDTH_COMPACT = 5.5
    CHART_HEIGHT_COMPACT = 2.3

    # Usable page width (A4 8.27" minus 2" margins)
    PAGE_WIDTH_INCH = 6.27

    # Unified color palette for charts (brand consistency)
    CHART_COLORS = {
        'primary': '#2563eb',
        'positive': '#059669',
        'negative': '#dc2626',
        'neutral': '#6b7280',
        'text': '#1f2937',
    }

    # Stress test scenarios to include in PDF (only these two historical crises)
    # Includes variations from both API response names and display names
    ALLOWED_STRESS_SCENARIOS = {
        '2008_financial_crisis', 'financial_crisis_2008', 'financial_crisis', '2008_crisis',
        '2020_covid_crash', 'covid_crash', 'covid_2020', 'covid', 'covid19',
    }

    def __init__(self):
        self.page_size = A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        if MPL_AVAILABLE:
            matplotlib.rcParams.update({
                'figure.dpi': 300,
                'savefig.dpi': 300,
                'font.family': ['Helvetica', 'Arial', 'DejaVu Sans'],
                'lines.linewidth': 1.5,
                'axes.linewidth': 1.0,
                'text.antialiased': True,
            })

    # ── Spacing helpers ───────────────────────────────────────────────────────

    def _sp(self, space_type: str) -> Spacer:
        """Return a Spacer for the given context type (institutional spacing)."""
        mapping = {
            'section':   self.SPACE_BEFORE_SECTION * inch,
            'header':   self.SPACE_AFTER_SECTION_HEADER * inch,
            'paragraph': self.SPACE_AFTER_PARAGRAPH * inch,
            'table_before': self.SPACE_BEFORE_TABLE * inch,
            'table':    self.SPACE_AFTER_TABLE * inch,
            'figure_before': self.SPACE_BEFORE_FIGURE * inch,
            'figure':   self.SPACE_AFTER_FIGURE * inch,
            'caption':  self.SPACE_AFTER_CAPTION * inch,
            'chart':    self.SPACE_AFTER_CHART * inch,
            'tight':    self.SPACE_TIGHT * inch,
        }
        return Spacer(1, mapping.get(space_type, self.SPACE_AFTER_TABLE * inch))

    def _append_spacer(self, story: list, space_type: str) -> None:
        """Append a standard spacer to the story for consistent vertical rhythm."""
        story.append(self._sp(space_type))

    def _start_major_section(self, story: list, section_num: int, title: str, force_new_page: bool = False) -> None:
        """Begin a major numbered section. Use force_new_page=True for data-heavy sections (3, 5, 7)."""
        if force_new_page:
            story.append(PageBreak())
        story.append(Spacer(1, self.SPACE_BEFORE_SECTION * inch))
        story.append(Paragraph(f"{section_num}. {title}", self.styles['SectionHeading']))
        story.append(Spacer(1, self.SPACE_AFTER_SECTION_HEADER * inch))

    def _subsection_heading(self, story: list, title: str) -> None:
        """Add a subsection heading, then spacing before content."""
        story.append(Spacer(1, self.SPACE_BEFORE_SUBSECTION * inch))
        story.append(Paragraph(title, self.styles['SubsectionHeading']))
        story.append(Spacer(1, self.SPACE_AFTER_SUBSECTION_HEADER * inch))

    def _generate_executive_dashboard(self, data: Dict[str, Any]) -> List:
        """First-page dashboard: title, KPI cards (Value, Expected Return, Risk, Sharpe), allocation visual, performance summary."""
        story = []
        portfolio_name = (data.get('portfolioName') or 'Investment Portfolio').strip()
        title_case_name = portfolio_name.title() if portfolio_name else 'Investment Portfolio'
        report_date = datetime.now().strftime("%B %d, %Y")
        portfolio_value = data.get('portfolioValue', 0.0)
        metrics = data.get('metrics') or {}
        exp_ret = data.get('expectedReturn') if 'expectedReturn' in data else metrics.get('expectedReturn')
        risk_val = data.get('risk') if 'risk' in data else metrics.get('risk')
        sharpe_val = data.get('sharpeRatio') if 'sharpeRatio' in data else metrics.get('sharpeRatio')

        story.append(Spacer(1, 0.8 * inch))
        story.append(Paragraph("Portfolio Analysis Report", self.styles['TitlePageMain']))
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph(title_case_name, self.styles['TitlePageSubtitle']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"Report Date: {report_date}", self.styles['TitlePageDate']))
        story.append(Spacer(1, 0.35 * inch))

        kpi_data = [
            ['Value', 'Expected Return', 'Risk (Vol)', 'Sharpe Ratio'],
            [
                self._format_number(portfolio_value, decimals=0, currency=True),
                self._format_percentage(exp_ret) if exp_ret is not None else 'N/A',
                self._format_percentage(risk_val) if risk_val is not None else 'N/A',
                self._format_number(sharpe_val, decimals=3) if sharpe_val is not None else 'N/A',
            ],
        ]
        kpi_table = self._create_table(kpi_data, col_widths=[1.5 * inch] * 4, ultra_compact=True)
        story.append(kpi_table)
        story.append(Spacer(1, 0.3 * inch))

        portfolio = data.get('portfolio', [])
        if portfolio and MPL_AVAILABLE:
            try:
                sector_weights = {}
                for pos in portfolio:
                    alloc = pos.get('allocation', 0.0)
                    if alloc > 1:
                        alloc = alloc / 100.0
                    if alloc <= 0:
                        continue
                    sector = pos.get('sector', 'Unknown')
                    sector_weights[sector] = sector_weights.get(sector, 0.0) + alloc
                has_real_sectors = sector_weights and any(s != 'Unknown' for s in sector_weights.keys())
                plt.figure(figsize=(4, 2.2))
                if has_real_sectors:
                    labels = list(sector_weights.keys())
                    sizes = list(sector_weights.values())
                    plt.pie(sizes, labels=labels, autopct='%1.0f%%', startangle=140,
                            colors=plt.cm.Paired(range(len(labels))), textprops={'fontsize': 6})
                    plt.title('Allocation Overview', fontsize=8, fontweight='bold')
                else:
                    ticker_labels = []
                    ticker_sizes = []
                    for pos in portfolio:
                        a = pos.get('allocation', 0.0)
                        if a > 1:
                            a = a / 100.0
                        if a > 0:
                            ticker_labels.append(pos.get('ticker', pos.get('symbol', 'N/A')))
                            ticker_sizes.append(a)
                    if ticker_labels and ticker_sizes:
                        plt.pie(ticker_sizes, labels=ticker_labels, autopct='%1.0f%%', startangle=140,
                                colors=plt.cm.Paired(range(len(ticker_labels))), textprops={'fontsize': 5})
                        plt.title('Holdings Allocation', fontsize=8, fontweight='bold')
                    else:
                        plt.close()
                        raise ValueError("No allocation data")
                plt.axis('equal')
                plt.tight_layout(pad=0.3)
                chart_img = self._generate_plot(plt, width=4, height=2.2)
                story.append(chart_img)
                story.append(Spacer(1, 0.2 * inch))
            except Exception as e:
                logger.warning(f"Dashboard allocation chart skipped: {e}")

        story.append(Paragraph(
            "This report summarizes portfolio composition, Swedish tax impact, optimization results, "
            "and risk metrics. See following sections for methodology, detailed tables, and projections.",
            self.styles['MethodologyBody'],
        ))
        story.append(Spacer(1, 0.25 * inch))
        story.append(Paragraph("Prepared by Portfolio Navigator Wizard", self.styles['TitlePageID']))
        story.append(PageBreak())
        return story

    def _generate_front_matter(self, data: Dict[str, Any]) -> List:
        """Front matter: page i executive dashboard, page ii TOC + lists, page iii disclaimer/definitions."""
        story = []
        story.extend(self._generate_executive_dashboard(data))

        # Page ii: TOC
        story.append(Spacer(1, 1.5 * inch))
        story.append(Paragraph("TABLE OF CONTENTS", self.styles['TOCHeading']))
        story.append(Spacer(1, 0.3 * inch))
        toc_entries = [
            ("1. Executive Summary", "3"),
            ("2. Methodology & Assumptions", "3"),
            ("3. Portfolio Composition", "4"),
            ("4. Swedish Tax Analysis", "4"),
            ("5. Optimization Results", "5"),
            ("6. Transaction Costs", "6"),
            ("7. Five-Year Projection", "7"),
            ("8. Risk Analysis", "8"),
        ]
        for entry, page_num in toc_entries:
            toc_line = f"{entry}{'.' * 50}{page_num}"
            story.append(Paragraph(toc_line, self.styles['TOCEntry']))
            story.append(Spacer(1, 0.08 * inch))
        story.append(Spacer(1, 0.5 * inch))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e0')))
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph("LIST OF FIGURES", self.styles['TOCSubHeading']))
        story.append(Spacer(1, 0.15 * inch))
        for fig, page_num in [("Figure 1: Sector Allocation", "4"), ("Figure 2: Efficient Frontier", "6"), ("Figure 3: Five-Year Projection", "7")]:
            story.append(Paragraph(f"{fig}{'.' * 45}{page_num}", self.styles['TOCFigure']))
            story.append(Spacer(1, 0.06 * inch))
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph("LIST OF TABLES", self.styles['TOCSubHeading']))
        story.append(Spacer(1, 0.15 * inch))
        table_entries = [
            ("Table 1: Executive Summary", "3"), ("Table 2: Portfolio Holdings", "4"), ("Table 3: Tax Analysis", "5"),
            ("Table 4: Account Comparison", "5"), ("Table 5: Optimization Metrics", "6"), ("Table 6: Transaction Costs", "6"),
            ("Table 7: Projection Values", "7"), ("Table 8: Risk Metrics", "8"),
        ]
        for tbl, page_num in table_entries:
            story.append(Paragraph(f"{tbl}{'.' * 45}{page_num}", self.styles['TOCFigure']))
            story.append(Spacer(1, 0.06 * inch))
        story.append(PageBreak())

        # Page iii: Disclaimer & definitions
        story.append(Spacer(1, 1.5 * inch))
        story.append(Paragraph("DISCLAIMER", self.styles['DisclaimerHeading']))
        story.append(Spacer(1, 0.2 * inch))
        disclaimer_text = (
            "This report is generated for informational and educational purposes only. "
            "It does not constitute financial advice, investment advice, tax advice, or any "
            "recommendation to buy or sell securities. Historical performance data presented "
            "herein is not indicative of future results. All projections and scenario analyses "
            "are based on assumptions that may not materialize.<br/><br/>"
            "The Swedish tax calculations reflect legislation as of the report date and are "
            "subject to change. Consult a qualified financial advisor and tax professional "
            "before making investment decisions. Portfolio Navigator Wizard and its affiliates "
            "assume no liability for losses resulting from the use of this report."
        )
        story.append(Paragraph(disclaimer_text, self.styles['DisclaimerBody']))
        story.append(Spacer(1, 0.4 * inch))
        story.append(Paragraph("KEY DEFINITIONS", self.styles['DisclaimerHeading']))
        story.append(Spacer(1, 0.2 * inch))
        definitions = [
            "<b>Schablonbeskattning:</b> Swedish flat-rate capital taxation applied annually to ISK and KF accounts, based on a percentage of capital value.",
            "<b>Expected Return:</b> Annualized historical return calculated from 3–5 years of daily price data.",
            "<b>Risk (Volatility):</b> Standard deviation of historical returns, representing typical annual price fluctuation.",
            "<b>Sharpe Ratio:</b> Risk-adjusted return metric; higher values indicate better return per unit of risk taken.",
            "<b>Efficient Frontier:</b> The curve of optimal portfolios offering maximum return for each level of risk.",
        ]
        for definition in definitions:
            story.append(Paragraph(definition, self.styles['DefinitionBody']))
            story.append(Spacer(1, 0.08 * inch))
        story.append(Spacer(1, 0.4 * inch))
        story.append(Paragraph("DATA SOURCES & METHODOLOGY", self.styles['DisclaimerHeading']))
        story.append(Spacer(1, 0.2 * inch))
        methodology_summary = (
            "Historical price data is sourced from Yahoo Finance API. Tax rates reflect official "
            "Skatteverket (Swedish Tax Agency) publications. Transaction cost estimates are based "
            "on standard broker fee schedules in Sweden.<br/><br/>"
            "Portfolio optimization uses Modern Portfolio Theory (Markowitz mean-variance optimization). "
            "Projections compound returns annually after deducting Swedish taxes and estimated "
            "transaction costs. All figures are denominated in Swedish Kronor (SEK)."
        )
        story.append(Paragraph(methodology_summary, self.styles['DisclaimerBody']))
        story.append(PageBreak())
        return story

    # ── Style setup ───────────────────────────────────────────────────────────

    def _setup_custom_styles(self):
        """Institutional typography: Report Title (24pt) > Section (15pt) > Subsection (12pt) > Body (10pt) > Table/Caption (8–10pt)."""
        # Report title (front matter)
        self.styles.add(ParagraphStyle(
            name='TitlePageMain',
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=0, spaceBefore=0,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=29,
        ))
        self.styles.add(ParagraphStyle(
            name='TitlePageSubtitle',
            fontSize=18,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=0, spaceBefore=0,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=22,
        ))
        self.styles.add(ParagraphStyle(
            name='TitlePageBody',
            fontSize=11,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=0, spaceBefore=0,
            alignment=TA_CENTER,
            fontName='Helvetica',
            leading=14,
        ))
        self.styles.add(ParagraphStyle(
            name='TitlePageDate',
            fontSize=10,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=0, spaceBefore=0,
            alignment=TA_CENTER,
            fontName='Helvetica',
            leading=13,
        ))
        self.styles.add(ParagraphStyle(
            name='TitlePageID',
            fontSize=9,
            textColor=colors.HexColor('#718096'),
            spaceAfter=0, spaceBefore=0,
            alignment=TA_CENTER,
            fontName='Helvetica',
            leading=11,
        ))
        # TOC
        self.styles.add(ParagraphStyle(
            name='TOCHeading',
            fontSize=16,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=0, spaceBefore=0,
            fontName='Helvetica-Bold',
            leading=19,
        ))
        self.styles.add(ParagraphStyle(
            name='TOCEntry',
            fontSize=11,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=0, spaceBefore=0,
            fontName='Helvetica',
            leading=14,
        ))
        self.styles.add(ParagraphStyle(
            name='TOCSubHeading',
            fontSize=13,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=0, spaceBefore=0,
            fontName='Helvetica-Bold',
            leading=16,
        ))
        self.styles.add(ParagraphStyle(
            name='TOCFigure',
            fontSize=10,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=0, spaceBefore=0,
            fontName='Helvetica',
            leading=13,
        ))
        # Disclaimer / definitions
        self.styles.add(ParagraphStyle(
            name='DisclaimerHeading',
            fontSize=13,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=0, spaceBefore=0,
            fontName='Helvetica-Bold',
            leading=16,
        ))
        self.styles.add(ParagraphStyle(
            name='DisclaimerBody',
            fontSize=9,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=0, spaceBefore=0,
            fontName='Helvetica',
            leading=12,
            alignment=TA_JUSTIFY,
        ))
        self.styles.add(ParagraphStyle(
            name='DefinitionBody',
            fontSize=9,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=0, spaceBefore=0,
            fontName='Helvetica',
            leading=12,
            leftIndent=10,
            firstLineIndent=-10,
        ))
        # Body: section headings and text
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            fontSize=15,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=0, spaceBefore=0,
            fontName='Helvetica-Bold',
            leading=18,
        ))
        self.styles.add(ParagraphStyle(
            name='SubsectionHeading',
            fontSize=12,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=0, spaceBefore=0,
            fontName='Helvetica-Bold',
            leading=15,
        ))
        self.styles.add(ParagraphStyle(
            name='AcademicBody',
            fontSize=10,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=0, spaceBefore=0,
            fontName='Helvetica',
            leading=13,
            alignment=TA_JUSTIFY,
        ))
        self.styles.add(ParagraphStyle(
            name='TableCaptionAbove',
            fontSize=10,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=0, spaceBefore=0,
            fontName='Helvetica',
            leading=13,
        ))
        self.styles.add(ParagraphStyle(
            name='FigureCaption',
            fontSize=9,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=0, spaceBefore=0,
            fontName='Helvetica',
            leading=12,
            alignment=TA_JUSTIFY,
        ))
        self.styles.add(ParagraphStyle(
            name='TableNote',
            fontSize=8.5,
            textColor=colors.HexColor('#718096'),
            spaceAfter=0, spaceBefore=0,
            fontName='Helvetica-Oblique',
            leading=11,
        ))
        # Legacy/body helpers
        self.styles.add(ParagraphStyle(
            name='ReportBody',
            parent=self.styles['Normal'],
            fontSize=8.5,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=0, spaceBefore=0,
            leading=11,
            firstLineIndent=0,
        ))
        self.styles.add(ParagraphStyle(
            name='CompactBody',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=0, spaceBefore=0,
            leading=10,
        ))
        self.styles.add(ParagraphStyle(
            name='MethodologyBody',
            parent=self.styles['Normal'],
            fontSize=8.5,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=0, spaceBefore=0,
            leading=11,
            leftIndent=8,
            rightIndent=8,
        ))
        self.styles.add(ParagraphStyle(
            name='InsightCallout',
            parent=self.styles['Normal'],
            fontSize=8.5,
            textColor=colors.HexColor('#2b6cb0'),
            spaceAfter=0, spaceBefore=0,
            leftIndent=6,
            leading=11,
        ))
        self.styles.add(ParagraphStyle(
            name='InlineMetric',
            parent=self.styles['Normal'],
            fontSize=8.5,
            leading=10,
            spaceAfter=0, spaceBefore=0,
        ))

    # ── Table helper ──────────────────────────────────────────────────────────

    def _create_table(self, data: List[List[str]], col_widths: Optional[List[float]] = None,
                      compact: bool = True, ultra_compact: bool = False) -> Table:
        """Create a styled table; splits across pages with header row repeated."""
        if col_widths is None and data:
            col_widths = self._calculate_optimal_column_widths(data)
        if col_widths is None:
            col_widths = [self.PAGE_WIDTH_INCH * inch / max(1, len(data[0]))] * len(data[0]) if data else []
        repeat_rows = 1 if len(data) > 1 else 0
        table = Table(data, colWidths=col_widths, repeatRows=repeat_rows)
        # Keep narrow tables left-aligned (e.g., Tax-Free Breakdown) instead of centered.
        table.hAlign = 'LEFT'

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

    def _create_numbered_table(self, table_num: int, title: str, data: List[List[str]],
                               note: str = None, **kwargs) -> List:
        """Academically formatted table: caption above, table, optional note below. Caller adds SPACE_AFTER_TABLE."""
        elements = []
        caption_above = f"<b>Table {table_num}:</b> {title}"
        elements.append(Paragraph(caption_above, self.styles['TableCaptionAbove']))
        elements.append(Spacer(1, self.SPACE_TIGHT * inch))
        table = self._create_table(data, **kwargs)
        elements.append(table)
        if note:
            elements.append(Spacer(1, self.SPACE_TIGHT * inch))
            elements.append(Paragraph(f"<i>Note:</i> {note}", self.styles['TableNote']))
        return elements

    def _create_numbered_figure(self, figure_num: int, title: str, chart_image: Image, caption: str) -> List:
        """Academically formatted figure: chart then caption below, kept together. Caller adds SPACE_AFTER_CAPTION."""
        elements = []
        elements.append(chart_image)
        elements.append(Spacer(1, self.SPACE_AFTER_FIGURE * inch))
        caption_text = f"<b>Figure {figure_num}:</b> {title}. {caption}"
        elements.append(Paragraph(caption_text, self.styles['FigureCaption']))
        return [KeepTogether(elements)]

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

    def _extract_stress_impact(self, scenario_result: Any) -> Optional[float]:
        """Extract scenario impact for charts. Prefers metrics.max_drawdown (peak-to-trough drawdown, negative for loss)."""
        if not isinstance(scenario_result, dict):
            return None
        metrics = scenario_result.get('metrics', {})
        if isinstance(metrics, dict) and metrics.get('max_drawdown') is not None:
            return float(metrics['max_drawdown'])
        for key in ('portfolio_impact', 'impact', 'value_change', 'value_change_pct'):
            value = scenario_result.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        if isinstance(metrics, dict):
            for key in ('total_return', 'worst_month_return'):
                value = metrics.get(key)
                if isinstance(value, (int, float)):
                    return float(value)
        return None

    def _is_allowed_stress_scenario(self, scenario_name: str) -> bool:
        """Check if scenario should be included in PDF (only COVID and 2008 Financial Crisis)."""
        normalized = scenario_name.lower().replace(' ', '_').replace('-', '_')
        return normalized in self.ALLOWED_STRESS_SCENARIOS

    def _filter_stress_scenarios(self, scenarios: Dict[str, Any]) -> Dict[str, Any]:
        """Filter scenarios to only include COVID and 2008 Financial Crisis."""
        return {
            name: data for name, data in scenarios.items()
            if self._is_allowed_stress_scenario(name)
        }

    def _format_scenario_name(self, scenario_name: str) -> str:
        """Format scenario name for display (e.g., 'covid19' -> '2020 COVID Crash')."""
        normalized = scenario_name.lower().replace(' ', '_').replace('-', '_')
        # Mapping from API/internal names to display names
        display_names = {
            'covid19': '2020 COVID Crash',
            'covid': '2020 COVID Crash',
            'covid_2020': '2020 COVID Crash',
            'covid_crash': '2020 COVID Crash',
            '2020_covid_crash': '2020 COVID Crash',
            '2008_crisis': '2008 Financial Crisis',
            '2008_financial_crisis': '2008 Financial Crisis',
            'financial_crisis': '2008 Financial Crisis',
            'financial_crisis_2008': '2008 Financial Crisis',
        }
        return display_names.get(normalized, scenario_name.replace('_', ' ').title())

    # ── Plot helpers ──────────────────────────────────────────────────────────

    def _generate_plot(self, plt_obj, width: float = None, height: float = None,
                       compact: bool = False, large: bool = False) -> Image:
        """Convert matplotlib plot to reportlab Image."""
        img_buffer = BytesIO()
        plt_obj.savefig(img_buffer, format='png', bbox_inches='tight', dpi=300,
                        facecolor='white', edgecolor='none', pad_inches=0.1,
                        transparent=False)
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
        plt_obj.savefig(img_buffer, format='png', bbox_inches='tight', dpi=300,
                        facecolor='white', edgecolor='none', pad_inches=0.1,
                        transparent=False)
        img_buffer.seek(0)
        plt_obj.close()
        return base64.b64encode(img_buffer.getvalue()).decode('utf-8')

    def _save_fig_svg_base64(self, plt_obj) -> str:
        """Save figure to SVG in a buffer, return base64 string. Does not close the figure."""
        svg_buffer = BytesIO()
        plt_obj.savefig(svg_buffer, format='svg', bbox_inches='tight',
                        facecolor='white', edgecolor='none', pad_inches=0.1)
        svg_buffer.seek(0)
        return base64.b64encode(svg_buffer.getvalue()).decode('utf-8')

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

        # 1. Portfolio composition: sector allocation or fallback to holdings allocation (exclude 0% positions)
        try:
            sector_weights = {}
            for pos in portfolio:
                weight = pos.get('allocation', 0.0)
                if weight > 1:
                    weight = weight / 100.0
                if weight <= 0:
                    continue
                sector = pos.get('sector', 'Unknown')
                sector_weights[sector] = sector_weights.get(sector, 0.0) + weight
            has_real_sectors = sector_weights and any(
                s != 'Unknown' for s in sector_weights.keys()
            )
            if portfolio:
                plt.figure(figsize=(10, 6))
                if has_real_sectors:
                    labels = list(sector_weights.keys())
                    sizes = list(sector_weights.values())
                    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140,
                            colors=plt.cm.Paired(range(len(labels))))
                    plt.title('Portfolio Sector Allocation')
                    filename = "sector_allocation.png"
                else:
                    ticker_labels = []
                    ticker_sizes = []
                    for pos in portfolio:
                        ticker = pos.get('ticker', pos.get('symbol', 'N/A'))
                        alloc = pos.get('allocation', 0.0)
                        if alloc > 1:
                            alloc = alloc / 100.0
                        if alloc > 0:
                            ticker_labels.append(ticker)
                            ticker_sizes.append(alloc)
                    if ticker_labels and ticker_sizes:
                        plt.pie(ticker_sizes, labels=ticker_labels, autopct='%1.1f%%', startangle=140,
                                colors=plt.cm.Paired(range(len(ticker_labels))))
                        plt.title('Portfolio Holdings Allocation')
                        filename = "portfolio_composition.png"
                    else:
                        plt.close()
                        raise ValueError("No allocation data")
                plt.axis('equal')
                svg_content = self._save_fig_svg_base64(plt)
                plots.append({"filename": filename.replace(".png", ".svg"), "content": svg_content, "size": len(svg_content)})
                content = self._generate_plot_base64(plt)
                plots.append({"filename": filename, "content": content, "size": len(content)})
        except Exception as e:
            logger.warning(f"Failed to generate composition plot for ZIP: {e}")

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
                                c=self.CHART_COLORS['negative'], s=100, marker='*', label='Current')
                weights_opt = (opt.get('weights_optimized_portfolio') or {}).get('optimized_portfolio', {}).get('metrics', {})
                if weights_opt:
                    plt.scatter(weights_opt.get('risk', 0), weights_opt.get('expected_return', 0),
                                c=self.CHART_COLORS['primary'], s=80, marker='D', label='Weights Optimized')
                market_opt = (opt.get('market_optimized_portfolio') or {}).get('optimized_portfolio', {}).get('metrics', {})
                if market_opt:
                    plt.scatter(market_opt.get('risk', 0), market_opt.get('expected_return', 0),
                                c=self.CHART_COLORS['positive'], s=80, marker='s', label='Market Optimized')
                plt.title('Portfolio Optimization: Risk vs Return')
                plt.xlabel('Risk (Volatility)')
                plt.ylabel('Expected Return')
                plt.legend()
                plt.grid(True, linestyle='--', alpha=0.7)
                svg_content = self._save_fig_svg_base64(plt)
                plots.append({"filename": "optimization_frontier.svg", "content": svg_content, "size": len(svg_content)})
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
                        impact = self._extract_stress_impact(res)
                        if impact is not None:
                            names.append(name.replace('_', ' ').title())
                            impacts.append(float(impact) * 100)
                    if names:
                        plt.figure(figsize=(10, 6))
                        # Convert to positive values (magnitude) since drawdowns are always losses
                        impacts_magnitude = [abs(x) for x in impacts]
                        sorted_indices = sorted(range(len(impacts_magnitude)), key=lambda k: impacts_magnitude[k], reverse=True)
                        names = [names[i] for i in sorted_indices]
                        impacts_magnitude = [impacts_magnitude[i] for i in sorted_indices]
                        plt.barh(names, impacts_magnitude, color=self.CHART_COLORS['negative'])
                        plt.axvline(x=0, color=self.CHART_COLORS['neutral'], linewidth=0.8, alpha=0.7)
                        plt.title('Peak-to-Trough Drawdown by Scenario')
                        plt.xlabel('Drawdown Magnitude (%)')
                        plt.grid(True, axis='x', linestyle='--', alpha=0.7)
                        plt.tight_layout(pad=0.5)
                        svg_content = self._save_fig_svg_base64(plt)
                        plots.append({"filename": "stress_test_impact.svg", "content": svg_content, "size": len(svg_content)})
                        content = self._generate_plot_base64(plt)
                        plots.append({"filename": "stress_test_impact.png", "content": content, "size": len(content)})
                    first_with_series = None
                    for name, res in scenarios.items():
                        if isinstance(res, dict):
                            perf = res.get('monthly_performance') or []
                            if perf and len(perf) > 0:
                                first_with_series = (name, res)
                                break
                    if first_with_series:
                        try:
                            scenario_name, scenario_data = first_with_series
                            perf = scenario_data.get('monthly_performance', [])
                            months = [p.get('month', '') for p in perf if p.get('month')]
                            values = [float(p.get('value', 0)) for p in perf]
                            if months and values and len(months) == len(values):
                                base = values[0] if values[0] != 0 else 1.0
                                indexed = [(v / base) * 100 for v in values]
                                plt.figure(figsize=(10, 5))
                                plt.plot(range(len(months)), indexed, color=self.CHART_COLORS['primary'], linewidth=2)
                                plt.axhline(y=100, color=self.CHART_COLORS['neutral'], linestyle='--', linewidth=0.8, alpha=0.7)
                                plt.title('Portfolio Value Over Time (Stress Scenario)')
                                plt.ylabel('Value (indexed to 100)')
                                plt.xlabel('Month')
                                step = max(1, len(months) // 10)
                                plt.xticks(range(0, len(months), step), [months[i] for i in range(0, len(months), step)], rotation=45, ha='right')
                                plt.grid(True, alpha=0.3)
                                plt.tight_layout(pad=0.5)
                                label = scenario_name.replace('_', ' ').title().replace(' ', '_')
                                svg_content = self._save_fig_svg_base64(plt)
                                plots.append({"filename": f"stress_test_portfolio_over_time_{label}.svg", "content": svg_content, "size": len(svg_content)})
                                content = self._generate_plot_base64(plt)
                                plots.append({"filename": f"stress_test_portfolio_over_time_{label}.png", "content": content, "size": len(content)})
                        except Exception as timeline_e:
                            logger.warning(f"Failed to generate stress portfolio-over-time plot for ZIP: {timeline_e}")
            except Exception as e:
                logger.warning(f"Failed to generate stress test plot for ZIP: {e}")

        # 4. 5-Year Projection
        projection_metrics = data.get('projectionMetrics') or {}
        portfolio_data = data.get('portfolio')
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
                p.get('ticker', p.get('symbol', '')): (p.get('allocation', 0) / 100.0 if (p.get('allocation', 0) > 1) else p.get('allocation', 0))
                for p in portfolio_data if p.get('ticker') or p.get('symbol')
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
                plt.plot(proj['years'], proj['optimistic'], color=self.CHART_COLORS['positive'], linestyle='-', marker='o', label='Optimistic')
                plt.plot(proj['years'], proj['base'], color=self.CHART_COLORS['primary'], linestyle='-', marker='o', label='Base Case')
                plt.plot(proj['years'], proj['pessimistic'], color=self.CHART_COLORS['negative'], linestyle='-', marker='o', label='Pessimistic')
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
                svg_content = self._save_fig_svg_base64(plt)
                plots.append({"filename": "five_year_projection.svg", "content": svg_content, "size": len(svg_content)})
                content = self._generate_plot_base64(plt)
                plots.append({"filename": "five_year_projection.png", "content": content, "size": len(content)})
            except Exception as e:
                logger.warning(f"Failed to generate projection plot for ZIP: {e}")

        return plots

    # ── Main report ───────────────────────────────────────────────────────────

    def generate_portfolio_report(self, data: Dict[str, Any]) -> bytes:
        """Generate academic-standard PDF report with front matter and numbered sections 1–8."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=self.page_size,
            leftMargin=self.MARGIN_LEFT * inch,
            rightMargin=self.MARGIN_RIGHT * inch,
            topMargin=self.MARGIN_TOP * inch,
            bottomMargin=self.MARGIN_BOTTOM * inch,
        )
        story = []
        portfolio_value = data.get('portfolioValue', 0.0)
        account_type = data.get('accountType', 'N/A')
        tax_year = data.get('taxYear', datetime.now().year)
        metrics = data.get('metrics') or {}
        cost_data = data.get('costData', {}) or {}

        story.extend(self._generate_front_matter(data))

        # ── Section 1: Executive Summary ─────────────────────────────────────
        self._start_major_section(story, 1, "Executive Summary", force_new_page=False)
        exp_ret = data.get('expectedReturn') if 'expectedReturn' in data else metrics.get('expectedReturn')
        risk_val = data.get('risk') if 'risk' in data else metrics.get('risk')
        sharpe_val = data.get('sharpeRatio') if 'sharpeRatio' in data else metrics.get('sharpeRatio')
        summary_data = [
            ['Portfolio Value', self._format_number(portfolio_value, currency=True), 'Account Type', account_type],
            ['Tax Year', str(tax_year), 'Expected Return',
             self._format_percentage(exp_ret) if exp_ret is not None else 'N/A'],
            ['Risk (Vol)', self._format_percentage(risk_val) if risk_val is not None else 'N/A',
             'Sharpe Ratio', self._format_number(sharpe_val, decimals=3) if sharpe_val is not None else 'N/A'],
        ]
        table1 = self._create_numbered_table(
            1, "Executive Summary",
            summary_data,
            note="Expected return and risk drive the projection range; a higher Sharpe ratio indicates better return per unit of risk. Use these KPIs to gauge whether the portfolio aligns with your goals and tolerance for volatility.",
            col_widths=[1.6 * inch, 1.8 * inch, 1.4 * inch, 1.8 * inch],
            ultra_compact=True,
        )
        story.extend(table1)
        story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))

        # ── Section 2: Methodology & Assumptions ─────────────────────────────
        self._start_major_section(story, 2, "Methodology & Assumptions", force_new_page=False)
        self._subsection_heading(story, "Data Sources")
        story.append(Spacer(1, self.SPACE_BEFORE_TABLE * inch))
        data_sources = [
            ['Source', 'Description'],
            ['Historical Prices', '3–5 years daily data → expected returns and risk metrics'],
            ['Tax Rates', 'Skatteverket official rates (schablonränta for ISK/KF, 30% gains for AF)'],
            ['Transaction Costs', 'Broker courtage schedules (Start, Mini, Small, Medium, Fixed Price tiers)'],
        ]
        story.append(self._create_table(data_sources, col_widths=[1.6 * inch, 4.0 * inch], ultra_compact=True))
        story.append(Spacer(1, self.SPACE_TIGHT * inch))
        story.append(Paragraph(
            "All projections use end-of-day historical prices. Tax rates reflect current legislation "
            "and may change. Consult your broker's fee schedule for accurate cost estimates.",
            self.styles['MethodologyBody'],
        ))
        story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))
        self._subsection_heading(story, "Projection Scenarios")
        story.append(Spacer(1, self.SPACE_BEFORE_TABLE * inch))
        proj_method_data = [
            ['Scenario', 'Calculation', 'Use Case'],
            ['Optimistic', 'Return + Volatility', 'Upper bound — plan upside potential'],
            ['Base Case', 'Expected Return', 'Most likely — central planning figure'],
            ['Pessimistic', 'Return − 50% Vol', 'Conservative — stress test goals'],
        ]
        story.append(self._create_table(
            proj_method_data,
            col_widths=[1.2 * inch, 1.6 * inch, 3.2 * inch],
            ultra_compact=True,
        ))
        story.append(Spacer(1, self.SPACE_TIGHT * inch))
        story.append(Paragraph(
            "Each year deducts tax and costs, then compounds net return for realistic wealth projection.",
            self.styles['MethodologyBody'],
        ))
        story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))
        self._subsection_heading(story, "Limitations")
        story.append(Spacer(1, self.SPACE_BEFORE_TABLE * inch))
        limitations_data = [
            ['Limitation', 'Impact'],
            ['Historical ≠ Future', 'Past returns do not guarantee future performance'],
            ['Static Assumptions', 'Current holdings maintained; trading changes outcomes'],
            ['Tax Law Changes', 'Rates based on current legislation; subject to revision'],
            ['Estimation Only', 'Educational purposes; consult a financial advisor'],
        ]
        story.append(self._create_table(limitations_data, col_widths=[1.6 * inch, 4.0 * inch], ultra_compact=True))
        story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))

        # ── Section 3: Portfolio Composition (new page) ───────────────────────
        self._start_major_section(story, 3, "Portfolio Composition", force_new_page=True)
        story.append(Paragraph(
            "Allocation below shows where capital is deployed. High concentration in a single holding or sector "
            "amplifies drawdown risk in downturns; spreading across assets and industries generally improves "
            "resilience when one segment underperforms.",
            self.styles['AcademicBody'],
        ))
        story.append(Spacer(1, self.SPACE_AFTER_PARAGRAPH * inch))
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
                if allocation > 0:
                    sector = pos.get('sector', 'Unknown')
                    sector_weights[sector] = sector_weights.get(sector, 0.0) + allocation
            story.append(Spacer(1, self.SPACE_BEFORE_TABLE * inch))
            table2 = self._create_numbered_table(
                2, "Portfolio Holdings",
                comp_data,
                note="Concentration above 20–25% in a single holding increases single-stock risk. Review positions with outsized weight relative to conviction.",
                compact=True,
            )
            story.extend(table2)
            story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))
            if MPL_AVAILABLE and portfolio:
                try:
                    has_real_sectors = sector_weights and any(
                        s != 'Unknown' for s in sector_weights.keys()
                    )
                    story.append(Spacer(1, self.SPACE_BEFORE_FIGURE * inch))
                    plt.figure(figsize=(6, 3.2))
                    if has_real_sectors:
                        labels = list(sector_weights.keys())
                        sizes = list(sector_weights.values())
                        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140,
                                colors=plt.cm.Paired(range(len(labels))), textprops={'fontsize': 7})
                        plt.title('Sector Allocation', fontsize=9, fontweight='bold')
                        caption = (
                            "Each slice shows the combined allocation to that industry. "
                            "Exposure above 40% in one sector creates industry-specific concentration risk. "
                            "A spread of 10–25% per sector generally improves stability across market cycles."
                        )
                        fig_title = "Sector Allocation"
                    else:
                        ticker_labels = []
                        ticker_sizes = []
                        for pos in portfolio:
                            ticker = pos.get('ticker', pos.get('symbol', 'N/A'))
                            alloc = pos.get('allocation', 0.0)
                            if alloc > 1:
                                alloc = alloc / 100.0
                            if alloc > 0:
                                ticker_labels.append(ticker)
                                ticker_sizes.append(alloc)
                        if ticker_labels and ticker_sizes:
                            plt.pie(ticker_sizes, labels=ticker_labels, autopct='%1.1f%%', startangle=140,
                                    colors=plt.cm.Paired(range(len(ticker_labels))), textprops={'fontsize': 6})
                            plt.title('Portfolio Holdings Allocation', fontsize=9, fontweight='bold')
                            caption = (
                                "Allocation by holding. Concentration above 20–25% in a single name "
                                "increases single-stock risk; consider rebalancing or diversification."
                            )
                            fig_title = "Portfolio Holdings Allocation"
                        else:
                            plt.close()
                            raise ValueError("No allocation data")
                    plt.axis('equal')
                    plt.tight_layout(pad=0.5)
                    chart_img = self._generate_plot(plt, compact=True)
                    fig1 = self._create_numbered_figure(1, fig_title, chart_img, caption)
                    story.extend(fig1)
                    story.append(Spacer(1, self.SPACE_AFTER_CAPTION * inch))
                except Exception as plot_e:
                    logger.warning(f"Failed to generate composition chart: {plot_e}")
        else:
            story.append(Paragraph("No portfolio data available.", self.styles['CompactBody']))
            story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))

        # ── Section 4: Swedish Tax Analysis ──────────────────────────────────
        self._start_major_section(story, 4, "Swedish Tax Analysis", force_new_page=False)
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
            story.append(Spacer(1, self.SPACE_BEFORE_TABLE * inch))
            table3 = self._create_numbered_table(
                3, "Tax Analysis",
                tax_table_data,
                note="ISK/KF: Schablonbeskattning — a flat annual tax on capital, regardless of whether gains are realized. AF: 30% tax applies only when assets are sold.",
                col_widths=[1.6 * inch, 2.0 * inch, 2.4 * inch],
                ultra_compact=True,
            )
            story.extend(table3)
            story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))
        else:
            story.append(Paragraph("No tax data available.", self.styles['CompactBody']))
            story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))
        tax_comparison = data.get('taxComparison')
        if tax_comparison and len(tax_comparison) > 0:
            self._subsection_heading(story, "Account Type Comparison")
            story.append(Spacer(1, self.SPACE_BEFORE_TABLE * inch))
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
            table4 = self._create_numbered_table(
                4, "Account Comparison",
                comp_table_data,
                note="★ = lowest annual tax for this portfolio size and return. Switching account types involves transfer friction; factor in time horizon before moving.",
                col_widths=[1.4 * inch, 1.6 * inch, 1.4 * inch, 1.6 * inch],
                ultra_compact=True,
            )
            story.extend(table4)
            story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))

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
                story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))
            else:
                story.append(Spacer(1, self.SPACE_BEFORE_TABLE * inch))
                breakdown_table = [
                    ['Component', 'Amount', 'Share'],
                    ['Tax-Free', self._format_number(tax_free_amount, currency=True),
                     self._format_percentage(tax_free_data.get('taxFreePercentage', 0))],
                    ['Taxable', self._format_number(taxable_amount, currency=True),
                     self._format_percentage(tax_free_data.get('taxablePercentage', 0))],
                ]
                story.append(self._create_table(
                    breakdown_table,
                    col_widths=[1.4 * inch, 2.0 * inch, 1.4 * inch],
                    ultra_compact=True,
                ))
                story.append(Spacer(1, self.SPACE_TIGHT * inch))
                story.append(Paragraph(
                    f"Tax-free level {tax_year}: {self._format_number(tax_free_level, currency=True)}",
                    self.styles['TableNote'],
                ))
                story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))
        recommendations = data.get('recommendations')
        if recommendations and len(recommendations) > 0:
            self._subsection_heading(story, "Recommendations")
            for rec in recommendations:
                rec_text = rec.replace('💡', '').replace('💰', '').replace('✅', '').replace('🎉', '').strip()
                story.append(Paragraph(f"• {rec_text}", self.styles['CompactBody']))
                story.append(Spacer(1, self.SPACE_TIGHT * inch))
            story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))

        # ── Section 5: Optimization Results (new page) ───────────────────────
        self._start_major_section(story, 5, "Optimization Results", force_new_page=False)
        opt = data.get('optimizationResults')
        if opt:
            rec = (opt.get('optimization_metadata') or {}).get('recommendation', 'weights')
            story.append(Paragraph(
                f"Strategy: {rec.replace('_', ' ').title()}. "
                "Comparing Current to Weights-Opt shows whether rebalancing improves risk-adjusted return; "
                "Market-Opt indicates if expanding the universe could achieve better tradeoffs. "
                "If your current portfolio sits below the efficient frontier, the same return may be achievable with lower risk.",
                self.styles['CompactBody'],
            ))
            story.append(Spacer(1, self.SPACE_AFTER_PARAGRAPH * inch))
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
                story.append(Spacer(1, self.SPACE_BEFORE_TABLE * inch))
                table5 = self._create_numbered_table(
                    5, "Optimization Metrics",
                    opt_table,
                    note="Current = as built; Weights-Opt = same assets rebalanced; Market-Opt = optimizer-selected assets. A higher Sharpe ratio implies better return per unit of risk. Portfolios below the frontier in the chart are inefficient—consider rebalancing or diversification.",
                    ultra_compact=True,
                )
                story.extend(table5)
                story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))
            if MPL_AVAILABLE:
                try:
                    fig, ax = plt.subplots(figsize=(6.5, 3.8))
                    random_portfolios = (
                        opt.get('market_optimized_portfolio', {}).get('random_portfolios') or
                        opt.get('weights_optimized_portfolio', {}).get('random_portfolios')
                    )
                    if random_portfolios:
                        rp_risks = [p['risk'] for p in random_portfolios]
                        rp_rets = [p['return'] for p in random_portfolios]
                        rp_sharpes = [
                            p.get('sharpe', p.get('sharpe_ratio', r / max(rk, 1e-6)))
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
                                color=self.CHART_COLORS['primary'], linewidth=2.2, zorder=2, label='Frontier')
                    if current:
                        ax.scatter(
                            current.get('risk', 0), current.get('expected_return', 0),
                            c=self.CHART_COLORS['negative'], s=220, marker='*',
                            edgecolors='white', linewidths=1.2, zorder=5, label='Current',
                        )
                    if wo_metrics:
                        ax.scatter(
                            wo_metrics.get('risk', 0), wo_metrics.get('expected_return', 0),
                            c=self.CHART_COLORS['primary'], s=130, marker='D',
                            edgecolors='white', linewidths=1.0, zorder=5, label='Weights Opt',
                        )
                    if mo_metrics:
                        ax.scatter(
                            mo_metrics.get('risk', 0), mo_metrics.get('expected_return', 0),
                            c=self.CHART_COLORS['positive'], s=130, marker='s',
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
                    story.append(Spacer(1, self.SPACE_BEFORE_FIGURE * inch))
                    fig2 = self._create_numbered_figure(
                        2, "Efficient Frontier",
                        chart_img,
                        "The blue curve shows the optimal risk/return boundary. Portfolios below the curve are inefficient — the same return is available with less risk. The red star is your current position; markers show optimized alternatives.",
                    )
                    story.extend(fig2)
                    story.append(Spacer(1, self.SPACE_AFTER_CAPTION * inch))
                except Exception as plot_e:
                    logger.warning(f"Failed to generate optimization plot: {plot_e}")
        else:
            story.append(Paragraph("No optimization data available.", self.styles['CompactBody']))
            story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))

        # ── Section 6: Transaction Costs ─────────────────────────────────────
        self._start_major_section(story, 6, "Transaction Costs", force_new_page=False)
        if cost_data:
            story.append(Spacer(1, self.SPACE_BEFORE_TABLE * inch))
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
            table6 = self._create_numbered_table(
                6, "Transaction Costs",
                cost_table_data,
                note="Setup cost is one-time. Annual cost recurs with each rebalance cycle. Annual costs above 1% compound meaningfully over time. Consider a lower courtage tier or reducing rebalancing frequency.",
                col_widths=[1.4 * inch, 2.0 * inch, 2.6 * inch],
                ultra_compact=True,
            )
            story.extend(table6)
            story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))
        else:
            story.append(Paragraph("No cost data available.", self.styles['CompactBody']))
            story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))

        # ── Section 7: Five-Year Projection (new page) ───────────────────────
        self._start_major_section(story, 7, "Five-Year Projection", force_new_page=False)
        story.append(Paragraph(
            "Net growth after Swedish taxes and costs. Use the pessimistic path to check that goals remain "
            "reachable in a bad market; if the range falls short of your target, consider increasing contributions "
            "or extending the time horizon. Base Case is the central planning figure.",
            self.styles['MethodologyBody'],
        ))
        story.append(Spacer(1, self.SPACE_AFTER_PARAGRAPH * inch))

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
                story.append(Spacer(1, self.SPACE_BEFORE_TABLE * inch))
                table7 = self._create_numbered_table(
                    7, "Projection Values",
                    proj_table_data,
                    note=f"Base: +{base_growth:.0f}% | Pessimistic: +{pess_growth:.0f}% over 5 years, net of taxes and costs. If the pessimistic scenario falls short of your goal, increase contributions or extend the time horizon.",
                    ultra_compact=True,
                )
                story.extend(table7)
                story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))
                if MPL_AVAILABLE:
                    plt.figure(figsize=(6, 2.6))
                    plt.plot(proj['years'], proj['optimistic'], self.CHART_COLORS['positive'], linewidth=1.8, label='Optimistic')
                    plt.plot(proj['years'], proj['base'], self.CHART_COLORS['primary'], linewidth=2.2, label='Base')
                    plt.plot(proj['years'], proj['pessimistic'], self.CHART_COLORS['negative'], linewidth=1.8, label='Pessimistic')
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
                    story.append(Spacer(1, self.SPACE_BEFORE_FIGURE * inch))
                    fig3 = self._create_numbered_figure(
                        3, "Five-Year Projection",
                        chart_img,
                        "Green = Optimistic, Blue = Base Case, Red = Pessimistic. The spread between scenarios reflects portfolio volatility. All values are NET after Swedish taxes and estimated transaction costs each year.",
                    )
                    story.extend(fig3)
                    story.append(Spacer(1, self.SPACE_AFTER_CAPTION * inch))
            except Exception as e:
                logger.warning(f"Could not add 5-year projection: {e}")

        # ── Section 8: Risk Analysis ─────────────────────────────────────────
        self._start_major_section(story, 8, "Risk Analysis", force_new_page=False)
        if metrics:
            story.append(Spacer(1, self.SPACE_BEFORE_TABLE * inch))
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
            table8 = self._create_numbered_table(
                8, "Risk Metrics",
                risk_table,
                note="High diversification (e.g. above 70) supports resistance to single-asset shocks. Sharpe above 1.0 is good risk-adjusted return. High volatility implies larger short-term swings—ensure your time horizon and comfort with drawdowns align with these metrics.",
                col_widths=[2.0 * inch, 1.5 * inch, 2.0 * inch],
                ultra_compact=True,
            )
            story.extend(table8)
            story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))
        include_sections = data.get('includeSections') or {}
        stress = data.get('stressTestResults')
        if stress and include_sections.get('stressTest', True):
            self._subsection_heading(story, "Stress Test Analysis")
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
                story.append(Spacer(1, self.SPACE_AFTER_PARAGRAPH * inch))
            all_scenarios = stress.get('scenarios') or stress.get('scenario_results') or {}
            scenarios = self._filter_stress_scenarios(all_scenarios)
            if scenarios:
                summary_rows = [['Scenario', 'Estimated Impact', 'Interpretation']]
                for scenario_name, scenario_data in scenarios.items():
                    impact = self._extract_stress_impact(scenario_data)
                    if impact is None:
                        continue
                    impact_pct = float(impact) * 100
                    if impact_pct <= -20:
                        interpretation = "Severe downside stress"
                    elif impact_pct <= -10:
                        interpretation = "Material downside stress"
                    elif impact_pct < 0:
                        interpretation = "Mild downside stress"
                    elif impact_pct == 0:
                        interpretation = "Neutral scenario outcome"
                    else:
                        interpretation = "Positive relative resilience"
                    summary_rows.append([
                        self._format_scenario_name(scenario_name),
                        self._format_percentage(impact_pct),
                        interpretation,
                    ])
                if len(summary_rows) > 1:
                    story.append(Spacer(1, self.SPACE_BEFORE_TABLE * inch))
                    story.append(self._create_table(
                        summary_rows,
                        col_widths=[1.8 * inch, 1.4 * inch, 3.0 * inch],
                        ultra_compact=True,
                    ))
                    story.append(Spacer(1, self.SPACE_TIGHT * inch))
                    story.append(Paragraph(
                        "This analysis shows how your portfolio would have performed during the 2008 Financial Crisis and 2020 COVID-19 crash. "
                        "Double-digit drawdowns indicate meaningful risk exposure; consider diversification if this exceeds your tolerance.",
                        self.styles['MethodologyBody'],
                    ))
                    story.append(Spacer(1, self.SPACE_AFTER_TABLE * inch))
            if scenarios and MPL_AVAILABLE:
                try:
                    first_with_series = None
                    for name, res in scenarios.items():
                        if isinstance(res, dict):
                            perf = res.get('monthly_performance') or []
                            if perf and len(perf) > 0:
                                first_with_series = (name, res)
                                break
                    if first_with_series:
                        try:
                            scenario_name, scenario_data = first_with_series
                            perf = scenario_data.get('monthly_performance', [])
                            months = [p.get('month', '') for p in perf if p.get('month')]
                            values = [float(p.get('value', 0)) for p in perf]
                            if months and values and len(months) == len(values):
                                base = values[0] if values[0] != 0 else 1.0
                                indexed = [(v / base) * 100 for v in values]
                                plt.figure(figsize=(6, 2.6))
                                plt.plot(range(len(months)), indexed, color=self.CHART_COLORS['primary'], linewidth=2)
                                plt.axhline(y=100, color=self.CHART_COLORS['neutral'], linestyle='--', linewidth=0.8, alpha=0.7)
                                plt.title('Portfolio Value Over Time', fontsize=9, fontweight='bold')
                                plt.ylabel('Value (indexed to 100)', fontsize=7)
                                plt.xlabel('Month', fontsize=7)
                                step = max(1, len(months) // 8)
                                plt.xticks(range(0, len(months), step), [months[i] for i in range(0, len(months), step)], rotation=45, ha='right', fontsize=6)
                                plt.tick_params(axis='y', labelsize=6)
                                plt.grid(True, alpha=0.3)
                                plt.tight_layout(pad=0.5)
                                chart_img = self._generate_plot(plt, compact=True)
                                story.append(Spacer(1, self.SPACE_BEFORE_FIGURE * inch))
                                story.append(chart_img)
                                story.append(Spacer(1, self.SPACE_AFTER_FIGURE * inch))
                                label = self._format_scenario_name(scenario_name)
                                story.append(Paragraph(
                                    f"Portfolio value over time during {label}. Value indexed to 100 at scenario start (crisis and recovery window).",
                                    self.styles['FigureCaption'],
                                ))
                                story.append(Spacer(1, self.SPACE_AFTER_CAPTION * inch))
                        except Exception as timeline_e:
                            logger.warning(f"Failed to generate stress portfolio-over-time chart: {timeline_e}")
                    plt.figure(figsize=(6, 2.8))
                    names, impacts = [], []
                    for name, res in scenarios.items():
                        impact = self._extract_stress_impact(res)
                        if impact is not None:
                            names.append(self._format_scenario_name(name))
                            impacts.append(float(impact) * 100)
                    if names:
                        # Convert to positive values (magnitude) since drawdowns are always losses
                        impacts_magnitude = [abs(x) for x in impacts]
                        sorted_indices = sorted(range(len(impacts_magnitude)), key=lambda k: impacts_magnitude[k], reverse=True)
                        names = [names[i] for i in sorted_indices]
                        impacts_magnitude = [impacts_magnitude[i] for i in sorted_indices]
                        plt.barh(names, impacts_magnitude, color=self.CHART_COLORS['negative'], height=0.55)
                        plt.axvline(x=0, color=self.CHART_COLORS['neutral'], linewidth=0.8, alpha=0.7)
                        plt.title('Peak-to-Trough Drawdown by Scenario', fontsize=9, fontweight='bold')
                        plt.xlabel('Drawdown Magnitude (%)', fontsize=7)
                        plt.tick_params(axis='both', labelsize=6)
                        plt.grid(True, axis='x', linestyle='--', alpha=0.5)
                        plt.tight_layout(pad=0.5)
                        chart_img = self._generate_plot(plt, compact=True)
                        story.append(Spacer(1, self.SPACE_BEFORE_FIGURE * inch))
                        story.append(chart_img)
                        story.append(Spacer(1, self.SPACE_AFTER_FIGURE * inch))
                        story.append(Paragraph(
                            "Peak-to-Trough Drawdown: Shows how much your portfolio would have fallen from peak to trough during the 2008 Financial Crisis and 2020 COVID-19 crash. These represent two of the most severe market downturns in recent history, providing a realistic stress test of portfolio resilience.",
                            self.styles['FigureCaption'],
                        ))
                        story.append(Spacer(1, self.SPACE_AFTER_CAPTION * inch))
                except Exception as plot_e:
                    logger.warning(f"Failed to generate stress test plot: {plot_e}")

        doc.build(story, canvasmaker=PageNumCanvas)
        buffer.seek(0)
        return buffer.getvalue()

#!/usr/bin/env python3
"""
PDF Report Generator
Generates comprehensive PDF reports for portfolios using reportlab.
Includes: Executive Summary, Portfolio, Tax, Optimization summary, Stress Test, Costs, 5-Year Projection, Metrics.
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
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas

class PageNumCanvas(canvas.Canvas):
    """Canvas that adds page numbers and footer/header to each page"""
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
        self.setFont("Helvetica", 7.5)
        self.setStrokeColor(colors.HexColor('#cbd5e0'))
        self.line(35, 35, 560, 35)  # Footer line - tighter
        self.line(35, 808, 560, 808)  # Header line - tighter
        
        # Footer - compact
        self.setFillColor(colors.HexColor('#718096'))
        self.drawRightString(560, 22, f"Page {self._pageNumber} of {page_count}")
        self.drawString(35, 22, "Portfolio Analysis Report")
        
        # Header - compact
        self.drawString(35, 815, "Portfolio Navigator Wizard")
        report_date = datetime.now().strftime("%Y-%m-%d")
        self.drawRightString(560, 815, report_date)

class PDFReportGenerator:
    """
    Generates comprehensive PDF reports for portfolios
    Optimized for professional finance-grade presentation with efficient space utilization
    """
    
    # Layout constants for consistent spacing (in inches)
    MARGIN_LEFT = 0.6
    MARGIN_RIGHT = 0.6
    MARGIN_TOP = 0.65
    MARGIN_BOTTOM = 0.65
    
    # Spacing constants (in inches) - tighter for professional density
    SPACE_AFTER_SECTION = 0.12
    SPACE_BEFORE_SUBSECTION = 0.08
    SPACE_AFTER_TABLE = 0.1
    SPACE_AFTER_CHART = 0.08
    SPACE_BETWEEN_PARAGRAPHS = 0.06
    
    # Chart dimensions - optimized for space
    CHART_WIDTH = 6.8
    CHART_HEIGHT = 3.5
    
    def __init__(self):
        """Initialize the PDF generator"""
        self.page_size = A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles - optimized for professional finance documents"""
        # Title style - prominent but not wasteful
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=16,
            spaceBefore=0,
            alignment=TA_CENTER,
            leading=26
        ))
        
        # Section heading - clear hierarchy, minimal space
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=6,
            spaceBefore=10,
            fontName='Helvetica-Bold',
            leading=17,
            borderPadding=0,
            borderWidth=0,
            borderColor=colors.HexColor('#3182ce'),
        ))
        
        # Subsection heading - subtle distinction
        self.styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=self.styles['Heading3'],
            fontSize=11,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=4,
            spaceBefore=8,
            fontName='Helvetica-Bold',
            leading=14
        ))
        
        # Body text - optimized line height
        self.styles.add(ParagraphStyle(
            name='ReportBody',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=4,
            spaceBefore=0,
            leading=12,
            firstLineIndent=0
        ))
        
        # Compact body for dense sections
        self.styles.add(ParagraphStyle(
            name='CompactBody',
            parent=self.styles['Normal'],
            fontSize=8.5,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=3,
            spaceBefore=0,
            leading=11
        ))
        
        # Disclaimer style - compact footer
        self.styles.add(ParagraphStyle(
            name='Disclaimer',
            parent=self.styles['Normal'],
            fontSize=7.5,
            textColor=colors.HexColor('#718096'),
            alignment=TA_CENTER,
            spaceBefore=12,
            spaceAfter=0,
            fontName='Helvetica-Oblique',
            leading=10
        ))

        # Chart explanation - tight integration with visuals
        self.styles.add(ParagraphStyle(
            name='ChartExplanation',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=8,
            spaceBefore=2,
            fontName='Helvetica-Oblique',
            leading=10,
            leftIndent=6,
            rightIndent=6
        ))
        
        # Key insight callout
        self.styles.add(ParagraphStyle(
            name='InsightCallout',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#2b6cb0'),
            spaceAfter=6,
            spaceBefore=4,
            leftIndent=8,
            borderPadding=4,
            leading=12
        ))
        
        # Table note - small annotations
        self.styles.add(ParagraphStyle(
            name='TableNote',
            parent=self.styles['Normal'],
            fontSize=7.5,
            textColor=colors.HexColor('#718096'),
            spaceAfter=6,
            spaceBefore=2,
            leading=9
        ))
    
    def _create_table(self, data: List[List[str]], col_widths: Optional[List[float]] = None, 
                       compact: bool = False) -> Table:
        """Create a styled table from data - optimized for professional finance documents"""
        table = Table(data, colWidths=col_widths)
        
        # Padding values - tighter for compact mode
        header_pad = 6 if compact else 8
        data_pad = 4 if compact else 6
        font_size_header = 8.5 if compact else 9
        font_size_data = 8 if compact else 8.5
        
        # Apply professional finance-grade table style
        table.setStyle(TableStyle([
            # Header row - dark blue professional look
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), font_size_header),
            ('BOTTOMPADDING', (0, 0), (-1, 0), header_pad),
            ('TOPPADDING', (0, 0), (-1, 0), header_pad),
            
            # Data rows - clean alternating
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2d3748')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), font_size_data),
            ('BOTTOMPADDING', (0, 1), (-1, -1), data_pad),
            ('TOPPADDING', (0, 1), (-1, -1), data_pad),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
            
            # Subtle grid - professional look
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#2d3748')),
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor('#cbd5e0')),
            ('LINEBEFORE', (0, 0), (0, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('LINEAFTER', (-1, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        return table
    
    def _format_number(self, value: float, decimals: int = 2, currency: bool = False) -> str:
        """Format a number for display"""
        if value is None:
            return "N/A"
        
        formatted = f"{value:,.{decimals}f}"
        if currency:
            formatted = f"{formatted} SEK"
        return formatted
    
    def _format_percentage(self, value: float, decimals: int = 2) -> str:
        """Format a percentage for display. Values in (0, 1] are treated as decimals (e.g. 0.12 -> 12%)."""
        if value is None:
            return "N/A"
        display_val = value
        if isinstance(value, (int, float)) and 0 < abs(value) <= 1 and value != 0:
            display_val = value * 100
        return f"{display_val:.{decimals}f}%"
    
    def _generate_plot(self, plt_obj, width: float = None, height: float = None) -> Image:
        """Convert a matplotlib plot to a reportlab Image - optimized dimensions"""
        img_buffer = BytesIO()
        plt_obj.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150, 
                       facecolor='white', edgecolor='none')
        img_buffer.seek(0)
        plt_obj.close()
        # Use class constants or provided dimensions
        w = (width or self.CHART_WIDTH) * inch
        h = (height or self.CHART_HEIGHT) * inch
        return Image(img_buffer, width=w, height=h)

    def _generate_plot_base64(self, plt_obj) -> str:
        """Convert a matplotlib plot to a base64 encoded PNG string"""
        img_buffer = BytesIO()
        plt_obj.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
        img_buffer.seek(0)
        plt_obj.close()
        return base64.b64encode(img_buffer.getvalue()).decode('utf-8')

    def generate_report_plots(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate all report plots as base64 encoded images for inclusion in ZIP exports.
        
        Returns:
            List of {filename, content, size}
        """
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
                # Normalize allocation
                if weight > 1: weight = weight / 100.0
                sector = pos.get('sector', 'Unknown')
                sector_weights[sector] = sector_weights.get(sector, 0.0) + weight
            
            if sector_weights and any(s != 'Unknown' for s in sector_weights.keys()):
                plt.figure(figsize=(10, 6))
                labels = list(sector_weights.keys())
                sizes = list(sector_weights.values())
                plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired(range(len(labels))))
                plt.title('Portfolio Sector Allocation')
                plt.axis('equal')
                content = self._generate_plot_base64(plt)
                plots.append({
                    "filename": "sector_allocation.png",
                    "content": content,
                    "size": len(content)
                })
        except Exception as e:
            logger.warning(f"Failed to generate sector plot for ZIP: {e}")

        # 2. Efficient Frontier
        if opt:
            try:
                plt.figure(figsize=(10, 6))
                
                # Random portfolios
                random_portfolios = opt.get('market_optimized_portfolio', {}).get('random_portfolios') or \
                                   opt.get('weights_optimized_portfolio', {}).get('random_portfolios')
                if random_portfolios:
                    plt.scatter([p['risk'] for p in random_portfolios], [p['return'] for p in random_portfolios], 
                                c='lightgrey', s=10, alpha=0.5, label='Random Portfolios')
                
                # Frontier
                frontier = opt.get('market_optimized_portfolio', {}).get('efficient_frontier') or \
                           opt.get('weights_optimized_portfolio', {}).get('efficient_frontier')
                if frontier:
                    plt.plot([p['risk'] for p in frontier], [p['return'] for p in frontier], 'b-', linewidth=2, label='Efficient Frontier')
                
                # Highlight portfolios
                current = (opt.get('current_portfolio') or {}).get('metrics', {})
                if current:
                    plt.scatter(current.get('risk', 0), current.get('expected_return', 0), c='red', s=100, marker='*', label='Current')
                
                weights_opt = (opt.get('weights_optimized_portfolio') or {}).get('optimized_portfolio', {}).get('metrics', {})
                if weights_opt:
                    plt.scatter(weights_opt.get('risk', 0), weights_opt.get('expected_return', 0), c='blue', s=80, marker='D', label='Weights Optimized')
                
                market_opt = (opt.get('market_optimized_portfolio') or {}).get('optimized_portfolio', {}).get('metrics', {})
                if market_opt:
                    plt.scatter(market_opt.get('risk', 0), market_opt.get('expected_return', 0), c='green', s=80, marker='s', label='Market Optimized')
                
                plt.title('Portfolio Optimization: Risk vs Return')
                plt.xlabel('Risk (Volatility)')
                plt.ylabel('Expected Return')
                plt.legend()
                plt.grid(True, linestyle='--', alpha=0.7)
                
                content = self._generate_plot_base64(plt)
                plots.append({
                    "filename": "optimization_frontier.png",
                    "content": content,
                    "size": len(content)
                })
            except Exception as e:
                logger.warning(f"Failed to generate optimization plot for ZIP: {e}")

        # 3. Stress Test
        if stress_results:
            try:
                scenarios = stress_results.get('scenarios') or stress_results.get('scenario_results') or {}
                if scenarios:
                    names = []
                    impacts = []
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
                        plots.append({
                            "filename": "stress_test_impact.png",
                            "content": content,
                            "size": len(content)
                        })
            except Exception as e:
                logger.warning(f"Failed to generate stress test plot for ZIP: {e}")

        # 4. 5-Year Projection
        projection_metrics = data.get('projectionMetrics') or {}
        weights = projection_metrics.get('weights') or (data.get('portfolio') or {}).get('weights') or {}
        if not weights and (data.get('portfolio') or {}).get('allocations'):
            weights = {a.get('symbol', a.get('ticker', '')): (a.get('allocation', 0) / 100.0) for a in (data.get('portfolio') or {}).get('allocations', []) if a.get('symbol') or a.get('ticker')}
        
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
                
                def format_sek(x, pos):
                    if x >= 1e6: return f'{x/1e6:.1f}M'
                    if x >= 1e3: return f'{x/1e3:.0f}k'
                    return f'{x:.0f}'
                from matplotlib.ticker import FuncFormatter
                plt.gca().yaxis.set_major_formatter(FuncFormatter(format_sek))
                
                content = self._generate_plot_base64(plt)
                plots.append({
                    "filename": "five_year_projection.png",
                    "content": content,
                    "size": len(content)
                })
            except Exception as e:
                logger.warning(f"Failed to generate projection plot for ZIP: {e}")
                
        return plots

    def generate_portfolio_report(self, data: Dict[str, Any]) -> bytes:
        """
        Generate comprehensive PDF report
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=self.page_size, 
                               leftMargin=self.MARGIN_LEFT*inch, 
                               rightMargin=self.MARGIN_RIGHT*inch,
                               topMargin=self.MARGIN_TOP*inch, 
                               bottomMargin=self.MARGIN_BOTTOM*inch)
        story = []
        
        portfolio_name = data.get('portfolioName') or "Investment Portfolio"
        
        # --- TITLE PAGE - Compact professional design ---
        story.append(Spacer(1, 1.5*inch))
        story.append(Paragraph("Portfolio Analysis Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph(f"<b>{portfolio_name}</b>", self.styles['SubsectionHeading']))
        story.append(Spacer(1, 0.3*inch))
        
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(f"Report Date: {report_date}", self.styles['ReportBody']))
        story.append(Spacer(1, 1.8*inch))
        
        disclaimer_text = ("DISCLAIMER: This report is for informational and educational purposes only. "
                          "It does not constitute financial, investment, or tax advice. "
                          "Historical performance is not indicative of future results. "
                          "Please consult with a qualified financial advisor before making any investment decisions.")
        story.append(Paragraph(disclaimer_text, self.styles['Disclaimer']))
        story.append(PageBreak())

        # --- TABLE OF CONTENTS - Compact two-column layout ---
        story.append(Paragraph("Table of Contents", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        toc_items = [
            "1. Executive Summary",
            "2. Methodology & Assumptions",
            "3. Portfolio Composition",
            "4. Swedish Tax Analysis"
        ]
        
        # Track sections for the TOC
        sec_num = 5
        if data.get('includeSections', {}).get('optimization', False) and data.get('optimizationResults'):
            toc_items.append(f"{sec_num}. Optimization Results")
            opt_sec_num = sec_num
            sec_num += 1
        else:
            opt_sec_num = None

        if data.get('includeSections', {}).get('stressTest', False) and data.get('stressTestResults'):
            toc_items.append(f"{sec_num}. Stress Test Analysis")
            stress_sec_num = sec_num
            sec_num += 1
        else:
            stress_sec_num = None
            
        toc_items.append(f"{sec_num}. Transaction Costs")
        cost_sec_num = sec_num
        sec_num += 1
        
        toc_items.append(f"{sec_num}. 5-Year Projection")
        proj_sec_num = sec_num
        sec_num += 1
        
        toc_items.append(f"{sec_num}. Risk Analysis")
        risk_sec_num = sec_num
        
        # Render TOC items compactly
        for item in toc_items:
            story.append(Paragraph(item, self.styles['ReportBody']))
        
        story.append(Spacer(1, 0.2*inch))
        
        # Don't page break after TOC - continue with Executive Summary
        story.append(Spacer(1, 0.15*inch))

        # --- 1. EXECUTIVE SUMMARY ---
        story.append(Paragraph("1. Executive Summary", self.styles['SectionHeading']))
        
        portfolio_value = data.get('portfolioValue', 0.0)
        account_type = data.get('accountType', 'N/A')
        tax_year = data.get('taxYear', datetime.now().year)
        
        summary_data = [
            ['Metric', 'Value'],
            ['Portfolio Value', self._format_number(portfolio_value, currency=True)],
            ['Account Type', account_type],
            ['Tax Year', str(tax_year)],
        ]
        
        metrics = data.get('metrics') or {}
        exp_ret = data.get('expectedReturn') if 'expectedReturn' in data else metrics.get('expectedReturn')
        risk_val = data.get('risk') if 'risk' in data else metrics.get('risk')
        sharpe_val = data.get('sharpeRatio') if 'sharpeRatio' in data else metrics.get('sharpeRatio')
        if exp_ret is not None:
            summary_data.append(['Expected Return', self._format_percentage(exp_ret)])
        if risk_val is not None:
            summary_data.append(['Risk (Volatility)', self._format_percentage(risk_val)])
        if sharpe_val is not None:
            summary_data.append(['Sharpe Ratio', self._format_number(sharpe_val, decimals=3)])
        
        story.append(self._create_table(summary_data, col_widths=[2.5*inch, 4.5*inch], compact=True))
        story.append(Spacer(1, 0.08*inch))
        
        # Executive Summary interpretation - compact
        story.append(Paragraph("<b>Interpretation:</b> Expected Return = historical annualized gain. "
                             "Risk = yearly fluctuation (higher = more uncertainty). "
                             "Sharpe Ratio = return per unit of risk (>1.0 = efficient, <0.5 = may be inadequate).",
                             self.styles['CompactBody']))
        
        # --- 2. METHODOLOGY & ASSUMPTIONS ---
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph("2. Methodology & Assumptions", self.styles['SectionHeading']))
        
        # Compact data sources as a table
        story.append(Paragraph("2a. Data Sources", self.styles['SubsectionHeading']))
        data_sources = [
            ['Source', 'Description'],
            ['Historical Prices', '3-5 years daily data → expected returns and risk metrics'],
            ['Tax Rates', 'Skatteverket official rates (schablonränta for ISK/KF, 30% gains for AF)'],
            ['Transaction Costs', 'Avanza courtage schedules (Start, Mini, Small, Medium, Fast Pris)']
        ]
        story.append(self._create_table(data_sources, col_widths=[1.8*inch, 5.2*inch], compact=True))
        story.append(Spacer(1, 0.1*inch))
        
        # Projection Methodology
        story.append(Paragraph("2b. Projection Scenarios", self.styles['SubsectionHeading']))
        
        proj_method_data = [
            ['Scenario', 'Calculation', 'Use Case'],
            ['Optimistic', 'Return + Volatility', 'Upper bound—plan upside potential'],
            ['Base Case', 'Expected Return', 'Most likely—central planning figure'],
            ['Pessimistic', 'Return − 50% Vol', 'Conservative—stress test goals']
        ]
        proj_method_table = Table(proj_method_data, colWidths=[1.3*inch, 1.8*inch, 3.9*inch])
        proj_method_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#2d3748')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        story.append(proj_method_table)
        story.append(Spacer(1, 0.06*inch))
        story.append(Paragraph("Each year deducts tax and costs, then compounds net return for realistic wealth projection.",
                             self.styles['CompactBody']))
        
        # Limitations - as compact table
        story.append(Paragraph("2c. Limitations", self.styles['SubsectionHeading']))
        limitations_data = [
            ['Limitation', 'Impact'],
            ['Historical ≠ Future', 'Markets can shift; past returns do not guarantee future performance'],
            ['Static Assumptions', 'Assumes current holdings maintained; trading changes outcomes'],
            ['Tax Law Changes', 'Swedish rules may change; rates based on current legislation'],
            ['Estimation Only', 'Educational purposes; consult a financial advisor']
        ]
        story.append(self._create_table(limitations_data, col_widths=[1.8*inch, 5.2*inch], compact=True))
        
        # --- 3. PORTFOLIO COMPOSITION ---
        story.append(PageBreak())
        story.append(Paragraph("3. Portfolio Composition", self.styles['SectionHeading']))
        story.append(Paragraph("Holdings breakdown. Well-diversified portfolios spread risk across assets and sectors.",
                             self.styles['CompactBody']))
        
        portfolio = data.get('portfolio', [])
        if portfolio:
            comp_data = [['Ticker', 'Allocation', 'Value (SEK)']]
            sector_weights = {}
            for pos in portfolio:
                ticker = pos.get('ticker', pos.get('symbol', 'N/A'))
                allocation = pos.get('allocation', 0.0)
                # Handle both 0.x and x.x formats
                if allocation > 1:
                    allocation = allocation / 100.0
                value = portfolio_value * allocation if portfolio_value else 0.0
                comp_data.append([
                    ticker,
                    self._format_percentage(allocation * 100),
                    self._format_number(value, currency=True)
                ])
                # Collect sector
                sector = pos.get('sector', 'Unknown')
                sector_weights[sector] = sector_weights.get(sector, 0.0) + allocation
            
            story.append(self._create_table(comp_data, compact=True))
            story.append(Paragraph("Concentration risk >20-25% in one holding warrants review.", self.styles['TableNote']))
            
            # Add Sector Allocation Pie Chart
            if MPL_AVAILABLE and sector_weights:
                try:
                    has_real_sectors = any(s != 'Unknown' for s in sector_weights.keys())
                    if has_real_sectors:
                        plt.figure(figsize=(8, 4.5))
                        labels = list(sector_weights.keys())
                        sizes = list(sector_weights.values())
                        
                        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, 
                                colors=plt.cm.Paired(range(len(labels))), textprops={'fontsize': 8})
                        plt.title('Sector Allocation', fontsize=10, fontweight='bold')
                        plt.axis('equal')
                        
                        story.append(self._generate_plot(plt, width=5.5, height=3.2))
                        story.append(Paragraph("<b>Sector Exposure:</b> >40% in one sector = high industry dependency. "
                                            "10-25% per sector typically provides stability during market rotations.", 
                                            self.styles['ChartExplanation']))
                except Exception as plot_e:
                    logger.warning(f"Failed to generate sector pie chart: {plot_e}")
        else:
            story.append(Paragraph("No portfolio data available.", self.styles['Normal']))
        
        # --- 4. SWEDISH TAX ANALYSIS ---
        # Continue on same page if space allows
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph("4. Swedish Tax Analysis", self.styles['SectionHeading']))

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

            story.append(self._create_table(tax_table_data, col_widths=[1.8*inch, 2*inch, 3.2*inch], compact=True))
            story.append(Paragraph(f"<b>{account_type}:</b> " + (
                "Schablonbeskattning—flat tax on capital regardless of gains." 
                if account_type in ('ISK', 'KF') else
                "30% on realized gains only. Pay when you sell."
            ), self.styles['TableNote']))
        else:
            story.append(Paragraph("No tax data available.", self.styles['Normal']))

        # --- 4a. ACCOUNT TYPE COMPARISON ---
        tax_comparison = data.get('taxComparison')
        if tax_comparison and len(tax_comparison) > 0:
            story.append(Spacer(1, 0.12*inch))
            story.append(Paragraph("4a. Account Type Comparison", self.styles['SubsectionHeading']))

            # Create comparison table
            comp_table_data = [['Account', 'Annual Tax', 'Eff. Rate', 'After-Tax']]

            # Find the lowest tax option
            lowest_tax = min(tc.get('annualTax', float('inf')) for tc in tax_comparison)

            for tc in tax_comparison:
                act_type = tc.get('accountType', 'N/A')
                annual_tax_val = tc.get('annualTax', 0)
                eff_rate_val = tc.get('effectiveRate', 0)
                after_tax_ret = tc.get('afterTaxReturn', 0)

                is_current = act_type == account_type
                is_lowest = annual_tax_val == lowest_tax

                label = act_type
                if is_current and is_lowest:
                    label += " ★"
                elif is_lowest:
                    label += " ★"

                comp_table_data.append([
                    label,
                    self._format_number(float(annual_tax_val), currency=True),
                    self._format_percentage(float(eff_rate_val)),
                    self._format_percentage(float(after_tax_ret))
                ])

            story.append(self._create_table(comp_table_data, col_widths=[1.6*inch, 2*inch, 1.7*inch, 1.7*inch], compact=True))
            story.append(Paragraph("★ = Optimal (lowest tax). Switching depends on transfer costs and time horizon.",
                                 self.styles['TableNote']))

        # --- 4b. TAX-FREE LEVEL BREAKDOWN ---
        tax_free_data = data.get('taxFreeData')
        if tax_free_data and (account_type == 'ISK' or account_type == 'KF'):
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph("4b. Tax-Free Breakdown", self.styles['SubsectionHeading']))

            tax_free_level = tax_free_data.get('taxFreeLevel', 0)
            tax_free_amount = tax_free_data.get('taxFreeAmount', 0)
            taxable_amount = tax_free_data.get('taxableAmount', 0)
            is_tax_free = tax_free_data.get('isTaxFree', False)

            if is_tax_free:
                story.append(Paragraph(f"<b>Zero Tax:</b> Portfolio ({self._format_number(portfolio_value, currency=True)}) is below "
                                     f"{tax_year} tax-free level ({self._format_number(tax_free_level, currency=True)}).",
                                     self.styles['InsightCallout']))
            else:
                breakdown_table = [
                    ['Component', 'Amount', '%'],
                    ['Tax-Free', self._format_number(tax_free_amount, currency=True), self._format_percentage(tax_free_data.get('taxFreePercentage', 0))],
                    ['Taxable', self._format_number(taxable_amount, currency=True), self._format_percentage(tax_free_data.get('taxablePercentage', 0))],
                ]
                story.append(self._create_table(breakdown_table, col_widths=[1.5*inch, 2.5*inch, 1.5*inch], compact=True))
                story.append(Paragraph(f"Tax-free level {tax_year}: {self._format_number(tax_free_level, currency=True)}",
                                     self.styles['TableNote']))

        # --- 4c. RECOMMENDATIONS ---
        recommendations = data.get('recommendations')
        if recommendations and len(recommendations) > 0:
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph("4c. Recommendations", self.styles['SubsectionHeading']))

            for i, rec in enumerate(recommendations, 1):
                rec_text = rec.replace('💡', '').replace('💰', '').replace('✅', '').replace('🎉', '').strip()
                story.append(Paragraph(f"<b>{i}.</b> {rec_text}", self.styles['CompactBody']))
        
        # --- 5. OPTIMIZATION RESULTS ---
        if opt_sec_num:
            story.append(PageBreak())
            opt = data['optimizationResults']
            story.append(Paragraph(f"{opt_sec_num}. Optimization Results", self.styles['SectionHeading']))
            
            rec = (opt.get('optimization_metadata') or {}).get('recommendation', 'weights')
            story.append(Paragraph(f"Strategy: {rec.replace('_', ' ').title()} — using Modern Portfolio Theory to maximize return per risk unit.",
                                 self.styles['CompactBody']))
            
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
                opt_table.append([
                    'Exp. Return',
                    self._format_percentage(current.get('expected_return', 0)),
                    self._format_percentage(wo_metrics.get('expected_return', 0))
                ] + ([self._format_percentage(mo_metrics.get('expected_return', 0))] if has_market else []))
                opt_table.append([
                    'Risk (Vol)',
                    self._format_percentage(current.get('risk', 0)),
                    self._format_percentage(wo_metrics.get('risk', 0))
                ] + ([self._format_percentage(mo_metrics.get('risk', 0))] if has_market else []))
                opt_table.append([
                    'Sharpe',
                    self._format_number(current.get('sharpe_ratio', 0), decimals=3),
                    self._format_number(wo_metrics.get('sharpe_ratio', 0), decimals=3)
                ] + ([self._format_number(mo_metrics.get('sharpe_ratio', 0), decimals=3)] if has_market else []))
                
                story.append(self._create_table(opt_table, compact=True))
                story.append(Paragraph("Higher Sharpe = better risk-adjusted returns. Use as guidance—assumes historical correlations persist.",
                                     self.styles['TableNote']))

            if MPL_AVAILABLE:
                try:
                    plt.figure(figsize=(8, 4.5))
                    random_portfolios = opt.get('market_optimized_portfolio', {}).get('random_portfolios') or \
                                       opt.get('weights_optimized_portfolio', {}).get('random_portfolios')
                    if random_portfolios:
                        plt.scatter([p['risk'] for p in random_portfolios], [p['return'] for p in random_portfolios], 
                                   c='#e2e8f0', s=8, alpha=0.4, label='Random')
                    frontier = opt.get('market_optimized_portfolio', {}).get('efficient_frontier') or \
                               opt.get('weights_optimized_portfolio', {}).get('efficient_frontier')
                    if frontier:
                        plt.plot([p['risk'] for p in frontier], [p['return'] for p in frontier], '#3182ce', linewidth=2, label='Frontier')
                    if current:
                        plt.scatter(current.get('risk', 0), current.get('expected_return', 0), c='#e53e3e', s=80, marker='*', label='Current')
                    if wo_metrics:
                        plt.scatter(wo_metrics.get('risk', 0), wo_metrics.get('expected_return', 0), c='#3182ce', s=60, marker='D', label='Weights Opt')
                    if mo_metrics:
                        plt.scatter(mo_metrics.get('risk', 0), mo_metrics.get('expected_return', 0), c='#38a169', s=60, marker='s', label='Market Opt')
                    
                    plt.title('Risk vs Return', fontsize=10, fontweight='bold')
                    plt.xlabel('Risk (Volatility)', fontsize=8)
                    plt.ylabel('Expected Return', fontsize=8)
                    plt.tick_params(axis='both', labelsize=7)
                    plt.grid(True, linestyle='--', alpha=0.4)
                    plt.legend(fontsize=7, loc='upper left')
                    story.append(self._generate_plot(plt, width=6.0, height=3.3))
                    story.append(Paragraph("<b>Efficient Frontier:</b> Blue curve = optimal combinations. "
                                         "Below line = inefficient. Red star = current. If below frontier, reallocation may improve returns without adding risk.", 
                                         self.styles['ChartExplanation']))
                except Exception as plot_e:
                    logger.warning(f"Failed to generate optimization plot: {plot_e}")

        # --- 6. STRESS TEST ANALYSIS ---
        if stress_sec_num:
            story.append(Spacer(1, 0.15*inch))
            stress = data['stressTestResults']
            story.append(Paragraph(f"{stress_sec_num}. Stress Test Analysis", self.styles['SectionHeading']))
            
            resilience = stress.get('resilience_score')
            if resilience is not None:
                resilience_label = (
                    "Excellent" if resilience >= 80 else
                    "Good" if resilience >= 60 else
                    "Fair" if resilience >= 40 else "Weak"
                )
                story.append(Paragraph(f"<b>Resilience Score:</b> {self._format_number(resilience, decimals=0)}/100 ({resilience_label})", 
                                     self.styles['InsightCallout']))
            
            scenarios = stress.get('scenarios') or stress.get('scenario_results') or {}
            if scenarios:
                if MPL_AVAILABLE:
                    try:
                        plt.figure(figsize=(8, 4))
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
                            plt.barh(names, impacts, color=['#e53e3e' if x < 0 else '#38a169' for x in impacts], height=0.6)
                            plt.title('Crisis Impact', fontsize=10, fontweight='bold')
                            plt.xlabel('Value Change (%)', fontsize=8)
                            plt.tick_params(axis='both', labelsize=7)
                            plt.grid(True, axis='x', linestyle='--', alpha=0.5)
                            plt.tight_layout()
                            story.append(self._generate_plot(plt, width=5.8, height=2.8))
                            story.append(Paragraph("<b>Crisis Impact:</b> Red = loss, Green = gain. >-20% indicates high sensitivity. "
                                                 "Multiple severe losses suggest correlated risk exposure.", 
                                                 self.styles['ChartExplanation']))
                    except Exception as plot_e:
                        logger.warning(f"Failed to generate stress test plot: {plot_e}")

        # --- 7. TRANSACTION COST ANALYSIS ---
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph(f"{cost_sec_num}. Transaction Costs", self.styles['SectionHeading']))
        
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
                cost_table_data.append(['Courtage', str(courtage).capitalize(), 'Fee tier'])
            story.append(self._create_table(cost_table_data, col_widths=[1.5*inch, 2.2*inch, 3.3*inch], compact=True))
            story.append(Paragraph(">1% annual costs: consider different courtage class or less trading.", self.styles['TableNote']))
        else:
            story.append(Paragraph("No cost data available.", self.styles['CompactBody']))

        # --- 8. 5-YEAR PROJECTION ---
        story.append(PageBreak())
        story.append(Paragraph(f"{proj_sec_num}. 5-Year Projection", self.styles['SectionHeading']))
        story.append(Paragraph("Net growth after Swedish taxes and costs. Base Case = realistic planning; Pessimistic = stress-test your goals.",
                             self.styles['CompactBody']))
        
        projection_metrics = data.get('projectionMetrics') or {}
        portfolio_data = data.get('portfolio')
        
        # Handle weights from various data structures
        weights = projection_metrics.get('weights') or {}
        if not weights and isinstance(portfolio_data, dict):
            weights = portfolio_data.get('weights') or {}
            if not weights and portfolio_data.get('allocations'):
                weights = {a.get('symbol', a.get('ticker', '')): (a.get('allocation', 0) / 100.0) 
                          for a in portfolio_data.get('allocations', []) 
                          if a.get('symbol') or a.get('ticker')}
        if not weights and isinstance(portfolio_data, list):
            weights = {p.get('ticker', p.get('symbol', '')): p.get('allocation', 0) 
                      for p in portfolio_data if p.get('ticker') or p.get('symbol')}
        
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
                    courtage_class=(cost_data.get('courtageClass') or 'medium').lower(),
                    rebalancing_frequency='quarterly',
                )
                proj_table = [['Year', 'Optimistic', 'Base Case', 'Pessimistic']]
                for i, year in enumerate(proj.get('years', [])):
                    proj_table.append([str(year), 
                                     self._format_number(proj['optimistic'][i], decimals=0, currency=True),
                                     self._format_number(proj['base'][i], decimals=0, currency=True),
                                     self._format_number(proj['pessimistic'][i], decimals=0, currency=True)])
                story.append(self._create_table(proj_table, compact=True))
                
                # Calculate growth metrics
                final_base = proj['base'][-1] if proj.get('base') else portfolio_value
                final_pess = proj['pessimistic'][-1] if proj.get('pessimistic') else portfolio_value
                base_growth = ((final_base / portfolio_value) - 1) * 100 if portfolio_value else 0
                pess_growth = ((final_pess / portfolio_value) - 1) * 100 if portfolio_value else 0
                
                story.append(Paragraph(f"Base: +{base_growth:.0f}% | Pessimistic: +{pess_growth:.0f}% (5yr net). "
                                     "If pessimistic doesn't meet goals, adjust strategy or timeline.",
                                     self.styles['TableNote']))
                
                if MPL_AVAILABLE:
                    plt.figure(figsize=(8, 4))
                    plt.plot(proj['years'], proj['optimistic'], '#38a169', marker='', linewidth=2, label='Optimistic')
                    plt.plot(proj['years'], proj['base'], '#3182ce', marker='', linewidth=2.5, label='Base')
                    plt.plot(proj['years'], proj['pessimistic'], '#e53e3e', marker='', linewidth=2, label='Pessimistic')
                    plt.title('5-Year Projection', fontsize=10, fontweight='bold')
                    plt.ylabel('Value (SEK)', fontsize=8)
                    plt.xlabel('Year', fontsize=8)
                    plt.tick_params(axis='both', labelsize=7)
                    plt.legend(fontsize=7)
                    plt.grid(True, alpha=0.3)
                    
                    # Format Y-axis
                    from matplotlib.ticker import FuncFormatter
                    def format_sek(x, pos):
                        if x >= 1e6: return f'{x/1e6:.1f}M'
                        if x >= 1e3: return f'{x/1e3:.0f}k'
                        return f'{x:.0f}'
                    plt.gca().yaxis.set_major_formatter(FuncFormatter(format_sek))
                    
                    story.append(self._generate_plot(plt, width=6.2, height=3.2))
                    story.append(Paragraph("<b>Trajectory:</b> Blue = Base (most likely), Green = Optimistic, Red = Pessimistic. "
                                         "Spread = uncertainty. All values NET after taxes and costs.", 
                                         self.styles['ChartExplanation']))
            except Exception as e:
                logger.warning(f"Could not add 5-year projection: {e}")

        # --- 9. RISK ANALYSIS & METRICS ---
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph(f"{risk_sec_num}. Risk Analysis", self.styles['SectionHeading']))
        
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
                risk_val = metrics['risk']
                risk_pct = risk_val * 100 if risk_val < 1 else risk_val
                risk_rating = (
                    "Low" if risk_pct < 10 else
                    "Moderate" if risk_pct < 20 else
                    "High" if risk_pct < 30 else "Very High"
                )
                risk_table.append(['Volatility', self._format_percentage(risk_val), risk_rating])
            
            story.append(self._create_table(risk_table, col_widths=[2*inch, 1.5*inch, 2*inch], compact=True))
            story.append(Paragraph("Diversification >70 = better turbulence resistance | Sharpe >1.0 = good, >1.5 = excellent | "
                                 "Volatility 20% = typical year swing of that amount", self.styles['TableNote']))

        # Final Build
        doc.build(story, canvasmaker=PageNumCanvas)
        buffer.seek(0)
        return buffer.getvalue()

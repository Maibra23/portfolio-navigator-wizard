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
        self.setFont("Helvetica", 9)
        self.setStrokeColor(colors.lightgrey)
        self.line(30, 40, 565, 40)  # Footer line
        self.line(30, 810, 565, 810)  # Header line
        
        # Footer
        self.drawRightString(565, 25, f"Page {self._pageNumber} of {page_count}")
        self.drawString(30, 25, "Portfolio Analysis Report - Confidential")
        
        # Header
        self.drawString(30, 818, "Portfolio Navigator Wizard")
        # Add date to header
        report_date = datetime.now().strftime("%Y-%m-%d")
        self.drawRightString(565, 818, report_date)

class PDFReportGenerator:
    """
    Generates comprehensive PDF reports for portfolios
    """
    
    def __init__(self):
        """Initialize the PDF generator"""
        self.page_size = A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Section heading
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=20
        ))
        
        # Subsection heading
        self.styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=8,
            spaceBefore=12
        ))
        
        # Disclaimer style
        self.styles.add(ParagraphStyle(
            name='Disclaimer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceBefore=20,
            fontName='Helvetica-Oblique'
        ))

        # Chart explanation
        self.styles.add(ParagraphStyle(
            name='ChartExplanation',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#444444'),
            spaceAfter=15,
            italic=True
        ))
    
    def _create_table(self, data: List[List[str]], col_widths: Optional[List[float]] = None) -> Table:
        """Create a styled table from data"""
        table = Table(data, colWidths=col_widths)
        
        # Apply table style
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
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
    
    def _generate_plot(self, plt_obj) -> Image:
        """Convert a matplotlib plot to a reportlab Image"""
        img_buffer = BytesIO()
        plt_obj.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
        img_buffer.seek(0)
        plt_obj.close()
        # Scale to fit page width (A4 width is approx 8.27 inch, minus margins)
        return Image(img_buffer, width=6.5*inch, height=4*inch)

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
                               leftMargin=0.5*inch, rightMargin=0.5*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []
        
        portfolio_name = data.get('portfolioName') or "Investment Portfolio"
        
        # --- TITLE PAGE ---
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph("Portfolio Analysis Report", self.styles['CustomTitle']))
        story.append(Paragraph(f"Prepared for: {portfolio_name}", self.styles['SubsectionHeading']))
        story.append(Spacer(1, 0.5*inch))
        
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(f"Report Date: {report_date}", self.styles['Normal']))
        story.append(Spacer(1, 2.5*inch))
        
        disclaimer_text = ("DISCLAIMER: This report is for informational and educational purposes only. "
                          "It does not constitute financial, investment, or tax advice. "
                          "Historical performance is not indicative of future results. "
                          "Please consult with a qualified financial advisor before making any investment decisions.")
        story.append(Paragraph(disclaimer_text, self.styles['Disclaimer']))
        story.append(PageBreak())

        # --- TABLE OF CONTENTS ---
        story.append(Paragraph("Table of Contents", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.2*inch))
        toc_items = [
            "1. Executive Summary",
            "2. Portfolio Composition & Allocations",
            "3. Swedish Tax Analysis"
        ]
        
        # Track sections for the TOC
        sec_num = 4
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
            
        toc_items.append(f"{sec_num}. Transaction Cost Analysis")
        cost_sec_num = sec_num
        sec_num += 1
        
        toc_items.append(f"{sec_num}. 5-Year Projection (Tax & Cost Adjusted)")
        proj_sec_num = sec_num
        sec_num += 1
        
        toc_items.append(f"{sec_num}. Risk Analysis & Metrics")
        risk_sec_num = sec_num
        
        for item in toc_items:
            story.append(Paragraph(item, self.styles['Normal']))
            story.append(Spacer(1, 0.15*inch))
        
        story.append(PageBreak())

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
        
        story.append(self._create_table(summary_data, col_widths=[3*inch, 4.2*inch]))
        story.append(Spacer(1, 0.3*inch))
        
        # --- 2. PORTFOLIO COMPOSITION ---
        story.append(PageBreak())
        story.append(Paragraph("2. Portfolio Composition & Allocations", self.styles['SectionHeading']))
        
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
            
            story.append(self._create_table(comp_data))
            story.append(Spacer(1, 0.2*inch))
            
            # Add Sector Allocation Pie Chart
            if MPL_AVAILABLE and sector_weights:
                try:
                    has_real_sectors = any(s != 'Unknown' for s in sector_weights.keys())
                    if has_real_sectors:
                        plt.figure(figsize=(10, 6))
                        labels = list(sector_weights.keys())
                        sizes = list(sector_weights.values())
                        
                        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, 
                                colors=plt.cm.Paired(range(len(labels))))
                        plt.title('Portfolio Sector Allocation')
                        plt.axis('equal')
                        
                        story.append(self._generate_plot(plt))
                        story.append(Paragraph("Figure 1: Distribution of holdings by market sector. "
                                            "Diversification across sectors helps mitigate industry-specific risks.", 
                                            self.styles['ChartExplanation']))
                except Exception as plot_e:
                    logger.warning(f"Failed to generate sector pie chart: {plot_e}")
        else:
            story.append(Paragraph("No portfolio data available.", self.styles['Normal']))
        
        # --- 3. SWEDISH TAX ANALYSIS ---
        story.append(PageBreak())
        story.append(Paragraph("3. Swedish Tax Analysis", self.styles['SectionHeading']))

        tax_data = data.get('taxData', {}) or {}
        if tax_data:
            tax_table_data = [['Tax Component', 'Value']]
            annual_tax = tax_data.get('annualTax') or tax_data.get('annual_tax')
            eff_rate = tax_data.get('effectiveTaxRate') or tax_data.get('effective_tax_rate')
            tax_free = tax_data.get('taxFreeLevel') or tax_data.get('tax_free_level')
            taxable_cap = tax_data.get('taxableCapital') or tax_data.get('taxable_capital')
            if annual_tax is not None:
                tax_table_data.append(['Estimated Annual Tax', self._format_number(float(annual_tax), currency=True)])
            if eff_rate is not None:
                tax_table_data.append(['Effective Tax Rate', self._format_percentage(float(eff_rate))])
            if tax_free is not None:
                tax_table_data.append(['Tax-Free Allowance', self._format_number(float(tax_free), currency=True)])
            if taxable_cap is not None:
                tax_table_data.append(['Taxable Capital Base', self._format_number(float(taxable_cap), currency=True)])

            story.append(self._create_table(tax_table_data, col_widths=[3*inch, 4.2*inch]))
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph(f"Analysis based on {account_type} rules for the {tax_year} tax year. "
                                 "Calculations include standard-tax for ISK/KF accounts or estimated capital gains tax based on current Swedish legislation.",
                                 self.styles['Normal']))
        else:
            story.append(Paragraph("No tax data available.", self.styles['Normal']))

        # --- 3a. ACCOUNT TYPE COMPARISON ---
        tax_comparison = data.get('taxComparison')
        if tax_comparison and len(tax_comparison) > 0:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("3a. Account Type Comparison", self.styles['SubsectionHeading']))
            story.append(Paragraph("The following table compares estimated annual taxes across all three Swedish investment account types based on your portfolio value.",
                                 self.styles['Normal']))
            story.append(Spacer(1, 0.1*inch))

            # Create comparison table
            comp_table_data = [['Account Type', 'Annual Tax (SEK)', 'Effective Rate (%)', 'After-Tax Return (%)']]

            # Find the lowest tax option
            lowest_tax = min(tc.get('annualTax', float('inf')) for tc in tax_comparison)

            for tc in tax_comparison:
                act_type = tc.get('accountType', 'N/A')
                annual_tax_val = tc.get('annualTax', 0)
                eff_rate_val = tc.get('effectiveRate', 0)
                after_tax_ret = tc.get('afterTaxReturn', 0)

                # Highlight the current account type and lowest tax option
                is_current = act_type == account_type
                is_lowest = annual_tax_val == lowest_tax

                label = act_type
                if is_current and is_lowest:
                    label += " ★ (Current & Optimal)"
                elif is_current:
                    label += " (Current)"
                elif is_lowest:
                    label += " ★ (Optimal)"

                comp_table_data.append([
                    label,
                    self._format_number(float(annual_tax_val), currency=True),
                    self._format_percentage(float(eff_rate_val)),
                    self._format_percentage(float(after_tax_ret))
                ])

            comp_table = Table(comp_table_data, colWidths=[2*inch, 2*inch, 1.7*inch, 1.5*inch])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(comp_table)
            story.append(Spacer(1, 0.15*inch))
            story.append(Paragraph("★ = Optimal (lowest annual tax)", self.styles['Normal']))

        # --- 3b. TAX-FREE LEVEL BREAKDOWN ---
        tax_free_data = data.get('taxFreeData')
        if tax_free_data and (account_type == 'ISK' or account_type == 'KF'):
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("3b. Tax-Free Level Breakdown", self.styles['SubsectionHeading']))

            tax_free_level = tax_free_data.get('taxFreeLevel', 0)
            tax_free_amount = tax_free_data.get('taxFreeAmount', 0)
            taxable_amount = tax_free_data.get('taxableAmount', 0)
            is_tax_free = tax_free_data.get('isTaxFree', False)

            if is_tax_free:
                story.append(Paragraph(f"🎉 <b>Congratulations!</b> Your entire portfolio of {self._format_number(portfolio_value, currency=True)} is below the {tax_year} tax-free level ({self._format_number(tax_free_level, currency=True)}). "
                                     "This means you pay <b>zero tax</b> on this account!",
                                     self.styles['Normal']))
            else:
                breakdown_table = [
                    ['Component', 'Amount (SEK)', 'Percentage'],
                    ['Tax-Free Portion', self._format_number(tax_free_amount, currency=True), self._format_percentage(tax_free_data.get('taxFreePercentage', 0))],
                    ['Taxable Portion', self._format_number(taxable_amount, currency=True), self._format_percentage(tax_free_data.get('taxablePercentage', 0))],
                    ['Total Capital', self._format_number(portfolio_value, currency=True), '100.00%']
                ]
                story.append(self._create_table(breakdown_table, col_widths=[2.5*inch, 2.5*inch, 2.2*inch]))
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph(f"Only the taxable portion ({self._format_number(taxable_amount, currency=True)}) is subject to schablonbeskattning. "
                                     f"The tax-free level for {tax_year} is {self._format_number(tax_free_level, currency=True)}.",
                                     self.styles['Normal']))

        # --- 3c. SMART RECOMMENDATIONS ---
        recommendations = data.get('recommendations')
        if recommendations and len(recommendations) > 0:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("3c. Smart Recommendations", self.styles['SubsectionHeading']))
            story.append(Paragraph("Based on your portfolio settings and Swedish tax regulations, here are personalized recommendations to optimize your returns:",
                                 self.styles['Normal']))
            story.append(Spacer(1, 0.1*inch))

            for i, rec in enumerate(recommendations, 1):
                # Clean up emoji from recommendations for PDF
                rec_text = rec.replace('💡', '').replace('💰', '').replace('✅', '').replace('🎉', '').strip()
                story.append(Paragraph(f"<b>{i}.</b> {rec_text}", self.styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
        
        # --- 4. OPTIMIZATION RESULTS ---
        if opt_sec_num:
            story.append(PageBreak())
            opt = data['optimizationResults']
            story.append(Paragraph(f"{opt_sec_num}. Optimization Results", self.styles['SectionHeading']))
            rec = (opt.get('optimization_metadata') or {}).get('recommendation', 'weights')
            story.append(Paragraph(f"Recommended Strategy: {rec.replace('_', ' ').title()}.", self.styles['SubsectionHeading']))
            
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
                    'Sharpe Ratio',
                    self._format_number(current.get('sharpe_ratio', 0), decimals=3),
                    self._format_number(wo_metrics.get('sharpe_ratio', 0), decimals=3)
                ] + ([self._format_number(mo_metrics.get('sharpe_ratio', 0), decimals=3)] if has_market else []))
                
                story.append(self._create_table(opt_table))
                story.append(Spacer(1, 0.2*inch))

            if MPL_AVAILABLE:
                try:
                    plt.figure(figsize=(10, 6))
                    random_portfolios = opt.get('market_optimized_portfolio', {}).get('random_portfolios') or \
                                       opt.get('weights_optimized_portfolio', {}).get('random_portfolios')
                    if random_portfolios:
                        plt.scatter([p['risk'] for p in random_portfolios], [p['return'] for p in random_portfolios], 
                                   c='lightgrey', s=10, alpha=0.5, label='Random Portfolios')
                    frontier = opt.get('market_optimized_portfolio', {}).get('efficient_frontier') or \
                               opt.get('weights_optimized_portfolio', {}).get('efficient_frontier')
                    if frontier:
                        plt.plot([p['risk'] for p in frontier], [p['return'] for p in frontier], 'b-', linewidth=2, label='Efficient Frontier')
                    if current:
                        plt.scatter(current.get('risk', 0), current.get('expected_return', 0), c='red', s=100, marker='*', label='Current')
                    if wo_metrics:
                        plt.scatter(wo_metrics.get('risk', 0), wo_metrics.get('expected_return', 0), c='blue', s=80, marker='D', label='Weights Optimized')
                    if mo_metrics:
                        plt.scatter(mo_metrics.get('risk', 0), mo_metrics.get('expected_return', 0), c='green', s=80, marker='s', label='Market Optimized')
                    
                    plt.title('Portfolio Optimization: Risk vs Return')
                    plt.xlabel('Annualized Risk (Volatility)')
                    plt.ylabel('Annualized Expected Return')
                    plt.grid(True, linestyle='--', alpha=0.7)
                    plt.legend()
                    story.append(self._generate_plot(plt))
                    story.append(Paragraph("Figure 2: The Efficient Frontier represents the set of optimal portfolios that offer the highest expected return for a defined level of risk. "
                                         "Your current portfolio is compared against mathematically optimized alternatives.", self.styles['ChartExplanation']))
                except Exception as plot_e:
                    logger.warning(f"Failed to generate optimization plot: {plot_e}")

        # --- 5. STRESS TEST ANALYSIS ---
        if stress_sec_num:
            story.append(PageBreak())
            stress = data['stressTestResults']
            story.append(Paragraph(f"{stress_sec_num}. Stress Test Analysis", self.styles['SectionHeading']))
            resilience = stress.get('resilience_score')
            if resilience is not None:
                story.append(Paragraph(f"Overall Resilience Score: {self._format_number(resilience, decimals=0)}/100.", self.styles['SubsectionHeading']))
            
            scenarios = stress.get('scenarios') or stress.get('scenario_results') or {}
            if scenarios:
                story.append(Paragraph("Historical simulation of portfolio performance during past market crises. "
                                     "This helps evaluate potential downside risk during extreme market events.", self.styles['Normal']))
                
                if MPL_AVAILABLE:
                    try:
                        plt.figure(figsize=(10, 6))
                        names, impacts = [], []
                        for name, res in scenarios.items():
                            if isinstance(res, dict):
                                impact = res.get('portfolio_impact') or res.get('impact')
                                if impact is not None:
                                    names.append(name.replace('_', ' ').title())
                                    impacts.append(impact * 100)
                        if names:
                            sorted_indices = sorted(range(len(impacts)), key=lambda k: impacts[k])
                            names = [names[i] for i in sorted_indices]
                            impacts = [impacts[i] for i in sorted_indices]
                            plt.barh(names, impacts, color=['red' if x < 0 else 'green' for x in impacts])
                            plt.title('Stress Test: Historical Scenario Impact')
                            plt.xlabel('Portfolio Value Change (%)')
                            plt.grid(True, axis='x', linestyle='--', alpha=0.7)
                            story.append(self._generate_plot(plt))
                            story.append(Paragraph("Figure 3: Estimated percentage change in portfolio value under historical stress scenarios. "
                                                 "Negative values indicate potential losses during the specified period.", self.styles['ChartExplanation']))
                    except Exception as plot_e:
                        logger.warning(f"Failed to generate stress test plot: {plot_e}")

        # --- 6. TRANSACTION COST ANALYSIS ---
        story.append(PageBreak())
        story.append(Paragraph(f"{cost_sec_num}. Transaction Cost Analysis", self.styles['SectionHeading']))
        cost_data = data.get('costData', {}) or {}
        if cost_data:
            cost_table_data = [['Cost Component', 'Value']]
            setup = cost_data.get('setupCost') or cost_data.get('setup_cost')
            annual = cost_data.get('annualRebalancingCost') or cost_data.get('annual_rebalancing_cost')
            total_first = cost_data.get('totalFirstYearCost') or cost_data.get('total_first_year_cost')
            courtage = cost_data.get('courtageClass') or cost_data.get('courtage_class')
            if setup is not None:
                cost_table_data.append(['Initial Setup (Trading)', self._format_number(float(setup), currency=True)])
            if annual is not None:
                cost_table_data.append(['Est. Annual Rebalancing', self._format_number(float(annual), currency=True)])
            if total_first is not None:
                cost_table_data.append(['Total Estimated Year 1', self._format_number(float(total_first), currency=True)])
            if courtage:
                cost_table_data.append(['Courtage Class', str(courtage).capitalize()])
            story.append(self._create_table(cost_table_data, col_widths=[3.5*inch, 3.7*inch]))
        else:
            story.append(Paragraph("No transaction cost data available.", self.styles['Normal']))

        # --- 7. 5-YEAR PROJECTION ---
        story.append(PageBreak())
        story.append(Paragraph(f"{proj_sec_num}. 5-Year Projection (Tax & Cost Adjusted)", self.styles['SectionHeading']))
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
                    courtage_class=(cost_data.get('courtageClass') or 'medium').lower(),
                    rebalancing_frequency='quarterly',
                )
                proj_table = [['Year', 'Optimistic', 'Base Case', 'Pessimistic']]
                for i, year in enumerate(proj.get('years', [])):
                    proj_table.append([str(year), 
                                     self._format_number(proj['optimistic'][i], decimals=0, currency=True),
                                     self._format_number(proj['base'][i], decimals=0, currency=True),
                                     self._format_number(proj['pessimistic'][i], decimals=0, currency=True)])
                story.append(self._create_table(proj_table))
                
                if MPL_AVAILABLE:
                    plt.figure(figsize=(10, 6))
                    plt.plot(proj['years'], proj['optimistic'], 'g-', marker='o', label='Optimistic')
                    plt.plot(proj['years'], proj['base'], 'b-', marker='o', label='Base Case')
                    plt.plot(proj['years'], proj['pessimistic'], 'r-', marker='o', label='Pessimistic')
                    plt.title('5-Year Value Projection')
                    plt.ylabel('Portfolio Value (SEK)')
                    plt.legend()
                    plt.grid(True, alpha=0.3)
                    
                    # Format Y-axis
                    from matplotlib.ticker import FuncFormatter
                    def format_sek(x, pos):
                        if x >= 1e6: return f'{x/1e6:.1f}M'
                        if x >= 1e3: return f'{x/1e3:.0f}k'
                        return f'{x:.0f}'
                    plt.gca().yaxis.set_major_formatter(FuncFormatter(format_sek))
                    
                    story.append(self._generate_plot(plt))
                    story.append(Paragraph("Figure 4: Long-term projection over 5 years. "
                                         "Calculations include quarterly rebalancing, Swedish taxes (ISK/KF), and transaction costs. "
                                         "The Optimistic and Pessimistic lines represent the 95th and 5th percentile outcomes respectively.", self.styles['ChartExplanation']))
            except Exception as e:
                logger.warning(f"Could not add 5-year projection: {e}")

        # --- 8. RISK ANALYSIS & METRICS ---
        story.append(PageBreak())
        story.append(Paragraph(f"{risk_sec_num}. Risk Analysis & Metrics", self.styles['SectionHeading']))
        if metrics:
            risk_table = [['Metric', 'Value']]
            if 'diversificationScore' in metrics:
                risk_table.append(['Diversification Score', self._format_number(metrics['diversificationScore'], decimals=2)])
            if 'sharpeRatio' in metrics:
                risk_table.append(['Sharpe Ratio', self._format_number(metrics['sharpeRatio'], decimals=3)])
            if 'risk' in metrics:
                risk_table.append(['Annualized Volatility', self._format_percentage(metrics['risk'])])
            
            story.append(self._create_table(risk_table, col_widths=[3.5*inch, 3.7*inch]))
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph("Diversification Score (0-100): Measures how effectively the portfolio spreads risk across uncorrelated assets. "
                                 "Higher scores indicate better resilience to single-asset volatility.", self.styles['Normal']))
            story.append(Paragraph("Sharpe Ratio: Measures excess return per unit of risk. A higher ratio indicates more efficient risk-taking.", self.styles['Normal']))

        # Final Build
        doc.build(story, canvasmaker=PageNumCanvas)
        buffer.seek(0)
        return buffer.getvalue()

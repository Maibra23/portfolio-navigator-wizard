#!/usr/bin/env python3
"""
PDF Report Generator
Generates comprehensive PDF reports for portfolios using reportlab.
Includes: Executive Summary, Portfolio, Tax, Optimization summary, Stress Test, Costs, 5-Year Projection, Metrics.
"""

import logging
from typing import Dict, List, Optional, Any
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors

try:
    from .five_year_projection import run_five_year_projection
except ImportError:
    run_five_year_projection = None
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

logger = logging.getLogger(__name__)


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
        """Format a percentage for display"""
        if value is None:
            return "N/A"
        return f"{value:.{decimals}f}%"
    
    def generate_portfolio_report(self, data: Dict[str, Any]) -> bytes:
        """
        Generate comprehensive PDF report
        
        Sections:
        1. Executive Summary
        2. Portfolio Composition & Allocations
        3. Swedish Tax Analysis
        4. Optimization Results (if available)
        5. Stress Test Analysis (if available)
        6. Goal-Based Projections (if available)
        7. Rebalancing Recommendations (if available)
        8. Transaction Cost Analysis
        9. Risk Analysis & Metrics
        
        Args:
            data: Dictionary containing all portfolio data
            
        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=self.page_size)
        story = []
        
        # Title
        story.append(Paragraph("Portfolio Analysis Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.2*inch))
        
        # Report metadata
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(f"Generated: {report_date}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # 1. Executive Summary
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
        
        if 'expectedReturn' in data:
            summary_data.append(['Expected Return', self._format_percentage(data['expectedReturn'])])
        if 'risk' in data:
            summary_data.append(['Risk (Volatility)', self._format_percentage(data['risk'])])
        if 'sharpeRatio' in data:
            summary_data.append(['Sharpe Ratio', self._format_number(data['sharpeRatio'], decimals=3)])
        
        story.append(self._create_table(summary_data, col_widths=[3*inch, 4*inch]))
        story.append(Spacer(1, 0.3*inch))
        
        # 2. Portfolio Composition & Allocations
        story.append(Paragraph("2. Portfolio Composition & Allocations", self.styles['SectionHeading']))
        
        portfolio = data.get('portfolio', [])
        if portfolio:
            comp_data = [['Ticker', 'Allocation', 'Value (SEK)']]
            for pos in portfolio:
                ticker = pos.get('ticker', pos.get('symbol', 'N/A'))
                allocation = pos.get('allocation', 0.0)
                value = portfolio_value * allocation if portfolio_value else 0.0
                comp_data.append([
                    ticker,
                    self._format_percentage(allocation * 100),
                    self._format_number(value, currency=True)
                ])
            
            story.append(self._create_table(comp_data))
        else:
            story.append(Paragraph("No portfolio data available.", self.styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # 3. Swedish Tax Analysis
        story.append(Paragraph("3. Swedish Tax Analysis", self.styles['SectionHeading']))
        
        tax_data = data.get('taxData', {}) or {}
        if tax_data:
            tax_table_data = [['Tax Component', 'Value']]
            annual_tax = tax_data.get('annualTax') or tax_data.get('annual_tax')
            eff_rate = tax_data.get('effectiveTaxRate') or tax_data.get('effective_tax_rate')
            tax_free = tax_data.get('taxFreeLevel') or tax_data.get('tax_free_level')
            taxable_cap = tax_data.get('taxableCapital') or tax_data.get('taxable_capital')
            if annual_tax is not None:
                tax_table_data.append(['Annual Tax', self._format_number(float(annual_tax), currency=True)])
            if eff_rate is not None:
                tax_table_data.append(['Effective Tax Rate', self._format_percentage(float(eff_rate))])
            if tax_free is not None:
                tax_table_data.append(['Tax-Free Level', self._format_number(float(tax_free), currency=True)])
            if taxable_cap is not None:
                tax_table_data.append(['Taxable Capital', self._format_number(float(taxable_cap), currency=True)])
            if len(tax_table_data) > 1:
                story.append(self._create_table(tax_table_data, col_widths=[3*inch, 4*inch]))
            else:
                story.append(Paragraph("No tax details available.", self.styles['Normal']))
        else:
            story.append(Paragraph("No tax data available.", self.styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # 4. Optimization Results (if available)
        if data.get('includeSections', {}).get('optimization', False) and data.get('optimizationResults'):
            opt = data['optimizationResults']
            story.append(Paragraph("4. Optimization Results", self.styles['SectionHeading']))
            rec = (opt.get('optimization_metadata') or {}).get('recommendation', 'weights')
            story.append(Paragraph(f"Recommendation: {rec}.", self.styles['Normal']))
            current = (opt.get('current_portfolio') or {}).get('metrics', {})
            weights_opt = (opt.get('weights_optimized_portfolio') or {}).get('optimized_portfolio', {})
            wo_metrics = weights_opt.get('metrics', {})
            if current or wo_metrics:
                opt_table = [['Metric', 'Current', 'Weights-Optimized']]
                opt_table.append([
                    'Expected Return',
                    self._format_percentage(current.get('expected_return', 0)),
                    self._format_percentage(wo_metrics.get('expected_return', 0))
                ])
                opt_table.append([
                    'Risk',
                    self._format_percentage(current.get('risk', 0)),
                    self._format_percentage(wo_metrics.get('risk', 0))
                ])
                opt_table.append([
                    'Sharpe Ratio',
                    self._format_number(current.get('sharpe_ratio', 0), decimals=3),
                    self._format_number(wo_metrics.get('sharpe_ratio', 0), decimals=3)
                ])
                story.append(self._create_table(opt_table, col_widths=[2*inch, 2*inch, 2*inch]))
            story.append(Spacer(1, 0.3*inch))
        
        # 5. Stress Test Analysis (if available)
        if data.get('includeSections', {}).get('stressTest', False) and data.get('stressTestResults'):
            stress = data['stressTestResults']
            story.append(Paragraph("5. Stress Test Analysis", self.styles['SectionHeading']))
            resilience = stress.get('resilience_score')
            if resilience is not None:
                story.append(Paragraph(f"Resilience Score: {self._format_number(resilience, decimals=0)}.", self.styles['Normal']))
            scenarios = stress.get('scenarios') or stress.get('scenario_results') or {}
            if scenarios:
                scenario_names = list(scenarios.keys())[:5]
                story.append(Paragraph("Scenarios: " + ", ".join(str(s) for s in scenario_names) + ".", self.styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
        
        # 6. Goal-Based Projections (if available)
        if data.get('includeSections', {}).get('goals', False) and data.get('goalProjections'):
            story.append(Paragraph("6. Goal-Based Projections", self.styles['SectionHeading']))
            story.append(Paragraph("Goal-based projections would be displayed here.", self.styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
        
        # 7. Rebalancing Recommendations (if available)
        if data.get('includeSections', {}).get('rebalancing', False) and data.get('rebalancingRecommendations'):
            story.append(Paragraph("7. Rebalancing Recommendations", self.styles['SectionHeading']))
            story.append(Paragraph("Rebalancing recommendations would be displayed here.", self.styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
        
        # 8. Transaction Cost Analysis
        story.append(Paragraph("8. Transaction Cost Analysis", self.styles['SectionHeading']))
        
        cost_data = data.get('costData', {}) or {}
        if cost_data:
            cost_table_data = [['Cost Component', 'Value']]
            setup = cost_data.get('setupCost') or cost_data.get('setup_cost')
            annual = cost_data.get('annualRebalancingCost') or cost_data.get('annual_rebalancing_cost')
            total_first = cost_data.get('totalFirstYearCost') or cost_data.get('total_first_year_cost')
            courtage = cost_data.get('courtageClass') or cost_data.get('courtage_class')
            if setup is not None:
                cost_table_data.append(['Setup Cost', self._format_number(float(setup), currency=True)])
            if annual is not None:
                cost_table_data.append(['Annual Rebalancing Cost', self._format_number(float(annual), currency=True)])
            if total_first is not None:
                cost_table_data.append(['Total First Year Cost', self._format_number(float(total_first), currency=True)])
            if courtage:
                cost_table_data.append(['Courtage Class', str(courtage)])
            if len(cost_table_data) > 1:
                story.append(self._create_table(cost_table_data, col_widths=[3*inch, 4*inch]))
            else:
                story.append(Paragraph("No cost details available.", self.styles['Normal']))
        else:
            story.append(Paragraph("No transaction cost data available.", self.styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # 9. 5-Year Projection (if we have required inputs). Use projectionMetrics when provided (recommended portfolio from Optimize tab).
        portfolio_value = data.get('portfolioValue', 0.0)
        account_type = data.get('accountType')
        tax_year = data.get('taxYear', datetime.now().year)
        metrics = data.get('metrics') or {}
        projection_metrics = data.get('projectionMetrics') or {}
        weights = projection_metrics.get('weights') or (data.get('portfolio') or {}).get('weights') or {}
        if not weights and (data.get('portfolio') or {}).get('allocations'):
            weights = {a.get('symbol', a.get('ticker', '')): (a.get('allocation', 0) / 100.0) for a in (data.get('portfolio') or {}).get('allocations', []) if a.get('symbol') or a.get('ticker')}
        exp_return = (projection_metrics.get('expectedReturn') if projection_metrics.get('expectedReturn') is not None else projection_metrics.get('expected_return')) if projection_metrics else None
        if exp_return is None:
            exp_return = metrics.get('expectedReturn', metrics.get('expected_return', 0.08))
        risk_val = projection_metrics.get('risk') if (projection_metrics and 'risk' in projection_metrics) else metrics.get('risk', 0.15)
        courtage_class = (cost_data.get('courtageClass') or cost_data.get('courtage_class') or '').lower() or 'medium'
        if courtage_class == 'fastpris':
            courtage_class = 'fastPris'
        if run_five_year_projection and portfolio_value and account_type and weights and 2025 <= tax_year <= 2026:
            try:
                proj = run_five_year_projection(
                    initial_capital=float(portfolio_value),
                    weights={k: float(v) for k, v in weights.items() if v and k},
                    expected_return=float(exp_return) if exp_return is not None else 0.08,
                    risk=float(risk_val) if risk_val is not None else 0.15,
                    account_type=str(account_type),
                    tax_year=int(tax_year),
                    courtage_class=courtage_class or 'medium',
                    rebalancing_frequency='quarterly',
                )
                story.append(Paragraph("9. 5-Year Projection (Tax & Cost Adjusted)", self.styles['SectionHeading']))
                proj_table = [['Year', 'Optimistic (SEK)', 'Base (SEK)', 'Pessimistic (SEK)']]
                for i, year in enumerate(proj.get('years', [])):
                    proj_table.append([
                        str(year),
                        self._format_number(proj.get('optimistic', [])[i], decimals=0),
                        self._format_number(proj.get('base', [])[i], decimals=0),
                        self._format_number(proj.get('pessimistic', [])[i], decimals=0),
                    ])
                story.append(self._create_table(proj_table, col_widths=[1*inch, 1.8*inch, 1.8*inch, 1.8*inch]))
                story.append(Spacer(1, 0.3*inch))
            except Exception as e:
                logger.warning(f"Could not add 5-year projection to PDF: {e}")
        
        # 10. Risk Analysis & Metrics
        story.append(Paragraph("10. Risk Analysis & Metrics", self.styles['SectionHeading']))
        
        metrics = data.get('metrics', {})
        if metrics:
            metrics_table_data = [['Metric', 'Value']]
            
            if 'expectedReturn' in metrics:
                metrics_table_data.append(['Expected Return', self._format_percentage(metrics['expectedReturn'])])
            if 'risk' in metrics:
                metrics_table_data.append(['Risk (Volatility)', self._format_percentage(metrics['risk'])])
            if 'sharpeRatio' in metrics:
                metrics_table_data.append(['Sharpe Ratio', self._format_number(metrics['sharpeRatio'], decimals=3)])
            if 'diversificationScore' in metrics:
                metrics_table_data.append(['Diversification Score', self._format_number(metrics['diversificationScore'], decimals=2)])
            
            story.append(self._create_table(metrics_table_data, col_widths=[3*inch, 4*inch]))
        else:
            story.append(Paragraph("No risk metrics available.", self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

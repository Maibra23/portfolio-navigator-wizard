#!/usr/bin/env python3
"""
PDF Report Generator
Generates comprehensive PDF reports for portfolios using reportlab
"""

import logging
from typing import Dict, List, Optional, Any
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
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
        
        tax_data = data.get('taxData', {})
        if tax_data:
            tax_table_data = [['Tax Component', 'Value']]
            
            if 'annual_tax' in tax_data:
                tax_table_data.append(['Annual Tax', self._format_number(tax_data['annual_tax'], currency=True)])
            if 'effective_tax_rate' in tax_data:
                tax_table_data.append(['Effective Tax Rate', self._format_percentage(tax_data['effective_tax_rate'])])
            if 'tax_free_level' in tax_data:
                tax_table_data.append(['Tax-Free Level', self._format_number(tax_data['tax_free_level'], currency=True)])
            if 'taxable_capital' in tax_data:
                tax_table_data.append(['Taxable Capital', self._format_number(tax_data['taxable_capital'], currency=True)])
            
            story.append(self._create_table(tax_table_data, col_widths=[3*inch, 4*inch]))
        else:
            story.append(Paragraph("No tax data available.", self.styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # 4. Optimization Results (if available)
        if data.get('includeSections', {}).get('optimization', False) and 'optimizationResults' in data:
            story.append(Paragraph("4. Optimization Results", self.styles['SectionHeading']))
            story.append(Paragraph("Optimization results would be displayed here.", self.styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
        
        # 5. Stress Test Analysis (if available)
        if data.get('includeSections', {}).get('stressTest', False) and 'stressTestResults' in data:
            story.append(Paragraph("5. Stress Test Analysis", self.styles['SectionHeading']))
            story.append(Paragraph("Stress test results would be displayed here.", self.styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
        
        # 6. Goal-Based Projections (if available)
        if data.get('includeSections', {}).get('goals', False) and 'goalProjections' in data:
            story.append(Paragraph("6. Goal-Based Projections", self.styles['SectionHeading']))
            story.append(Paragraph("Goal-based projections would be displayed here.", self.styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
        
        # 7. Rebalancing Recommendations (if available)
        if data.get('includeSections', {}).get('rebalancing', False) and 'rebalancingRecommendations' in data:
            story.append(Paragraph("7. Rebalancing Recommendations", self.styles['SectionHeading']))
            story.append(Paragraph("Rebalancing recommendations would be displayed here.", self.styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
        
        # 8. Transaction Cost Analysis
        story.append(Paragraph("8. Transaction Cost Analysis", self.styles['SectionHeading']))
        
        cost_data = data.get('costData', {})
        if cost_data:
            cost_table_data = [['Cost Component', 'Value']]
            
            if 'setup_cost' in cost_data:
                cost_table_data.append(['Setup Cost', self._format_number(cost_data['setup_cost'], currency=True)])
            if 'annual_rebalancing_cost' in cost_data:
                cost_table_data.append(['Annual Rebalancing Cost', self._format_number(cost_data['annual_rebalancing_cost'], currency=True)])
            if 'total_first_year_cost' in cost_data:
                cost_table_data.append(['Total First Year Cost', self._format_number(cost_data['total_first_year_cost'], currency=True)])
            if 'courtage_class' in cost_data:
                cost_table_data.append(['Courtage Class', cost_data['courtage_class']])
            
            story.append(self._create_table(cost_table_data, col_widths=[3*inch, 4*inch]))
        else:
            story.append(Paragraph("No transaction cost data available.", self.styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # 9. Risk Analysis & Metrics
        story.append(Paragraph("9. Risk Analysis & Metrics", self.styles['SectionHeading']))
        
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

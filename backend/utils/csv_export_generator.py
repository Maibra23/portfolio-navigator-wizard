#!/usr/bin/env python3
"""
CSV Export Generator
Generates CSV exports for portfolio data
"""

import logging
import csv
from typing import Dict, List, Optional, Any
from io import StringIO
from datetime import datetime

logger = logging.getLogger(__name__)


class CSVExportGenerator:
    """
    Generates CSV exports for various portfolio data
    """
    
    def __init__(self):
        """Initialize the CSV generator"""
        pass
    
    def _format_number(self, value: float, decimals: int = 2) -> str:
        """Format a number for CSV"""
        if value is None:
            return ""
        return f"{value:.{decimals}f}"
    
    def generate_portfolio_holdings_csv(self, portfolio: List[Dict]) -> str:
        """
        Generate portfolio_holdings.csv
        
        Args:
            portfolio: List of portfolio positions
            
        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Ticker', 'Symbol', 'Shares', 'Allocation', 'Value (SEK)', 'Name', 'Asset Type'])
        
        # Data rows
        for pos in portfolio:
            ticker = pos.get('ticker', pos.get('symbol', ''))
            symbol = pos.get('symbol', ticker)
            shares = pos.get('shares', 0)
            allocation = pos.get('allocation', 0.0)
            value = pos.get('value', 0.0)
            name = pos.get('name', '')
            asset_type = pos.get('assetType', '')
            
            writer.writerow([
                ticker,
                symbol,
                shares,
                self._format_number(allocation * 100, decimals=4),  # Percentage
                self._format_number(value, decimals=2),
                name,
                asset_type
            ])
        
        return output.getvalue()
    
    def generate_tax_analysis_csv(self, tax_data: Dict) -> str:
        """
        Generate tax_analysis.csv
        
        Args:
            tax_data: Tax calculation data
            
        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Tax Component', 'Value (SEK)', 'Percentage'])
        
        account_type = tax_data.get('account_type', 'N/A')
        tax_year = tax_data.get('tax_year', 'N/A')
        
        writer.writerow(['Account Type', account_type, ''])
        writer.writerow(['Tax Year', str(tax_year), ''])
        writer.writerow(['', '', ''])  # Empty row
        
        # Tax details
        if 'capital_underlag' in tax_data:
            writer.writerow(['Capital Underlag', self._format_number(tax_data['capital_underlag']), ''])
        
        if 'tax_free_level' in tax_data:
            writer.writerow(['Tax-Free Level', self._format_number(tax_data['tax_free_level']), ''])
        
        if 'taxable_capital' in tax_data:
            writer.writerow(['Taxable Capital', self._format_number(tax_data['taxable_capital']), ''])
        
        if 'annual_tax' in tax_data:
            writer.writerow(['Annual Tax', self._format_number(tax_data['annual_tax']), ''])
        
        if 'effective_tax_rate' in tax_data:
            writer.writerow(['Effective Tax Rate', '', self._format_number(tax_data['effective_tax_rate'], decimals=3)])
        
        # AF-specific fields
        if 'realized_gains' in tax_data:
            writer.writerow(['Realized Gains', self._format_number(tax_data['realized_gains']), ''])
        
        if 'capital_gains_tax' in tax_data:
            writer.writerow(['Capital Gains Tax', self._format_number(tax_data['capital_gains_tax']), ''])
        
        if 'dividend_tax' in tax_data:
            writer.writerow(['Dividend Tax', self._format_number(tax_data['dividend_tax']), ''])
        
        if 'fund_schablon_tax' in tax_data:
            writer.writerow(['Fund Schablon Tax', self._format_number(tax_data['fund_schablon_tax']), ''])
        
        if 'total_tax' in tax_data:
            writer.writerow(['Total Tax (AF)', self._format_number(tax_data['total_tax']), ''])
        
        return output.getvalue()
    
    def generate_transaction_costs_csv(self, cost_data: Dict) -> str:
        """
        Generate transaction_costs.csv
        
        Args:
            cost_data: Transaction cost data
            
        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Cost Component', 'Value (SEK)', 'Details'])
        
        courtage_class = cost_data.get('courtage_class', 'N/A')
        writer.writerow(['Courtage Class', courtage_class, ''])
        writer.writerow(['', '', ''])  # Empty row
        
        # Setup costs
        if 'setup_cost' in cost_data:
            writer.writerow(['Setup Cost', self._format_number(cost_data['setup_cost']), ''])
        
        if 'setup_breakdown' in cost_data:
            writer.writerow(['', '', ''])  # Empty row
            writer.writerow(['Setup Breakdown', '', ''])
            writer.writerow(['Ticker', 'Shares', 'Value (SEK)', 'Courtage (SEK)'])
            
            for item in cost_data['setup_breakdown']:
                writer.writerow([
                    item.get('ticker', ''),
                    item.get('shares', 0),
                    self._format_number(item.get('value', 0)),
                    self._format_number(item.get('courtage', 0))
                ])
        
        writer.writerow(['', '', ''])  # Empty row
        
        # Rebalancing costs
        if 'annual_rebalancing_cost' in cost_data:
            writer.writerow(['Annual Rebalancing Cost', self._format_number(cost_data['annual_rebalancing_cost']), ''])
        
        if 'per_rebalance_cost' in cost_data:
            writer.writerow(['Per Rebalance Cost', self._format_number(cost_data['per_rebalance_cost']), ''])
        
        if 'rebalancing_frequency' in cost_data:
            writer.writerow(['Rebalancing Frequency', cost_data['rebalancing_frequency'], ''])
        
        if 'total_first_year_cost' in cost_data:
            writer.writerow(['Total First Year Cost', self._format_number(cost_data['total_first_year_cost']), ''])
        
        return output.getvalue()
    
    def generate_portfolio_metrics_csv(self, metrics: Dict) -> str:
        """
        Generate portfolio_metrics.csv
        
        Args:
            metrics: Portfolio metrics data
            
        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Metric', 'Value'])
        
        # Metrics
        if 'expectedReturn' in metrics:
            writer.writerow(['Expected Return (%)', self._format_number(metrics['expectedReturn'], decimals=2)])
        
        if 'risk' in metrics:
            writer.writerow(['Risk / Volatility (%)', self._format_number(metrics['risk'], decimals=2)])
        
        if 'sharpeRatio' in metrics:
            writer.writerow(['Sharpe Ratio', self._format_number(metrics['sharpeRatio'], decimals=3)])
        
        if 'diversificationScore' in metrics:
            writer.writerow(['Diversification Score', self._format_number(metrics['diversificationScore'], decimals=2)])
        
        if 'totalAllocation' in metrics:
            writer.writerow(['Total Allocation', self._format_number(metrics['totalAllocation'] * 100, decimals=2)])
        
        if 'stockCount' in metrics:
            writer.writerow(['Stock Count', str(metrics['stockCount'])])
        
        # Tax-adjusted metrics
        if 'grossExpectedReturn' in metrics:
            writer.writerow(['Gross Expected Return (%)', self._format_number(metrics['grossExpectedReturn'], decimals=2)])
        
        if 'annualTaxImpact' in metrics:
            writer.writerow(['Annual Tax Impact (SEK)', self._format_number(metrics['annualTaxImpact'])])
        
        if 'afterTaxReturn' in metrics:
            writer.writerow(['After-Tax Return (%)', self._format_number(metrics['afterTaxReturn'], decimals=2)])
        
        if 'netExpectedReturn' in metrics:
            writer.writerow(['Net Expected Return (%)', self._format_number(metrics['netExpectedReturn'], decimals=2)])
        
        return output.getvalue()
    
    def generate_stress_test_csv(self, stress_data: Dict) -> str:
        """
        Generate stress_test_results.csv
        
        Args:
            stress_data: Stress test results
            
        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Scenario', 'Portfolio Value (SEK)', 'Return (%)', 'Details'])
        
        scenarios = stress_data.get('scenarios', [])
        for scenario in scenarios:
            scenario_name = scenario.get('name', 'Unknown')
            portfolio_value = scenario.get('portfolioValue', 0.0)
            return_pct = scenario.get('return', 0.0)
            details = scenario.get('details', '')
            
            writer.writerow([
                scenario_name,
                self._format_number(portfolio_value),
                self._format_number(return_pct, decimals=2),
                details
            ])
        
        return output.getvalue()

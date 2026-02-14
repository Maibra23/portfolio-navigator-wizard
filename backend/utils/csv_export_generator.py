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
    
    def generate_portfolio_holdings_csv(self, portfolio: List[Dict], portfolio_value: Optional[float] = None) -> str:
        """
        Generate portfolio_holdings.csv.
        When portfolio_value is provided, Value (SEK) is computed as portfolio_value * allocation (same as PDF).

        Args:
            portfolio: List of portfolio positions (allocation 0-1 per position)
            portfolio_value: Total portfolio value in SEK; used to compute value per holding when not in pos

        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['Ticker', 'Symbol', 'Shares', 'Allocation (%)', 'Value (SEK)', 'Name', 'Asset Type', 'Sector'])

        # Data rows
        for pos in portfolio:
            ticker = pos.get('ticker', pos.get('symbol', ''))
            symbol = pos.get('symbol', ticker)
            shares = pos.get('shares', 0)
            allocation = pos.get('allocation', 0.0)
            # Normalize allocation if stored as percentage (e.g. 25 instead of 0.25)
            if allocation > 1:
                allocation = allocation / 100.0
            # Value: use pos value if set, else compute from portfolio_value (align with PDF)
            if pos.get('value') is not None and pos.get('value') != '':
                value = float(pos.get('value', 0) or 0)
            elif portfolio_value is not None and portfolio_value > 0:
                value = portfolio_value * allocation
            else:
                value = 0.0
            name = pos.get('name', '')
            asset_type = pos.get('assetType', '')
            sector = pos.get('sector', '')

            writer.writerow([
                ticker,
                symbol,
                shares,
                self._format_number(allocation * 100, decimals=4),
                self._format_number(value, decimals=2),
                name,
                asset_type,
                sector
            ])

        return output.getvalue()
    
    def _get(self, d: Dict, *keys: str):
        """Get value from dict using first key that exists (supports snake_case and camelCase)."""
        for k in keys:
            if k in d and d[k] is not None:
                return d[k]
        return None

    def generate_tax_analysis_csv(self, tax_data: Dict) -> str:
        """
        Generate tax_analysis.csv.
        Accepts both snake_case and camelCase keys (e.g. annual_tax or annualTax).
        
        Args:
            tax_data: Tax calculation data
            
        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Tax Component', 'Value (SEK)', 'Percentage'])
        
        account_type = self._get(tax_data, 'account_type', 'accountType') or 'N/A'
        tax_year = self._get(tax_data, 'tax_year', 'taxYear') or 'N/A'
        
        writer.writerow(['Account Type', account_type, ''])
        writer.writerow(['Tax Year', str(tax_year), ''])
        writer.writerow(['', '', ''])  # Empty row
        
        # Tax details (snake_case and camelCase)
        capital_underlag = self._get(tax_data, 'capital_underlag', 'capitalUnderlag')
        if capital_underlag is not None:
            writer.writerow(['Tax Base (Capital)', self._format_number(float(capital_underlag)), ''])
        
        tax_free = self._get(tax_data, 'tax_free_level', 'taxFreeLevel')
        if tax_free is not None:
            writer.writerow(['Tax-Free Level', self._format_number(float(tax_free)), ''])
        
        taxable = self._get(tax_data, 'taxable_capital', 'taxableCapital')
        if taxable is not None:
            writer.writerow(['Taxable Capital', self._format_number(float(taxable)), ''])
        
        annual_tax = self._get(tax_data, 'annual_tax', 'annualTax')
        if annual_tax is not None:
            writer.writerow(['Annual Tax', self._format_number(float(annual_tax)), ''])
        
        eff_rate = self._get(tax_data, 'effective_tax_rate', 'effectiveTaxRate')
        if eff_rate is not None:
            writer.writerow(['Effective Tax Rate', '', self._format_number(float(eff_rate), decimals=3)])
        
        # AF-specific fields (snake_case and camelCase)
        realized = self._get(tax_data, 'realized_gains', 'realizedGains')
        if realized is not None:
            writer.writerow(['Realized Gains', self._format_number(float(realized)), ''])
        cap_gains = self._get(tax_data, 'capital_gains_tax', 'capitalGainsTax')
        if cap_gains is not None:
            writer.writerow(['Capital Gains Tax', self._format_number(float(cap_gains)), ''])
        div_tax = self._get(tax_data, 'dividend_tax', 'dividendTax')
        if div_tax is not None:
            writer.writerow(['Dividend Tax', self._format_number(float(div_tax)), ''])
        fund_tax = self._get(tax_data, 'fund_schablon_tax', 'fundSchablonTax')
        if fund_tax is not None:
            writer.writerow(['Fund Schablon Tax', self._format_number(float(fund_tax)), ''])
        total_tax = self._get(tax_data, 'total_tax', 'totalTax')
        if total_tax is not None:
            writer.writerow(['Total Tax (AF)', self._format_number(float(total_tax)), ''])
        
        return output.getvalue()
    
    def generate_transaction_costs_csv(self, cost_data: Dict) -> str:
        """
        Generate transaction_costs.csv.
        Accepts both snake_case and camelCase keys (e.g. setup_cost or setupCost).
        
        Args:
            cost_data: Transaction cost data
            
        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Cost Component', 'Value (SEK)', 'Details'])
        
        courtage_class = self._get(cost_data, 'courtage_class', 'courtageClass') or 'N/A'
        writer.writerow(['Courtage Class', str(courtage_class), ''])
        writer.writerow(['', '', ''])  # Empty row
        
        # Setup costs
        setup_cost = self._get(cost_data, 'setup_cost', 'setupCost')
        if setup_cost is not None:
            writer.writerow(['Setup Cost', self._format_number(float(setup_cost)), ''])
        
        setup_breakdown = self._get(cost_data, 'setup_breakdown', 'setupBreakdown')
        if setup_breakdown is not None:
            writer.writerow(['', '', ''])  # Empty row
            writer.writerow(['Setup Breakdown', '', ''])
            writer.writerow(['Ticker', 'Shares', 'Value (SEK)', 'Courtage (SEK)'])
            
            for item in (setup_breakdown if isinstance(setup_breakdown, list) else []):
                writer.writerow([
                    item.get('ticker', ''),
                    item.get('shares', 0),
                    self._format_number(item.get('value', 0)),
                    self._format_number(item.get('courtage', 0))
                ])
        
        writer.writerow(['', '', ''])  # Empty row
        
        # Rebalancing costs (snake_case and camelCase)
        annual_rebal = self._get(cost_data, 'annual_rebalancing_cost', 'annualRebalancingCost')
        if annual_rebal is not None:
            writer.writerow(['Annual Rebalancing Cost', self._format_number(float(annual_rebal)), ''])
        per_rebal = self._get(cost_data, 'per_rebalance_cost', 'perRebalanceCost')
        if per_rebal is not None:
            writer.writerow(['Per Rebalance Cost', self._format_number(float(per_rebal)), ''])
        rebal_freq = self._get(cost_data, 'rebalancing_frequency', 'rebalancingFrequency')
        if rebal_freq is not None:
            writer.writerow(['Rebalancing Frequency', str(rebal_freq), ''])
        total_first = self._get(cost_data, 'total_first_year_cost', 'totalFirstYearCost')
        if total_first is not None:
            writer.writerow(['Total First Year Cost', self._format_number(float(total_first)), ''])
        
        return output.getvalue()
    
    def _pct_for_csv(self, value) -> Optional[float]:
        """Normalize percentage: if in (0,1] treat as decimal and return * 100 for CSV display."""
        if value is None:
            return None
        v = float(value)
        if 0 < abs(v) <= 1 and v != 0:
            return v * 100
        return v

    def generate_portfolio_metrics_csv(self, metrics: Dict) -> str:
        """
        Generate portfolio_metrics.csv.
        Accepts both camelCase and snake_case (e.g. expectedReturn or expected_return).
        Values in (0,1] are treated as decimals and shown as percentages (e.g. 0.12 -> 12).
        
        Args:
            metrics: Portfolio metrics data
            
        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Metric', 'Value'])
        
        # Metrics (camelCase and snake_case)
        exp_ret = self._get(metrics, 'expectedReturn', 'expected_return')
        if exp_ret is not None:
            pct = self._pct_for_csv(exp_ret)
            writer.writerow(['Expected Return (%)', self._format_number(pct if pct is not None else exp_ret, decimals=2)])
        
        risk_val = self._get(metrics, 'risk', 'risk')
        if risk_val is not None:
            pct = self._pct_for_csv(risk_val)
            writer.writerow(['Risk / Volatility (%)', self._format_number(pct if pct is not None else risk_val, decimals=2)])
        
        sharpe = self._get(metrics, 'sharpeRatio', 'sharpe_ratio')
        if sharpe is not None:
            writer.writerow(['Sharpe Ratio', self._format_number(float(sharpe), decimals=3)])
        
        div_score = self._get(metrics, 'diversificationScore', 'diversification_score')
        if div_score is not None:
            writer.writerow(['Diversification Score', self._format_number(float(div_score), decimals=2)])
        
        total_alloc = self._get(metrics, 'totalAllocation', 'total_allocation')
        if total_alloc is not None:
            writer.writerow(['Total Allocation', self._format_number(float(total_alloc) * 100, decimals=2)])
        
        stock_count = self._get(metrics, 'stockCount', 'stock_count')
        if stock_count is not None:
            writer.writerow(['Stock Count', str(stock_count)])
        
        # Tax-adjusted metrics
        gross = self._get(metrics, 'grossExpectedReturn', 'gross_expected_return')
        if gross is not None:
            pct = self._pct_for_csv(gross)
            writer.writerow(['Gross Expected Return (%)', self._format_number(pct if pct is not None else gross, decimals=2)])
        
        tax_impact = self._get(metrics, 'annualTaxImpact', 'annual_tax_impact')
        if tax_impact is not None:
            writer.writerow(['Annual Tax Impact (SEK)', self._format_number(float(tax_impact))])
        
        after_tax = self._get(metrics, 'afterTaxReturn', 'after_tax_return')
        if after_tax is not None:
            pct = self._pct_for_csv(after_tax)
            writer.writerow(['After-Tax Return (%)', self._format_number(pct if pct is not None else after_tax, decimals=2)])
        
        net_ret = self._get(metrics, 'netExpectedReturn', 'net_expected_return')
        if net_ret is not None:
            pct = self._pct_for_csv(net_ret)
            writer.writerow(['Net Expected Return (%)', self._format_number(pct if pct is not None else net_ret, decimals=2)])
        
        return output.getvalue()
    
    def generate_stress_test_csv(self, stress_data: Dict) -> str:
        """
        Generate stress_test_results.csv
        
        Args:
            stress_data: Stress test results (scenarios as dict keyed by name or list of objects)
            
        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Summary row
        writer.writerow(['Resilience Score', self._format_number(stress_data.get('resilience_score'), decimals=0)])
        writer.writerow(['Overall Assessment', str(stress_data.get('overall_assessment', 'N/A'))])
        writer.writerow([])
        
        # Header
        writer.writerow(['Scenario', 'Total Return (%)', 'Max Drawdown (%)', 'Recovery Months', 'Details'])
        
        scenarios = stress_data.get('scenarios') or stress_data.get('scenario_results') or {}
        if isinstance(scenarios, dict):
            for scenario_name, scenario_obj in scenarios.items():
                metrics = (scenario_obj or {}).get('metrics', {})
                total_return = (metrics.get('total_return') or 0) * 100
                max_dd = (metrics.get('max_drawdown') or 0) * 100
                recovery = metrics.get('recovery_months') or metrics.get('trajectory_projections', {}).get('moderate_months') or ''
                recovery_str = f"{recovery}" if recovery != '' else 'N/A'
                writer.writerow([
                    scenario_name,
                    self._format_number(total_return, decimals=2),
                    self._format_number(max_dd, decimals=2),
                    recovery_str,
                    (scenario_obj or {}).get('period', {}).get('start', '') or ''
                ])
        else:
            for scenario in (scenarios or []):
                scenario_name = scenario.get('name', 'Unknown')
                portfolio_value = scenario.get('portfolioValue', 0.0)
                return_pct = scenario.get('return', 0.0)
                details = scenario.get('details', '')
                writer.writerow([
                    scenario_name,
                    self._format_number(return_pct, decimals=2),
                    self._format_number(portfolio_value, decimals=0),
                    details,
                    ''
                ])
        
        return output.getvalue()

    def _pct_display(self, value: Any) -> Optional[str]:
        """Format as percentage for display; values in (0,1] treated as decimal."""
        if value is None:
            return None
        v = float(value)
        if 0 < abs(v) <= 1 and v != 0:
            v = v * 100
        return self._format_number(v, decimals=2)

    def generate_optimization_comparison_csv(self, opt_results: Dict) -> str:
        """
        Generate optimization_comparison.csv (same content as PDF section 4).
        Columns: Portfolio, Expected Return (%), Risk (%), Sharpe Ratio.
        """
        output = StringIO()
        writer = csv.writer(output)
        current = (opt_results.get('current_portfolio') or {}).get('metrics', {})
        wo = (opt_results.get('weights_optimized_portfolio') or {}).get('optimized_portfolio', {})
        wo_metrics = wo.get('metrics', {})
        mo = (opt_results.get('market_optimized_portfolio') or {}).get('optimized_portfolio', {})
        mo_metrics = mo.get('metrics', {}) if mo else {}
        has_market = bool(mo_metrics)
        headers = ['Portfolio', 'Expected Return (%)', 'Risk (%)', 'Sharpe Ratio']
        writer.writerow(headers)
        if current:
            writer.writerow([
                'Current',
                self._pct_display(current.get('expected_return')) or '',
                self._pct_display(current.get('risk')) or '',
                self._format_number(current.get('sharpe_ratio'), decimals=3) if current.get('sharpe_ratio') is not None else ''
            ])
        if wo_metrics:
            writer.writerow([
                'Weights-Optimized',
                self._pct_display(wo_metrics.get('expected_return')) or '',
                self._pct_display(wo_metrics.get('risk')) or '',
                self._format_number(wo_metrics.get('sharpe_ratio'), decimals=3) if wo_metrics.get('sharpe_ratio') is not None else ''
            ])
        if has_market:
            writer.writerow([
                'Market-Optimized',
                self._pct_display(mo_metrics.get('expected_return')) or '',
                self._pct_display(mo_metrics.get('risk')) or '',
                self._format_number(mo_metrics.get('sharpe_ratio'), decimals=3) if mo_metrics.get('sharpe_ratio') is not None else ''
            ])
        return output.getvalue()

    def generate_quality_scores_csv(self, opt_results: Dict) -> str:
        """Generate quality_scores.csv from optimizationResults.comparison.quality_scores."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Portfolio', 'Composite Score'])
        comparison = opt_results.get('comparison') or {}
        quality_scores = comparison.get('quality_scores') or {}
        for key, q in quality_scores.items():
            if q and isinstance(q, dict):
                score = q.get('composite_score') or q.get('compositeScore')
                if score is not None:
                    writer.writerow([key.replace('_', ' ').title(), self._format_number(float(score), decimals=1)])
        return output.getvalue()

    def generate_monte_carlo_csv(self, opt_results: Dict) -> str:
        """Generate monte_carlo_summary.csv from optimizationResults.comparison.monte_carlo."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Portfolio', 'Percentile 5%', 'Percentile 50%', 'Percentile 95%'])
        comparison = opt_results.get('comparison') or {}
        monte_carlo = comparison.get('monte_carlo') or {}
        for key, mc in monte_carlo.items():
            if mc and isinstance(mc, dict):
                p5 = mc.get('percentile_5') or mc.get('percentile5')
                p50 = mc.get('percentile_50') or mc.get('percentile50')
                p95 = mc.get('percentile_95') or mc.get('percentile95')
                writer.writerow([
                    key.replace('_', ' ').title(),
                    p5 if p5 is not None else '',
                    p50 if p50 is not None else '',
                    p95 if p95 is not None else ''
                ])
        return output.getvalue()

    def generate_five_year_projection_csv(self, proj: Dict) -> str:
        """Generate five_year_projection.csv (same content as PDF section 9). proj: {years, optimistic, base, pessimistic}."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Year', 'Optimistic (SEK)', 'Base (SEK)', 'Pessimistic (SEK)'])
        years = proj.get('years') or []
        optimistic = proj.get('optimistic') or []
        base = proj.get('base') or []
        pessimistic = proj.get('pessimistic') or []
        for i, year in enumerate(years):
            writer.writerow([
                str(year),
                self._format_number(optimistic[i], decimals=0) if i < len(optimistic) else '',
                self._format_number(base[i], decimals=0) if i < len(base) else '',
                self._format_number(pessimistic[i], decimals=0) if i < len(pessimistic) else ''
            ])
        return output.getvalue()

    def generate_tax_comparison_csv(self, tax_comparison: List[Dict], current_account_type: str = None) -> str:
        """
        Generate tax_comparison.csv showing ISK/KF/AF comparison.

        Args:
            tax_comparison: List of tax calculations for different account types
            current_account_type: The currently selected account type

        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'Account Type',
            'Annual Tax (SEK)',
            'Effective Rate (%)',
            'After-Tax Return (%)',
            'Tax-Free Level (SEK)',
            'Tax Base (Capital) (SEK)',
            'Current Selection'
        ])

        # Find lowest tax
        lowest_tax = min(tc.get('annualTax', float('inf')) for tc in tax_comparison) if tax_comparison else None

        # Data rows
        for tc in tax_comparison:
            account_type = tc.get('accountType', '')
            annual_tax = tc.get('annualTax', 0)
            effective_rate = tc.get('effectiveRate', 0)
            after_tax_return = tc.get('afterTaxReturn', 0)
            tax_free_level = tc.get('taxFreeLevel', 0)
            capital_underlag = tc.get('capitalUnderlag', 0)

            is_current = account_type == current_account_type
            is_optimal = annual_tax == lowest_tax

            # Add markers
            account_label = account_type
            if is_current and is_optimal:
                account_label += " (Current & Optimal)"
            elif is_current:
                account_label += " (Current)"
            elif is_optimal:
                account_label += " (Optimal)"

            writer.writerow([
                account_label,
                self._format_number(float(annual_tax), decimals=2),
                self._format_number(float(effective_rate), decimals=2),
                self._format_number(float(after_tax_return), decimals=2),
                self._format_number(float(tax_free_level), decimals=0),
                self._format_number(float(capital_underlag), decimals=0),
                'Yes' if is_current else 'No'
            ])

        # Add summary row
        writer.writerow([])
        writer.writerow(['Summary', '', '', '', '', '', ''])
        if lowest_tax is not None:
            optimal_account = next((tc.get('accountType') for tc in tax_comparison if tc.get('annualTax') == lowest_tax), None)
            writer.writerow(['Optimal Account Type', optimal_account or '', '', '', '', '', ''])
            writer.writerow(['Lowest Annual Tax', self._format_number(float(lowest_tax), decimals=2), 'SEK', '', '', '', ''])

        return output.getvalue()

    def generate_recommendations_csv(self, recommendations: List[str]) -> str:
        """
        Generate recommendations.csv from smart recommendations.

        Args:
            recommendations: List of recommendation strings

        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['Priority', 'Category', 'Recommendation', 'Details'])

        # Parse and categorize recommendations
        for i, rec in enumerate(recommendations, 1):
            # Remove emojis
            rec_clean = rec.replace('💡', '').replace('💰', '').replace('✅', '').replace('🎉', '').strip()

            # Determine category from content
            category = 'General'
            if 'Tax Year' in rec_clean or 'tax year' in rec_clean or '2026' in rec_clean:
                category = 'Tax Year Optimization'
            elif 'Account Type' in rec_clean or 'Switching from' in rec_clean:
                category = 'Account Type Optimization'
            elif 'Optimal Configuration' in rec_clean or 'optimal' in rec_clean.lower():
                category = 'Validation'
            elif 'Courtage' in rec_clean or 'courtage' in rec_clean:
                category = 'Cost Optimization'

            # Extract savings if present
            details = ''
            if 'SEK' in rec_clean:
                # Try to extract savings amount
                import re
                sek_matches = re.findall(r'([\d,]+)\s+SEK', rec_clean)
                if sek_matches:
                    details = f"Potential savings: {sek_matches[0]} SEK"

            writer.writerow([
                str(i),
                category,
                rec_clean,
                details
            ])

        return output.getvalue()

    def generate_educational_summary_csv(self, educational_summary: Dict) -> str:
        """
        Generate educational_summary.csv with account and tax settings information.

        Args:
            educational_summary: Dictionary with account type, tax year, and courtage info

        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['Setting', 'Value', 'Details'])

        # Account Type
        selected_account = educational_summary.get('selectedAccountType', 'N/A')
        writer.writerow(['Selected Account Type', selected_account, ''])

        # Tax Year Information
        tax_year_info = educational_summary.get('taxYearInfo', {})
        if tax_year_info:
            writer.writerow(['', '', ''])
            writer.writerow(['Tax Year Settings', '', ''])
            writer.writerow(['Year', str(tax_year_info.get('year', '')), ''])
            writer.writerow(['Tax-Free Level', self._format_number(tax_year_info.get('taxFreeLevel', 0), decimals=0), 'SEK'])
            writer.writerow(['Schablonränta', self._format_number(tax_year_info.get('schablonranta', 0), decimals=2), '%'])

        # Courtage Information
        courtage_info = educational_summary.get('courtageInfo', {})
        if courtage_info:
            writer.writerow(['', '', ''])
            writer.writerow(['Transaction Costs', '', ''])
            writer.writerow(['Courtage Class', str(courtage_info.get('class', '')), ''])
            writer.writerow(['Setup Cost', self._format_number(courtage_info.get('setupCost', 0), decimals=2), 'SEK'])
            writer.writerow(['Annual Rebalancing', self._format_number(courtage_info.get('annualRebalancing', 0), decimals=2), 'SEK'])
            writer.writerow(['Total First Year', self._format_number(courtage_info.get('totalFirstYear', 0), decimals=2), 'SEK'])

        return output.getvalue()

    def generate_executive_summary_csv(
        self,
        portfolio_value: float,
        account_type: str,
        tax_year: int,
        metrics: Optional[Dict] = None,
        portfolio_name: Optional[str] = None,
    ) -> str:
        """
        Generate executive_summary.csv (same high-level info as PDF Section 1).

        Args:
            portfolio_value: Total portfolio value (SEK)
            account_type: ISK, KF, or AF
            tax_year: Tax year
            metrics: Optional dict with expectedReturn, risk, sharpeRatio, diversificationScore
            portfolio_name: Optional report title

        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(['Executive Summary', '', ''])
        if portfolio_name:
            writer.writerow(['Portfolio Name', portfolio_name, ''])
        writer.writerow(['Portfolio Value (SEK)', self._format_number(float(portfolio_value), decimals=0), ''])
        writer.writerow(['Account Type', account_type or 'N/A', ''])
        writer.writerow(['Tax Year', str(tax_year), ''])
        writer.writerow(['', '', ''])

        if metrics:
            exp_ret = self._get(metrics, 'expectedReturn', 'expected_return')
            if exp_ret is not None:
                pct = self._pct_for_csv(exp_ret) or exp_ret * 100
                writer.writerow(['Expected Return', self._format_number(float(pct), decimals=2), '%'])
            risk = self._get(metrics, 'risk', 'risk')
            if risk is not None:
                pct = self._pct_for_csv(risk) or risk * 100
                writer.writerow(['Risk (Volatility)', self._format_number(float(pct), decimals=2), '%'])
            sharpe = self._get(metrics, 'sharpeRatio', 'sharpe_ratio')
            if sharpe is not None:
                writer.writerow(['Sharpe Ratio', self._format_number(float(sharpe), decimals=3), ''])
            div_score = self._get(metrics, 'diversificationScore', 'diversification_score')
            if div_score is not None:
                writer.writerow(['Diversification Score', self._format_number(float(div_score), decimals=2), ''])

        return output.getvalue()

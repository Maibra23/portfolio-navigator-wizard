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

    def generate_tax_analysis_csv(self, tax_data: Dict, tax_free_data: Optional[Dict] = None) -> str:
        """
        Generate tax_analysis.csv (same content as PDF Section 4 + 4b Tax-Free Breakdown).
        Accepts both snake_case and camelCase keys.
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
        
        # 4b. Tax-Free Breakdown (same as PDF)
        if tax_free_data:
            writer.writerow(['', '', ''])
            writer.writerow(['Tax-Free Breakdown (4b)', '', ''])
            tax_free_level = self._get(tax_free_data, 'tax_free_level', 'taxFreeLevel')
            tax_free_amt = self._get(tax_free_data, 'tax_free_amount', 'taxFreeAmount')
            taxable_amt = self._get(tax_free_data, 'taxable_amount', 'taxableAmount')
            tax_free_pct = self._get(tax_free_data, 'tax_free_percentage', 'taxFreePercentage')
            taxable_pct = self._get(tax_free_data, 'taxable_percentage', 'taxablePercentage')
            is_tax_free = self._get(tax_free_data, 'is_tax_free', 'isTaxFree')
            if tax_free_level is not None:
                writer.writerow(['Tax-Free Level (year)', self._format_number(float(tax_free_level)), ''])
            if tax_free_amt is not None:
                writer.writerow(['Tax-Free Amount', self._format_number(float(tax_free_amt)), self._format_number(float(tax_free_pct), decimals=2) + '%' if tax_free_pct is not None else ''])
            if taxable_amt is not None:
                writer.writerow(['Taxable Amount', self._format_number(float(taxable_amt)), self._format_number(float(taxable_pct), decimals=2) + '%' if taxable_pct is not None else ''])
            if is_tax_free is not None:
                writer.writerow(['Portfolio Below Tax-Free', 'Yes' if is_tax_free else 'No', ''])
        
        return output.getvalue()
    
    def generate_transaction_costs_csv(self, cost_data: Dict, portfolio_value: Optional[float] = None) -> str:
        """
        Generate transaction_costs.csv (same content as PDF: Component, Value, Impact %).
        Accepts both snake_case and camelCase keys. When portfolio_value is set, adds Impact column as in PDF.
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header: match PDF (Component, Value, Impact)
        writer.writerow(['Cost Component', 'Value (SEK)', 'Impact'])
        
        courtage_class = self._get(cost_data, 'courtage_class', 'courtageClass') or 'N/A'
        writer.writerow(['Courtage Class', str(courtage_class), 'Fee tier'])
        writer.writerow(['', '', ''])
        
        setup_cost = self._get(cost_data, 'setup_cost', 'setupCost')
        if setup_cost is not None:
            impact = ''
            if portfolio_value and float(portfolio_value) > 0:
                pct = float(setup_cost) / portfolio_value * 100
                impact = f'{pct:.2f}% (one-time)'
            writer.writerow(['Setup Cost', self._format_number(float(setup_cost)), impact])
        
        setup_breakdown = self._get(cost_data, 'setup_breakdown', 'setupBreakdown')
        if setup_breakdown is not None:
            writer.writerow(['', '', ''])
            writer.writerow(['Setup Breakdown', '', ''])
            writer.writerow(['Ticker', 'Shares', 'Value (SEK)', 'Courtage (SEK)'])
            for item in (setup_breakdown if isinstance(setup_breakdown, list) else []):
                writer.writerow([
                    item.get('ticker', ''),
                    item.get('shares', 0),
                    self._format_number(item.get('value', 0)),
                    self._format_number(item.get('courtage', 0))
                ])
        
        writer.writerow(['', '', ''])
        
        annual_rebal = self._get(cost_data, 'annual_rebalancing_cost', 'annualRebalancingCost')
        if annual_rebal is not None:
            impact = ''
            if portfolio_value and float(portfolio_value) > 0:
                pct = float(annual_rebal) / portfolio_value * 100
                impact = f'{pct:.2f}%/year'
            writer.writerow(['Annual Rebalancing Cost', self._format_number(float(annual_rebal)), impact])
        per_rebal = self._get(cost_data, 'per_rebalance_cost', 'perRebalanceCost')
        if per_rebal is not None:
            writer.writerow(['Per Rebalance Cost', self._format_number(float(per_rebal)), ''])
        rebal_freq = self._get(cost_data, 'rebalancing_frequency', 'rebalancingFrequency')
        if rebal_freq is not None:
            writer.writerow(['Rebalancing Frequency', str(rebal_freq), ''])
        total_first = self._get(cost_data, 'total_first_year_cost', 'totalFirstYearCost')
        if total_first is not None:
            impact = ''
            if portfolio_value and float(portfolio_value) > 0:
                pct = float(total_first) / portfolio_value * 100
                impact = f'{pct:.2f}% drag'
            writer.writerow(['Total First Year Cost', self._format_number(float(total_first)), impact])
        
        return output.getvalue()
    
    def _pct_for_csv(self, value) -> Optional[float]:
        """Normalize percentage: if in (0,1] treat as decimal and return * 100 for CSV display."""
        if value is None:
            return None
        v = float(value)
        if 0 < abs(v) <= 1 and v != 0:
            return v * 100
        return v

    def _risk_rating_diversification(self, score: float) -> str:
        """Same logic as PDF Risk Analysis section."""
        if score is None:
            return ''
        s = float(score)
        return "Excellent" if s >= 80 else "Good" if s >= 60 else "Moderate" if s >= 40 else "Low"

    def _risk_rating_sharpe(self, sharpe: float) -> str:
        """Same logic as PDF Risk Analysis section."""
        if sharpe is None:
            return ''
        s = float(sharpe)
        return "Excellent" if s >= 1.5 else "Good" if s >= 1.0 else "Fair" if s >= 0.5 else "Low"

    def _risk_rating_volatility(self, risk_val: Any) -> str:
        """Same logic as PDF Risk Analysis section (risk_pct)."""
        if risk_val is None:
            return ''
        v = float(risk_val)
        risk_pct = v * 100 if 0 < abs(v) <= 1 else v
        return "Low" if risk_pct < 10 else "Moderate" if risk_pct < 20 else "High" if risk_pct < 30 else "Very High"

    def generate_portfolio_metrics_csv(self, metrics: Dict) -> str:
        """
        Generate portfolio_metrics.csv (same content as PDF Risk Analysis section).
        Accepts both camelCase and snake_case. Includes Value and Rating columns to match PDF.
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header: Metric, Value, Rating (PDF section 9)
        writer.writerow(['Metric', 'Value', 'Rating'])
        
        # Diversification (value + rating)
        div_score = self._get(metrics, 'diversificationScore', 'diversification_score')
        if div_score is not None:
            writer.writerow([
                'Diversification',
                self._format_number(float(div_score), decimals=0),
                self._risk_rating_diversification(div_score),
            ])
        
        # Sharpe Ratio (value + rating)
        sharpe = self._get(metrics, 'sharpeRatio', 'sharpe_ratio')
        if sharpe is not None:
            writer.writerow([
                'Sharpe Ratio',
                self._format_number(float(sharpe), decimals=3),
                self._risk_rating_sharpe(sharpe),
            ])
        
        # Volatility (value + rating)
        risk_val = self._get(metrics, 'risk', 'risk')
        if risk_val is not None:
            pct = self._pct_for_csv(risk_val)
            disp = pct if pct is not None else risk_val
            writer.writerow([
                'Volatility (%)',
                self._format_number(disp, decimals=2),
                self._risk_rating_volatility(risk_val),
            ])
        
        # Expected Return
        exp_ret = self._get(metrics, 'expectedReturn', 'expected_return')
        if exp_ret is not None:
            pct = self._pct_for_csv(exp_ret)
            writer.writerow(['Expected Return (%)', self._format_number(pct if pct is not None else exp_ret, decimals=2), ''])
        
        # Other metrics (no rating in PDF)
        total_alloc = self._get(metrics, 'totalAllocation', 'total_allocation')
        if total_alloc is not None:
            writer.writerow(['Total Allocation (%)', self._format_number(float(total_alloc) * 100, decimals=2), ''])
        
        stock_count = self._get(metrics, 'stockCount', 'stock_count')
        if stock_count is not None:
            writer.writerow(['Stock Count', str(stock_count), ''])
        
        gross = self._get(metrics, 'grossExpectedReturn', 'gross_expected_return')
        if gross is not None:
            pct = self._pct_for_csv(gross)
            writer.writerow(['Gross Expected Return (%)', self._format_number(pct if pct is not None else gross, decimals=2), ''])
        
        tax_impact = self._get(metrics, 'annualTaxImpact', 'annual_tax_impact')
        if tax_impact is not None:
            writer.writerow(['Annual Tax Impact (SEK)', self._format_number(float(tax_impact)), ''])
        
        after_tax = self._get(metrics, 'afterTaxReturn', 'after_tax_return')
        if after_tax is not None:
            pct = self._pct_for_csv(after_tax)
            writer.writerow(['After-Tax Return (%)', self._format_number(pct if pct is not None else after_tax, decimals=2), ''])
        
        net_ret = self._get(metrics, 'netExpectedReturn', 'net_expected_return')
        if net_ret is not None:
            pct = self._pct_for_csv(net_ret)
            writer.writerow(['Net Expected Return (%)', self._format_number(pct if pct is not None else net_ret, decimals=2), ''])
        
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
        
        # Summary row (same as PDF: Resilience Score + label)
        resilience = stress_data.get('resilience_score')
        writer.writerow(['Resilience Score', self._format_number(resilience, decimals=0) if resilience is not None else '', ''])
        if resilience is not None:
            label = "Excellent" if resilience >= 80 else "Good" if resilience >= 60 else "Fair" if resilience >= 40 else "Weak"
            writer.writerow(['Resilience Label', label, ''])
        writer.writerow(['Overall Assessment', str(stress_data.get('overall_assessment', 'N/A')), ''])
        writer.writerow([])
        
        # Header: include Portfolio Impact (%) to match PDF Crisis Impact chart
        writer.writerow(['Scenario', 'Portfolio Impact (%)', 'Total Return (%)', 'Max Drawdown (%)', 'Recovery Months', 'Details'])
        
        scenarios = stress_data.get('scenarios') or stress_data.get('scenario_results') or {}
        if isinstance(scenarios, dict):
            for scenario_name, scenario_obj in scenarios.items():
                obj = scenario_obj or {}
                impact = obj.get('portfolio_impact') or obj.get('impact')
                impact_pct = (float(impact) * 100) if impact is not None else ''
                metrics = obj.get('metrics', {})
                total_return = (metrics.get('total_return') or 0) * 100
                max_dd = (metrics.get('max_drawdown') or 0) * 100
                recovery = metrics.get('recovery_months') or metrics.get('trajectory_projections', {}).get('moderate_months') or ''
                recovery_str = f"{recovery}" if recovery != '' else 'N/A'
                writer.writerow([
                    scenario_name,
                    self._format_number(impact_pct, decimals=2) if impact_pct != '' else '',
                    self._format_number(total_return, decimals=2),
                    self._format_number(max_dd, decimals=2),
                    recovery_str,
                    obj.get('period', {}).get('start', '') or ''
                ])
        else:
            for scenario in (scenarios or []):
                scenario_name = scenario.get('name', 'Unknown')
                impact = scenario.get('portfolio_impact') or scenario.get('impact')
                impact_pct = (float(impact) * 100) if impact is not None else ''
                return_pct = scenario.get('return', 0.0)
                details = scenario.get('details', '')
                writer.writerow([
                    scenario_name,
                    self._format_number(impact_pct, decimals=2) if impact_pct != '' else '',
                    self._format_number(return_pct, decimals=2),
                    '',
                    '',
                    details,
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
        """Generate monte_carlo_summary.csv from optimizationResults.comparison.monte_carlo (same content as PDF/UI).
        Backend returns percentiles as p5, p50, p95 under mc['percentiles']; also supports percentile_5/50/95."""
        output = StringIO()
        writer = csv.writer(output)
        # Header: match PDF/UI labels (5th = worst 5%, 50th = median, 95th = best case)
        writer.writerow([
            'Portfolio',
            '5th Percentile (Worst 5%) (%)',
            '25th Percentile (%)',
            'Median (50th Percentile) (%)',
            '75th Percentile (%)',
            '95th Percentile (Best Case) (%)',
            'Probability Positive Return (%)',
            'Prob. Loss >10% (%)',
            'Prob. Loss >20% (%)',
            'Simulations',
            'Time Horizon (Years)',
            'Expected Return (Input) (%)',
            'Volatility (Input) (%)',
        ])
        comparison = opt_results.get('comparison') or {}
        monte_carlo = comparison.get('monte_carlo') or {}
        for key, mc in monte_carlo.items():
            if mc and isinstance(mc, dict):
                percentiles = mc.get('percentiles') or {}
                # Backend uses p5, p50, p95; also support legacy percentile_5 etc.
                def _pct(val, default=None):
                    if val is not None:
                        v = float(val)
                        return self._format_number(v * 100 if -1 <= v <= 1 and v != 0 else v, decimals=2)
                    return default or ''
                p5 = percentiles.get('p5') if percentiles else (mc.get('percentile_5') or mc.get('percentile5'))
                p25 = percentiles.get('p25') if percentiles else None
                p50 = percentiles.get('p50') if percentiles else (mc.get('percentile_50') or mc.get('percentile50'))
                p75 = percentiles.get('p75') if percentiles else None
                p95 = percentiles.get('p95') if percentiles else (mc.get('percentile_95') or mc.get('percentile95'))
                prob_pos = mc.get('probability_positive')
                loss_thresh = mc.get('probability_loss_thresholds') or {}
                prob_10 = loss_thresh.get('loss_10pct')
                prob_20 = loss_thresh.get('loss_20pct')
                params = mc.get('parameters') or {}
                n_sim = params.get('num_simulations', '')
                horizon = params.get('time_horizon_years', '')
                exp_ret = params.get('expected_return')
                risk_in = params.get('risk')
                writer.writerow([
                    key.replace('_', ' ').title(),
                    _pct(p5, ''),
                    _pct(p25, ''),
                    _pct(p50, ''),
                    _pct(p75, ''),
                    _pct(p95, ''),
                    self._format_number(float(prob_pos), decimals=2) if prob_pos is not None else '',
                    self._format_number(float(prob_10), decimals=2) if prob_10 is not None else '',
                    self._format_number(float(prob_20), decimals=2) if prob_20 is not None else '',
                    str(n_sim) if n_sim != '' else '',
                    str(horizon) if horizon != '' else '',
                    _pct(exp_ret, ''),
                    _pct(risk_in, ''),
                ])
        return output.getvalue()

    def generate_five_year_projection_csv(self, proj: Dict) -> str:
        """Generate five_year_projection.csv (same content as PDF 5-Year Projection section: table + growth summary)."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Year', 'Optimistic (SEK)', 'Base Case (SEK)', 'Pessimistic (SEK)'])
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
        # Growth summary (same as PDF: "Base: +X% | Pessimistic: +Y% (5yr net)")
        initial = proj.get('initial_capital') or (base[0] if base else None)
        if initial and base and pessimistic and len(base) > 0 and len(pessimistic) > 0:
            writer.writerow([])
            writer.writerow(['Summary (5-year net growth)', '', '', ''])
            final_base = base[-1]
            final_pess = pessimistic[-1]
            base_growth = ((final_base / initial) - 1) * 100 if initial else 0
            pess_growth = ((final_pess / initial) - 1) * 100 if initial else 0
            writer.writerow(['Initial Capital (SEK)', self._format_number(initial, decimals=0), '', ''])
            writer.writerow(['Final Base Case (SEK)', self._format_number(final_base, decimals=0), '', ''])
            writer.writerow(['Final Pessimistic (SEK)', self._format_number(final_pess, decimals=0), '', ''])
            writer.writerow(['Base Case Growth (%)', self._format_number(base_growth, decimals=2), '', ''])
            writer.writerow(['Pessimistic Growth (%)', self._format_number(pess_growth, decimals=2), '', ''])
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

    def generate_methodology_csv(
        self,
        account_type: str = None,
        tax_year: int = None,
        courtage_class: str = None,
    ) -> str:
        """
        Generate methodology.csv explaining data sources, calculations, and assumptions.
        This provides educational context for all other CSV files.

        Args:
            account_type: ISK, KF, or AF
            tax_year: Tax year used
            courtage_class: Courtage class used

        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['PORTFOLIO ANALYSIS - METHODOLOGY & ASSUMPTIONS'])
        writer.writerow([])
        writer.writerow(['This document explains how the analysis was performed and what assumptions were made.'])
        writer.writerow(['Use this information to interpret the data files correctly and understand their limitations.'])
        writer.writerow([])

        # Data Sources
        writer.writerow(['=== DATA SOURCES ==='])
        writer.writerow(['Category', 'Source', 'Notes'])
        writer.writerow(['Historical Prices', 'Market data providers', 'Typically 3-5 years of daily returns'])
        writer.writerow(['Expected Return', 'Weighted average of historical annualized returns', 'Based on your portfolio allocation'])
        writer.writerow(['Risk (Volatility)', 'Portfolio variance from correlation matrix', 'Accounts for diversification effects'])
        writer.writerow(['Tax Rates', 'Swedish Tax Agency (Skatteverket)', 'Official rates for ISK/KF/AF accounts'])
        writer.writerow(['Transaction Costs', 'Avanza fee schedules', 'Based on selected courtage class'])
        writer.writerow([])

        # Projection Methodology
        writer.writerow(['=== 5-YEAR PROJECTION METHODOLOGY ==='])
        writer.writerow(['Scenario', 'Calculation', 'Use Case'])
        writer.writerow(['Optimistic', 'Expected Return + Volatility', 'Upper bound - plan for upside potential'])
        writer.writerow(['Base Case', 'Expected Return', 'Most likely outcome - central planning figure'])
        writer.writerow(['Pessimistic', 'Expected Return - 50% of Volatility', 'Conservative - stress test your goals'])
        writer.writerow([])
        writer.writerow(['Note', 'Each year deducts annual tax and transaction costs then compounds net return'])
        writer.writerow([])

        # Tax Calculation
        writer.writerow(['=== TAX CALCULATION ==='])
        if account_type in ('ISK', 'KF'):
            writer.writerow(['Account Type', account_type, 'Schablonbeskattning (flat tax on capital)'])
            writer.writerow(['Mechanism', 'Tax on notional income regardless of actual gains', ''])
            tax_free = '150,000 SEK' if tax_year == 2025 else '300,000 SEK'
            schablon = '2.96%' if tax_year == 2025 else '3.55%'
            writer.writerow(['Tax-Free Level', tax_free, f'For {tax_year}'])
            writer.writerow(['Schablonranta', schablon, f'For {tax_year}'])
            writer.writerow(['Effective Rate', 'Approximately 0.89-1.07% of capital above free level', ''])
        elif account_type == 'AF':
            writer.writerow(['Account Type', 'AF (Aktie- och Fondkonto)', 'Capital gains tax'])
            writer.writerow(['Mechanism', '30% tax on realized gains only', 'Pay when you sell'])
            writer.writerow(['Dividends', '30% withheld automatically', ''])
            writer.writerow(['Note', 'Projections assume gains realized annually', 'Actual tax depends on trading activity'])
        else:
            writer.writerow(['Account Type', account_type or 'Not specified', ''])
        writer.writerow([])

        # Transaction Costs
        writer.writerow(['=== TRANSACTION COSTS ==='])
        if courtage_class:
            writer.writerow(['Courtage Class', courtage_class.capitalize(), 'Your selected fee tier'])
        writer.writerow(['Setup Cost', 'One-time cost to establish positions', 'Deducted in Year 1'])
        writer.writerow(['Annual Costs', 'Ongoing trading costs', 'Deducted each year from returns'])
        writer.writerow([])

        # Limitations
        writer.writerow(['=== IMPORTANT LIMITATIONS ==='])
        writer.writerow(['Limitation', 'Explanation', 'Impact'])
        writer.writerow(['Historical data not predictive', 'Past returns do not guarantee future performance', 'Actual results may differ significantly'])
        writer.writerow(['Static Assumptions', 'Projections assume current holdings maintained', 'Trading activity will change outcomes'])
        writer.writerow(['Tax Law Changes', 'Swedish tax rules may change', 'Future rates could differ'])
        writer.writerow(['Correlation Stability', 'Asset correlations assumed constant', 'Diversification benefits may vary'])
        writer.writerow(['Estimation Only', 'All figures are estimates for educational purposes', 'Not financial advice'])
        writer.writerow([])

        writer.writerow(['=== DISCLAIMER ==='])
        writer.writerow(['This analysis is for informational and educational purposes only.'])
        writer.writerow(['It does not constitute financial investment or tax advice.'])
        writer.writerow(['Please consult a qualified financial advisor before making investment decisions.'])

        return output.getvalue()

    def generate_glossary_csv(self) -> str:
        """
        Generate glossary.csv with metric definitions and interpretation guidance.
        Helps users understand what each value means and how to use it.

        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['GLOSSARY - METRIC DEFINITIONS & INTERPRETATION'])
        writer.writerow([])
        writer.writerow(['This glossary explains the metrics used throughout the analysis files.'])
        writer.writerow([])

        # Portfolio Metrics
        writer.writerow(['=== PORTFOLIO METRICS ==='])
        writer.writerow(['Metric', 'Definition', 'Good/Bad', 'Decision Guidance'])
        writer.writerow([
            'Expected Return',
            'Annualized average return based on historical data',
            'Higher is better (but consider risk)',
            'Compare to your required return rate'
        ])
        writer.writerow([
            'Risk (Volatility)',
            'Standard deviation of returns - how much values fluctuate',
            '<15% low | 15-25% moderate | >25% high',
            'Match to your risk tolerance; high volatility = larger swings'
        ])
        writer.writerow([
            'Sharpe Ratio',
            'Return per unit of risk (excess return / volatility)',
            '<0.5 poor | 0.5-1.0 fair | >1.0 good | >1.5 excellent',
            'Higher = more efficient risk-taking'
        ])
        writer.writerow([
            'Diversification Score',
            'How well risk is spread across uncorrelated assets (0-100)',
            '<40 poor | 40-60 fair | 60-80 good | >80 excellent',
            'Low scores indicate concentration risk'
        ])
        writer.writerow([])

        # Tax Metrics
        writer.writerow(['=== TAX METRICS ==='])
        writer.writerow(['Metric', 'Definition', 'Good/Bad', 'Decision Guidance'])
        writer.writerow([
            'Annual Tax',
            'Estimated yearly tax burden in SEK',
            'Lower is better',
            'Compare across account types to optimize'
        ])
        writer.writerow([
            'Effective Tax Rate',
            'Tax as percentage of portfolio value',
            'Lower is better',
            'ISK/KF typically 0-1.1%; AF varies with gains'
        ])
        writer.writerow([
            'Tax-Free Level',
            'Capital amount exempt from ISK/KF tax',
            'N/A',
            'Below this = zero tax; above = taxed on excess'
        ])
        writer.writerow([
            'After-Tax Return',
            'Expected return minus tax impact',
            'Higher is better',
            'True measure of what you keep'
        ])
        writer.writerow([])

        # Cost Metrics
        writer.writerow(['=== COST METRICS ==='])
        writer.writerow(['Metric', 'Definition', 'Good/Bad', 'Decision Guidance'])
        writer.writerow([
            'Setup Cost',
            'One-time trading cost to establish positions',
            '<0.5% of capital is reasonable',
            'Higher costs reduce initial capital'
        ])
        writer.writerow([
            'Annual Costs',
            'Ongoing trading/management costs per year',
            '<0.5% per year is reasonable',
            'Compounds over time; minimize where possible'
        ])
        writer.writerow([
            'Courtage Class',
            'Fee tier determining transaction costs',
            'N/A - depends on trading volume',
            'Higher classes = lower per-trade cost but may have minimums'
        ])
        writer.writerow([])

        # Projection Metrics
        writer.writerow(['=== PROJECTION SCENARIOS ==='])
        writer.writerow(['Scenario', 'What It Means', 'Probability', 'How To Use'])
        writer.writerow([
            'Optimistic',
            'Upper bound if markets outperform',
            'Roughly 15-20% chance',
            'Plan for upside potential; do not count on it'
        ])
        writer.writerow([
            'Base Case',
            'Most likely outcome based on history',
            'Roughly 50-60% chance',
            'Use for central financial planning'
        ])
        writer.writerow([
            'Pessimistic',
            'Conservative estimate for downside',
            'Roughly 15-20% chance',
            'Stress test goals; ensure you can handle this'
        ])
        writer.writerow([])

        # Optimization Metrics
        writer.writerow(['=== OPTIMIZATION TERMS ==='])
        writer.writerow(['Term', 'Definition', 'Relevance'])
        writer.writerow([
            'Efficient Frontier',
            'Curve showing optimal risk-return combinations',
            'Portfolios below it are suboptimal'
        ])
        writer.writerow([
            'Weights-Optimized',
            'Rebalanced using same stocks with different weights',
            'Improve without changing holdings'
        ])
        writer.writerow([
            'Market-Optimized',
            'May include new stocks for better diversification',
            'Maximum improvement; requires new positions'
        ])
        writer.writerow([])

        # Stress Test Terms
        writer.writerow(['=== STRESS TEST TERMS ==='])
        writer.writerow(['Term', 'Definition', 'Interpretation'])
        writer.writerow([
            'Resilience Score',
            'Overall portfolio robustness to market stress (0-100)',
            '>80 excellent | 60-80 good | 40-60 fair | <40 vulnerable'
        ])
        writer.writerow([
            'Scenario Impact',
            'Estimated portfolio change during historical crisis',
            'Negative = loss; compare magnitude to your tolerance'
        ])

        return output.getvalue()

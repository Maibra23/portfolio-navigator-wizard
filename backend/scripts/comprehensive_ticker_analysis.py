#!/usr/bin/env python3
"""
Comprehensive Ticker Analysis Script
Analyzes Redis ticker data for:
1. 15-year data coverage
2. Exchange filtering (exclude unknown)
3. Ticker counts per risk profile
4. Portfolio generation feasibility
"""

import sys
import os
import json
import redis
import gzip
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple
from datetime import datetime
import pandas as pd
from itertools import combinations

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

RISK_PROFILES = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']

# Requirements from the system
RISK_PROFILE_VOLATILITY = {
    'very-conservative': (0.05, 0.18),
    'conservative': (0.15, 0.25),
    'moderate': (0.22, 0.32),
    'aggressive': (0.28, 0.45),
    'very-aggressive': (0.38, 1.00)
}

RETURN_TARGET_RANGES = {
    'very-conservative': (0.04, 0.14),
    'conservative': (0.12, 0.22),
    'moderate': (0.18, 0.32),
    'aggressive': (0.26, 0.52),
    'very-aggressive': (0.48, 1.70)
}

STOCK_COUNT_RANGES = {
    'very-conservative': (3, 5),
    'conservative': (3, 5),
    'moderate': (3, 5),
    'aggressive': (3, 4),
    'very-aggressive': (3, 4)
}

# 15 years = 180 months minimum
MIN_MONTHS_REQUIRED = 180


def connect_redis():
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
        r.ping()
        return r
    except Exception as e:
        print(f"❌ Redis connection failed: {e}", file=sys.stderr)
        return None


def load_ticker_comprehensive(redis_client, ticker: str) -> Dict:
    """Load comprehensive ticker data including exchange, data coverage, metrics"""
    try:
        data = {
            'symbol': ticker,
            'volatility': 0.0,
            'return': 0.0,
            'sector': 'Unknown',
            'exchange': 'Unknown',
            'data_months': 0,
            'has_data': False,
            'meets_15_year_requirement': False
        }
        
        # Get exchange from info
        info_key = f"ticker_data:info:{ticker}"
        info_data = redis_client.get(info_key)
        if info_data:
            try:
                if isinstance(info_data, bytes):
                    try:
                        info_dict = json.loads(gzip.decompress(info_data).decode('utf-8'))
                    except:
                        info_dict = json.loads(info_data.decode('utf-8'))
                else:
                    info_dict = json.loads(info_data)
                data['exchange'] = info_dict.get('exchange', info_dict.get('exchangeCode', 'Unknown'))
            except:
                pass
        
        # Get prices to check data coverage
        prices_key = f"ticker_data:prices:{ticker}"
        prices_data = redis_client.get(prices_key)
        
        if prices_data:
            try:
                if isinstance(prices_data, bytes):
                    try:
                        prices_dict = json.loads(gzip.decompress(prices_data).decode('utf-8'))
                    except:
                        prices_dict = json.loads(prices_data.decode('utf-8'))
                else:
                    prices_dict = json.loads(prices_data)
                
                if isinstance(prices_dict, dict):
                    data['data_months'] = len(prices_dict)
                    data['meets_15_year_requirement'] = data['data_months'] >= MIN_MONTHS_REQUIRED
                    
                    # Calculate volatility and return from prices if we have enough data
                    if len(prices_dict) > 1:
                        prices_series = pd.Series(list(prices_dict.values()))
                        prices_series = prices_series.sort_index() if isinstance(prices_dict, dict) else prices_series
                        
                        price_changes = prices_series.pct_change().dropna()
                        if len(price_changes) > 0:
                            data['volatility'] = price_changes.std() * (252 ** 0.5)  # Annualized
                            
                            # Calculate return (annualized)
                            if len(prices_series) >= 12:
                                data['return'] = ((prices_series.iloc[-1] / prices_series.iloc[0]) ** (12 / len(prices_series))) - 1
                            else:
                                data['return'] = (prices_series.iloc[-1] / prices_series.iloc[0]) - 1
                            
                            data['has_data'] = True
            except Exception as e:
                pass
        
        # Try to get from metrics (override if available)
        metrics_key = f"ticker_data:metrics:{ticker}"
        metrics_data = redis_client.get(metrics_key)
        
        if metrics_data:
            try:
                if isinstance(metrics_data, bytes):
                    try:
                        metrics = json.loads(gzip.decompress(metrics_data).decode('utf-8'))
                    except:
                        metrics = json.loads(metrics_data.decode('utf-8'))
                else:
                    metrics = json.loads(metrics_data)
                
                # Use metrics if available (more accurate)
                if metrics.get('risk') or metrics.get('volatility'):
                    data['volatility'] = metrics.get('risk', metrics.get('volatility', metrics.get('annualized_volatility', data['volatility'])))
                    data['return'] = metrics.get('annualized_return', metrics.get('return', data['return']))
                    data['has_data'] = True
            except:
                pass
        
        # Get sector
        sector_key = f"ticker_data:sector:{ticker}"
        sector_data = redis_client.get(sector_key)
        
        if sector_data:
            try:
                if isinstance(sector_data, bytes):
                    try:
                        sector_dict = json.loads(gzip.decompress(sector_data).decode('utf-8'))
                    except:
                        sector_dict = json.loads(sector_data.decode('utf-8'))
                else:
                    sector_dict = json.loads(sector_data)
                
                data['sector'] = sector_dict.get('sector', 'Unknown')
            except:
                pass
        
        return data if data['has_data'] else None
        
    except Exception as e:
        return None


def get_all_tickers(redis_client) -> List[str]:
    """Get all tickers from Redis"""
    tickers = set()
    
    patterns = ["ticker_data:info:*", "ticker_data:metrics:*", "ticker_data:prices:*", "ticker_data:sector:*"]
    
    for pattern in patterns:
        for key in redis_client.scan_iter(match=pattern):
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            parts = key_str.split(':')
            if len(parts) >= 3:
                ticker = parts[2]
                tickers.add(ticker)
    
    return sorted(list(tickers))


def analyze_ticker_coverage(redis_client, all_tickers: List[str]) -> Dict:
    """Analyze ticker data coverage and exchange distribution"""
    coverage_stats = {
        'total_tickers': len(all_tickers),
        'tickers_with_data': 0,
        'tickers_15_years': 0,
        'tickers_with_exchange': 0,
        'tickers_valid_exchange': 0,
        'exchange_distribution': Counter(),
        'data_coverage_distribution': Counter(),
        'tickers_by_exchange': defaultdict(list)
    }
    
    for ticker in all_tickers:
        ticker_data = load_ticker_comprehensive(redis_client, ticker)
        
        if not ticker_data or not ticker_data['has_data']:
            continue
        
        coverage_stats['tickers_with_data'] += 1
        
        # Check 15-year requirement
        if ticker_data['meets_15_year_requirement']:
            coverage_stats['tickers_15_years'] += 1
        
        # Exchange analysis
        exchange = ticker_data['exchange']
        if exchange and exchange != 'Unknown':
            coverage_stats['tickers_with_exchange'] += 1
            coverage_stats['tickers_valid_exchange'] += 1
            coverage_stats['exchange_distribution'][exchange] += 1
            coverage_stats['tickers_by_exchange'][exchange].append(ticker_data)
        else:
            coverage_stats['exchange_distribution']['Unknown'] += 1
        
        # Data coverage distribution
        months = ticker_data['data_months']
        years = months / 12 if months > 0 else 0
        year_bucket = f"{int(years)}-{int(years)+1} years" if years < 15 else "15+ years"
        coverage_stats['data_coverage_distribution'][year_bucket] += 1
    
    return coverage_stats


def analyze_risk_profile_feasibility(redis_client, all_tickers: List[str], exclude_unknown_exchange: bool = False) -> Dict:
    """Analyze how many tickers meet requirements for each risk profile"""
    
    # First, load all ticker data (only once)
    valid_tickers = []
    for ticker in all_tickers:
        ticker_data = load_ticker_comprehensive(redis_client, ticker)
        
        if not ticker_data or not ticker_data['has_data']:
            continue
        
        # Filter by exchange if required (but exchange data may not be available)
        if exclude_unknown_exchange and ticker_data['exchange'] == 'Unknown':
            continue
        
        # Filter by 15-year requirement
        if not ticker_data['meets_15_year_requirement']:
            continue
        
        valid_tickers.append(ticker_data)
    
    if exclude_unknown_exchange:
        print(f"✅ Loaded {len(valid_tickers)} valid tickers (with valid exchange and 15+ years data)")
    else:
        print(f"✅ Loaded {len(valid_tickers)} valid tickers (with 15+ years data)")
    
    # Analyze for each risk profile
    profile_analysis = {}
    
    for risk_profile in RISK_PROFILES:
        volatility_range = RISK_PROFILE_VOLATILITY.get(risk_profile, (0.0, 1.0))
        return_range = RETURN_TARGET_RANGES.get(risk_profile, (0.0, 1.0))
        stock_count_range = STOCK_COUNT_RANGES.get(risk_profile, (3, 5))
        
        # Filter tickers by volatility
        matching_tickers = [
            t for t in valid_tickers
            if volatility_range[0] <= t['volatility'] <= volatility_range[1]
        ]
        
        # Analyze return distribution
        return_values = [t['return'] for t in matching_tickers]
        
        in_return_range = [
            t for t in matching_tickers
            if return_range[0] <= t['return'] <= return_range[1]
        ]
        
        above_return_range = [
            t for t in matching_tickers
            if t['return'] > return_range[1]
        ]
        
        below_return_range = [
            t for t in matching_tickers
            if t['return'] < return_range[0]
        ]
        
        # Calculate possible portfolio combinations
        min_stocks = stock_count_range[0]
        max_stocks = stock_count_range[1]
        
        # Use tickers in return range for portfolio generation
        usable_tickers = in_return_range if len(in_return_range) >= min_stocks else matching_tickers
        
        possible_portfolios_min = 0
        possible_portfolios_max = 0
        
        if len(usable_tickers) >= min_stocks:
            # Calculate combinations
            try:
                # Minimum portfolios (using min_stocks)
                if len(usable_tickers) >= min_stocks:
                    from math import comb
                    possible_portfolios_min = comb(len(usable_tickers), min_stocks)
                else:
                    possible_portfolios_min = 0
                
                # Maximum portfolios (using max_stocks)
                if len(usable_tickers) >= max_stocks:
                    possible_portfolios_max = comb(len(usable_tickers), max_stocks)
                else:
                    possible_portfolios_max = 0
            except:
                # Fallback for large numbers
                possible_portfolios_min = float('inf') if len(usable_tickers) >= min_stocks else 0
                possible_portfolios_max = float('inf') if len(usable_tickers) >= max_stocks else 0
        
        profile_analysis[risk_profile] = {
            'volatility_range': volatility_range,
            'return_range': return_range,
            'stock_count_range': stock_count_range,
            'total_matching_tickers': len(matching_tickers),
            'tickers_in_return_range': len(in_return_range),
            'tickers_above_return_range': len(above_return_range),
            'tickers_below_return_range': len(below_return_range),
            'usable_tickers_count': len(usable_tickers),
            'return_stats': {
                'min': min(return_values) if return_values else 0,
                'max': max(return_values) if return_values else 0,
                'avg': sum(return_values) / len(return_values) if return_values else 0,
                'median': sorted(return_values)[len(return_values)//2] if return_values else 0
            },
            'possible_portfolios_min': possible_portfolios_min,
            'possible_portfolios_max': possible_portfolios_max,
            'sample_tickers': matching_tickers[:10]
        }
    
    return profile_analysis


def generate_comprehensive_report(coverage_stats: Dict, profile_analysis: Dict) -> str:
    """Generate comprehensive analysis report"""
    lines = []
    lines.append("# Comprehensive Ticker Data Analysis Report")
    lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("\n---\n")
    
    # Data Coverage Analysis
    lines.append("## 1. Data Coverage Analysis\n")
    lines.append(f"- **Total Tickers Found:** {coverage_stats['total_tickers']}")
    lines.append(f"- **Tickers With Data:** {coverage_stats['tickers_with_data']}")
    lines.append(f"- **Tickers With 15+ Years Data:** {coverage_stats['tickers_15_years']} ({coverage_stats['tickers_15_years']/max(1, coverage_stats['tickers_with_data'])*100:.1f}%)")
    lines.append(f"- **Tickers With Valid Exchange (Not Unknown):** {coverage_stats['tickers_valid_exchange']} ({coverage_stats['tickers_valid_exchange']/max(1, coverage_stats['tickers_with_data'])*100:.1f}%)")
    
    lines.append("\n### Exchange Distribution\n")
    lines.append("| Exchange | Count | Percentage |")
    lines.append("|----------|-------|------------|")
    for exchange, count in coverage_stats['exchange_distribution'].most_common():
        pct = count / max(1, coverage_stats['tickers_with_data']) * 100
        lines.append(f"| {exchange} | {count} | {pct:.1f}% |")
    
    lines.append("\n### Data Coverage Distribution\n")
    lines.append("| Coverage | Count |")
    lines.append("|----------|-------|")
    for coverage, count in sorted(coverage_stats['data_coverage_distribution'].items()):
        lines.append(f"| {coverage} | {count} |")
    
    lines.append("\n---\n")
    
    # Risk Profile Feasibility Analysis
    lines.append("## 2. Risk Profile Feasibility Analysis\n")
    lines.append("**Note:** Analysis requires 15+ years data. Exchange data is not available in Redis, so all tickers are included.\n")
    
    for risk_profile in RISK_PROFILES:
        if risk_profile not in profile_analysis:
            continue
        
        analysis = profile_analysis[risk_profile]
        
        lines.append(f"### {risk_profile.replace('-', ' ').title()} Profile\n")
        
        lines.append(f"**Requirements:**")
        lines.append(f"- Volatility: {analysis['volatility_range'][0]:.1%} - {analysis['volatility_range'][1]:.1%}")
        lines.append(f"- Return: {analysis['return_range'][0]:.1%} - {analysis['return_range'][1]:.1%}")
        lines.append(f"- Stock Count: {analysis['stock_count_range'][0]}-{analysis['stock_count_range'][1]}")
        
        lines.append(f"\n**Ticker Pool:**")
        lines.append(f"- Total Matching (volatility): {analysis['total_matching_tickers']}")
        lines.append(f"- In Return Range: {analysis['tickers_in_return_range']}")
        lines.append(f"- Above Return Range: {analysis['tickers_above_return_range']}")
        lines.append(f"- Below Return Range: {analysis['tickers_below_return_range']}")
        lines.append(f"- Usable Tickers: {analysis['usable_tickers_count']}")
        
        stats = analysis['return_stats']
        lines.append(f"\n**Return Statistics (of volatility-matched tickers):**")
        lines.append(f"- Min: {stats['min']:.2%}")
        lines.append(f"- Max: {stats['max']:.2%}")
        lines.append(f"- Avg: {stats['avg']:.2%}")
        lines.append(f"- Median: {stats['median']:.2%}")
        
        lines.append(f"\n**Portfolio Generation Feasibility:**")
        min_stocks = analysis['stock_count_range'][0]
        max_stocks = analysis['stock_count_range'][1]
        
        if analysis['possible_portfolios_min'] == 0:
            lines.append(f"- ❌ **INSUFFICIENT:** Cannot generate portfolios (need {min_stocks} stocks, have {analysis['usable_tickers_count']})")
        else:
            if analysis['possible_portfolios_min'] == float('inf'):
                lines.append(f"- ✅ Possible portfolios (min {min_stocks} stocks): **UNLIMITED** (>{analysis['usable_tickers_count']} combinations)")
            else:
                lines.append(f"- ✅ Possible portfolios (min {min_stocks} stocks): {analysis['possible_portfolios_min']:,}")
            
            if analysis['possible_portfolios_max'] == float('inf'):
                lines.append(f"- ✅ Possible portfolios (max {max_stocks} stocks): **UNLIMITED** (>{analysis['usable_tickers_count']} combinations)")
            else:
                lines.append(f"- ✅ Possible portfolios (max {max_stocks} stocks): {analysis['possible_portfolios_max']:,}")
        
        # Feasibility assessment
        lines.append(f"\n**Feasibility Assessment:**")
        if analysis['usable_tickers_count'] < min_stocks:
            lines.append(f"❌ **NOT FEASIBLE:** Insufficient tickers ({analysis['usable_tickers_count']} < {min_stocks} required)")
        elif analysis['tickers_in_return_range'] < 12:
            lines.append(f"⚠️  **LIMITED:** Only {analysis['tickers_in_return_range']} tickers in return range (need at least 12 for 12 portfolios)")
            if analysis['return_stats']['avg'] < analysis['return_range'][0]:
                lines.append(f"   → Ticker pool average return ({stats['avg']:.2%}) is BELOW minimum required ({analysis['return_range'][0]:.2%})")
        else:
            lines.append(f"✅ **FEASIBLE:** Sufficient tickers ({analysis['usable_tickers_count']}) and return range coverage ({analysis['tickers_in_return_range']})")
        
        lines.append("\n---\n")
    
    # Root Cause Re-Evaluation
    lines.append("## 3. Root Cause Re-Evaluation\n")
    
    # Check systematic issues
    all_feasible = True
    all_insufficient_returns = True
    
    for risk_profile in RISK_PROFILES:
        if risk_profile not in profile_analysis:
            continue
        
        analysis = profile_analysis[risk_profile]
        
        if analysis['usable_tickers_count'] < analysis['stock_count_range'][0]:
            all_feasible = False
        
        if analysis['return_stats']['avg'] >= analysis['return_range'][0]:
            all_insufficient_returns = False
    
    lines.append("### Key Findings:\n")
    
    if not all_feasible:
        lines.append("❌ **ISSUE:** Some risk profiles have insufficient tickers after filtering (15 years + valid exchange)")
    
    if all_insufficient_returns:
        lines.append("❌ **CRITICAL ISSUE:** All risk profiles have ticker pool average returns BELOW minimum requirements")
        lines.append("   → Return target ranges are set too high for available ticker data")
        lines.append("   → System cannot generate portfolios meeting return requirements")
    
    # Check return range violations
    lines.append("\n### Return Range Analysis:\n")
    lines.append("| Risk Profile | Pool Avg Return | Required Min | Gap | Status |")
    lines.append("|-------------|-----------------|--------------|-----|--------|")
    
    for risk_profile in RISK_PROFILES:
        if risk_profile not in profile_analysis:
            continue
        
        analysis = profile_analysis[risk_profile]
        stats = analysis['return_stats']
        required_min = analysis['return_range'][0]
        gap = stats['avg'] - required_min
        
        if gap >= 0:
            status = "✅ OK"
        elif gap >= -0.01:  # Within 1%
            status = "⚠️  CLOSE"
        else:
            status = "❌ BELOW"
        
        lines.append(f"| {risk_profile} | {stats['avg']:.2%} | {required_min:.2%} | {gap:+.2%} | {status} |")
    
    lines.append("\n---\n")
    
    # Conclusions
    lines.append("## 4. Conclusions\n")
    
    total_usable = sum(pa['usable_tickers_count'] for pa in profile_analysis.values())
    total_needed = sum(pa['stock_count_range'][0] * 12 for pa in profile_analysis.values())  # 12 portfolios per profile
    
    lines.append(f"- **Total Usable Tickers (across all profiles):** {total_usable}")
    lines.append(f"- **Minimum Tickers Needed (60 portfolios):** {total_needed}")
    
    if total_usable >= total_needed:
        lines.append(f"✅ **Overall:** Sufficient ticker pool for portfolio generation")
    else:
        lines.append(f"❌ **Overall:** Insufficient ticker pool (need {total_needed}, have {total_usable})")
    
    return '\n'.join(lines)


def main():
    print("🔍 Comprehensive Ticker Data Analysis")
    print("=" * 80)
    
    redis_client = connect_redis()
    if not redis_client:
        return 1
    
    # Get all tickers
    print("\nLoading all tickers from Redis...")
    all_tickers = get_all_tickers(redis_client)
    print(f"✅ Found {len(all_tickers)} unique tickers")
    
    # Analyze data coverage
    print("\nAnalyzing data coverage and exchange distribution...")
    coverage_stats = analyze_ticker_coverage(redis_client, all_tickers)
    print(f"  Tickers with data: {coverage_stats['tickers_with_data']}")
    print(f"  Tickers with 15+ years: {coverage_stats['tickers_15_years']}")
    print(f"  Tickers with valid exchange: {coverage_stats['tickers_valid_exchange']}")
    
    # Analyze risk profile feasibility
    print("\nAnalyzing risk profile feasibility (requiring 15+ years data, exchange data not available)...")
    profile_analysis = analyze_risk_profile_feasibility(redis_client, all_tickers, exclude_unknown_exchange=False)
    
    for profile in RISK_PROFILES:
        if profile in profile_analysis:
            analysis = profile_analysis[profile]
            print(f"  {profile}:")
            print(f"    Matching tickers: {analysis['total_matching_tickers']}")
            print(f"    In return range: {analysis['tickers_in_return_range']}")
            print(f"    Usable tickers: {analysis['usable_tickers_count']}")
    
    # Generate report
    print("\nGenerating comprehensive report...")
    report = generate_comprehensive_report(coverage_stats, profile_analysis)
    
    # Save report
    output_file = os.path.join(os.path.dirname(__file__), '..', 'comprehensive_ticker_analysis.md')
    with open(output_file, 'w') as f:
        f.write(report)
    
    print(f"\n✅ Analysis complete!")
    print(f"📄 Report saved to: {output_file}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

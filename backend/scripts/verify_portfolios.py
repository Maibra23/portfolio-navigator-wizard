#!/usr/bin/env python3
"""
Portfolio Verification Script
Analyzes portfolios in Redis to verify:
1. Portfolio uniqueness (ticker exclusion mechanism)
2. Risk profile constraints (volatility, stock count, return ranges)
"""

import sys
import os
import json
import redis
from collections import defaultdict, Counter
from typing import Dict, List, Set

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Risk profile constraints from the system
RISK_PROFILE_VOLATILITY = {
    'very-conservative': (0.05, 0.18),
    'conservative': (0.15, 0.25),
    'moderate': (0.22, 0.32),
    'aggressive': (0.28, 0.45),
    'very-aggressive': (0.38, 1.00)
}

STOCK_COUNT_RANGES = {
    'very-conservative': (3, 5),
    'conservative': (3, 5),
    'moderate': (3, 5),
    'aggressive': (3, 4),
    'very-aggressive': (3, 4)
}

RETURN_TARGET_RANGES = {
    'very-conservative': (0.04, 0.14),
    'conservative': (0.12, 0.22),
    'moderate': (0.18, 0.32),
    'aggressive': (0.26, 0.52),
    'very-aggressive': (0.48, 1.70)
}

DIVERSIFICATION_RANGES = {
    'very-conservative': (50.0, 100.0),
    'conservative': (50.0, 100.0),
    'moderate': (50.0, 100.0),
    'aggressive': (30.0, 100.0),
    'very-aggressive': (20.0, 100.0)
}

RISK_PROFILES = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']


def connect_redis():
    """Connect to Redis"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
        r.ping()
        print("✅ Redis connection established")
        return r
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return None


def load_portfolios_from_redis(redis_client, risk_profile: str) -> List[Dict]:
    """Load all portfolios for a risk profile from Redis"""
    portfolios = []
    bucket_prefix = f"portfolio_bucket:{risk_profile}"
    
    for i in range(12):
        key = f"{bucket_prefix}:{i}"
        try:
            data = redis_client.get(key)
            if data:
                if isinstance(data, bytes):
                    portfolio = json.loads(data.decode('utf-8'))
                else:
                    portfolio = json.loads(data)
                portfolio['variation_id'] = i
                portfolios.append(portfolio)
        except Exception as e:
            print(f"⚠️  Error loading portfolio {i} for {risk_profile}: {e}", file=sys.stderr)
    
    return portfolios


def check_uniqueness(portfolios: List[Dict]) -> Dict:
    """Check portfolio uniqueness"""
    results = {
        'total_portfolios': len(portfolios),
        'unique_tickers_per_portfolio': [],
        'ticker_overlap_matrix': {},
        'duplicate_tickers': [],
        'total_unique_tickers': set(),
        'overlap_percentage': {}
    }
    
    portfolio_tickers = []
    for i, portfolio in enumerate(portfolios):
        allocations = portfolio.get('allocations', [])
        tickers = {alloc.get('symbol') for alloc in allocations if alloc.get('symbol')}
        portfolio_tickers.append(tickers)
        results['unique_tickers_per_portfolio'].append({
            'portfolio_id': i,
            'ticker_count': len(tickers),
            'tickers': sorted(list(tickers))
        })
        results['total_unique_tickers'].update(tickers)
    
    for i in range(len(portfolios)):
        for j in range(i + 1, len(portfolios)):
            tickers_i = portfolio_tickers[i]
            tickers_j = portfolio_tickers[j]
            overlap = tickers_i & tickers_j
            overlap_key = f"{i}-{j}"
            results['ticker_overlap_matrix'][overlap_key] = {
                'overlap_count': len(overlap),
                'overlap_tickers': sorted(list(overlap)),
                'overlap_percentage': (len(overlap) / min(len(tickers_i), len(tickers_j)) * 100) if min(len(tickers_i), len(tickers_j)) > 0 else 0
            }
            
            if overlap:
                results['duplicate_tickers'].append({
                    'portfolios': [i, j],
                    'shared_tickers': sorted(list(overlap))
                })
    
    if len(portfolios) > 0:
        total_pairs = len(portfolios) * (len(portfolios) - 1) // 2
        pairs_with_overlap = len(results['duplicate_tickers'])
        results['overlap_percentage'] = {
            'pairs_with_overlap': pairs_with_overlap,
            'total_pairs': total_pairs,
            'overlap_rate': (pairs_with_overlap / total_pairs * 100) if total_pairs > 0 else 0
        }
    
    return results


def check_risk_profile_constraints(portfolios: List[Dict], risk_profile: str) -> Dict:
    """Check if portfolios meet risk profile constraints"""
    results = {
        'risk_profile': risk_profile,
        'total_portfolios': len(portfolios),
        'stock_count_violations': [],
        'return_range_violations': [],
        'diversification_violations': [],
        'portfolio_details': []
    }
    
    expected_stock_range = STOCK_COUNT_RANGES.get(risk_profile, (3, 5))
    expected_return_range = RETURN_TARGET_RANGES.get(risk_profile, (0.0, 1.0))
    expected_diversification_range = DIVERSIFICATION_RANGES.get(risk_profile, (0.0, 100.0))
    
    for i, portfolio in enumerate(portfolios):
        allocations = portfolio.get('allocations', [])
        stock_count = len(allocations)
        expected_return = portfolio.get('expectedReturn', 0.0) / 100.0
        diversification = portfolio.get('diversificationScore', 0.0)
        
        portfolio_detail = {
            'portfolio_id': i,
            'variation_id': portfolio.get('variation_id', i),
            'stock_count': stock_count,
            'expected_return': expected_return * 100,
            'diversification_score': diversification,
            'violations': []
        }
        
        if stock_count < expected_stock_range[0] or stock_count > expected_stock_range[1]:
            results['stock_count_violations'].append({
                'portfolio_id': i,
                'actual': stock_count,
                'expected_range': expected_stock_range
            })
            portfolio_detail['violations'].append('stock_count')
        
        if expected_return < expected_return_range[0] or expected_return > expected_return_range[1]:
            results['return_range_violations'].append({
                'portfolio_id': i,
                'actual': expected_return * 100,
                'expected_range': (expected_return_range[0] * 100, expected_return_range[1] * 100)
            })
            portfolio_detail['violations'].append('return_range')
        
        if diversification < expected_diversification_range[0] or diversification > expected_diversification_range[1]:
            results['diversification_violations'].append({
                'portfolio_id': i,
                'actual': diversification,
                'expected_range': expected_diversification_range
            })
            portfolio_detail['violations'].append('diversification_range')
        
        results['portfolio_details'].append(portfolio_detail)
    
    return results


def generate_report(redis_client):
    """Generate comprehensive verification report"""
    print("\n" + "="*80)
    print("PORTFOLIO VERIFICATION REPORT")
    print("="*80)
    
    all_results = {}
    
    for risk_profile in RISK_PROFILES:
        print(f"\n{'='*80}")
        print(f"ANALYZING: {risk_profile.upper()}")
        print(f"{'='*80}")
        
        portfolios = load_portfolios_from_redis(redis_client, risk_profile)
        
        if not portfolios:
            print(f"❌ No portfolios found for {risk_profile}")
            all_results[risk_profile] = {'status': 'no_portfolios', 'count': 0}
            continue
        
        print(f"✅ Loaded {len(portfolios)} portfolios")
        
        print(f"\n📊 UNIQUENESS ANALYSIS:")
        print("-" * 80)
        uniqueness_results = check_uniqueness(portfolios)
        
        total_unique_tickers = len(uniqueness_results['total_unique_tickers'])
        avg_tickers = sum(r['ticker_count'] for r in uniqueness_results['unique_tickers_per_portfolio']) / len(portfolios) if portfolios else 0
        
        print(f"  Total unique tickers: {total_unique_tickers}")
        print(f"  Average tickers per portfolio: {avg_tickers:.1f}")
        print(f"  Portfolios with duplicate tickers: {len(uniqueness_results['duplicate_tickers'])} pairs")
        
        if uniqueness_results['duplicate_tickers']:
            print(f"  ⚠️  TICKER OVERLAP DETECTED:")
            for dup in uniqueness_results['duplicate_tickers'][:3]:
                print(f"    Portfolios {dup['portfolios']} share: {', '.join(dup['shared_tickers'])}")
        else:
            print(f"  ✅ All portfolios have unique ticker sets")
        
        overlap_rate = uniqueness_results['overlap_percentage'].get('overlap_rate', 0)
        print(f"  Overall overlap rate: {overlap_rate:.1f}%")
        
        print(f"\n📋 CONSTRAINT CHECK:")
        print("-" * 80)
        constraint_results = check_risk_profile_constraints(portfolios, risk_profile)
        
        violations_count = (
            len(constraint_results['stock_count_violations']) +
            len(constraint_results['return_range_violations']) +
            len(constraint_results['diversification_violations'])
        )
        
        if violations_count == 0:
            print(f"  ✅ All portfolios meet constraints")
        else:
            print(f"  ⚠️  {violations_count} violations found:")
            if constraint_results['stock_count_violations']:
                print(f"    - Stock count: {len(constraint_results['stock_count_violations'])}")
            if constraint_results['return_range_violations']:
                print(f"    - Return range: {len(constraint_results['return_range_violations'])}")
            if constraint_results['diversification_violations']:
                print(f"    - Diversification: {len(constraint_results['diversification_violations'])}")
        
        all_results[risk_profile] = {
            'status': 'analyzed',
            'portfolio_count': len(portfolios),
            'uniqueness': uniqueness_results,
            'constraints': constraint_results,
            'violations_count': violations_count
        }
    
    print(f"\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}")
    
    total_portfolios = sum(r['portfolio_count'] for r in all_results.values() if r.get('status') == 'analyzed')
    total_violations = sum(r.get('violations_count', 0) for r in all_results.values())
    
    print(f"  Total portfolios: {total_portfolios}/60")
    print(f"  Total violations: {total_violations}")
    
    return all_results


def main():
    """Main execution"""
    print("🔍 Portfolio Verification Script")
    print("=" * 80)
    
    redis_client = connect_redis()
    if not redis_client:
        return 1
    
    results = generate_report(redis_client)
    
    output_file = os.path.join(os.path.dirname(__file__), '..', 'verification_results.json')
    try:
        def convert_for_json(obj):
            if isinstance(obj, set):
                return list(obj)
            elif isinstance(obj, dict):
                return {k: convert_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_for_json(item) for item in obj]
            return obj
        
        with open(output_file, 'w') as f:
            json.dump(convert_for_json(results), f, indent=2, default=str)
        print(f"\n✅ Results saved to: {output_file}")
    except Exception as e:
        print(f"⚠️  Could not save results: {e}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

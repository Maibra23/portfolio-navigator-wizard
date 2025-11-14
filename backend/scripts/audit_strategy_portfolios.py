#!/usr/bin/env python3
"""
Strategy Portfolio Cache Audit Script
Comprehensive audit and review of all strategy portfolios cached in Redis
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import redis
    from utils.redis_first_data_service import RedisFirstDataService
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


class StrategyPortfolioAuditor:
    """Audit and review strategy portfolios in Redis"""
    
    def __init__(self):
        self.redis_service = RedisFirstDataService()
        if not self.redis_service or not self.redis_service.redis_client:
            raise ConnectionError("❌ Cannot connect to Redis")
        self.redis_client = self.redis_service.redis_client
        
    def get_all_strategy_keys(self) -> List[bytes]:
        """Get all strategy portfolio keys from Redis"""
        return self.redis_client.keys("strategy_portfolios:*")
    
    def parse_key(self, key: bytes) -> Dict[str, str]:
        """Parse Redis key to extract components"""
        key_str = key.decode('utf-8') if isinstance(key, bytes) else key
        parts = key_str.split(':')
        
        result = {
            'full_key': key_str,
            'type': parts[1] if len(parts) > 1 else 'unknown',  # pure or personalized
        }
        
        if result['type'] == 'pure':
            result['strategy'] = parts[2] if len(parts) > 2 else 'unknown'
        elif result['type'] == 'personalized':
            result['strategy'] = parts[2] if len(parts) > 2 else 'unknown'
            result['risk_profile'] = parts[3] if len(parts) > 3 else 'unknown'
        
        return result
    
    def get_portfolio_data(self, key: str) -> Optional[Dict]:
        """Retrieve and parse portfolio data from Redis"""
        try:
            data = self.redis_client.get(key)
            if not data:
                return None
            
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            
            return json.loads(data)
        except Exception as e:
            print(f"⚠️  Error parsing data for {key}: {e}")
            return None
    
    def validate_portfolio_structure(self, portfolio: Dict) -> Dict[str, Any]:
        """Validate portfolio structure and return issues"""
        issues = []
        warnings = []
        
        required_fields = ['symbol', 'allocation']
        optional_fields = ['name', 'assetType']
        
        # Check if it's a portfolio dict or a list of allocations
        if 'allocations' in portfolio:
            allocations = portfolio['allocations']
        elif isinstance(portfolio, list):
            allocations = portfolio
        else:
            issues.append("Invalid portfolio structure - missing 'allocations' or not a list")
            return {'issues': issues, 'warnings': warnings, 'valid': False}
        
        if not isinstance(allocations, list):
            issues.append("'allocations' is not a list")
            return {'issues': issues, 'warnings': warnings, 'valid': False}
        
        total_allocation = 0
        symbols = set()
        
        for i, allocation in enumerate(allocations):
            if not isinstance(allocation, dict):
                issues.append(f"Allocation {i} is not a dictionary")
                continue
            
            # Check required fields
            for field in required_fields:
                if field not in allocation:
                    issues.append(f"Allocation {i} missing required field: {field}")
            
            # Check symbol
            symbol = allocation.get('symbol', '').strip()
            if not symbol:
                issues.append(f"Allocation {i} has empty or missing symbol")
            elif symbol in symbols:
                warnings.append(f"Duplicate symbol found: {symbol}")
            else:
                symbols.add(symbol)
            
            # Check allocation value
            allocation_value = allocation.get('allocation', 0)
            try:
                allocation_value = float(allocation_value)
                total_allocation += allocation_value
                
                if allocation_value < 0:
                    issues.append(f"Allocation {i} ({symbol}) has negative value: {allocation_value}")
                if allocation_value > 100:
                    warnings.append(f"Allocation {i} ({symbol}) exceeds 100%: {allocation_value}%")
            except (ValueError, TypeError):
                issues.append(f"Allocation {i} ({symbol}) has invalid allocation value: {allocation_value}")
        
        # Check total allocation
        # Allocations can be stored as decimals (0-1) or percentages (0-100)
        # If total is <= 1.0, assume decimals; if > 1.0, assume percentages
        if total_allocation <= 1.0:
            # Stored as decimals, convert to percentage for display
            total_percentage = total_allocation * 100
            if abs(total_percentage - 100.0) > 0.1:
                warnings.append(f"Total allocation is {total_percentage:.2f}% (expected ~100%) - stored as decimal: {total_allocation}")
        else:
            # Stored as percentages
            if abs(total_allocation - 100.0) > 0.1:
                warnings.append(f"Total allocation is {total_allocation:.2f}% (expected ~100%)")
        
        return {
            'issues': issues,
            'warnings': warnings,
            'valid': len(issues) == 0,
            'total_allocation': total_allocation,
            'symbol_count': len(symbols),
            'unique_symbols': list(symbols)
        }
    
    def audit_portfolio_group(self, key_info: Dict, data: Dict) -> Dict[str, Any]:
        """Audit a group of portfolios (pure or personalized)"""
        result = {
            'key': key_info['full_key'],
            'type': key_info['type'],
            'strategy': key_info.get('strategy', 'unknown'),
            'risk_profile': key_info.get('risk_profile'),
            'ttl_seconds': self.redis_client.ttl(key_info['full_key']),
            'generated_at': data.get('generated_at'),
            'count': data.get('count', 0),
            'portfolios': [],
            'summary': {}
        }
        
        portfolios = data.get('portfolios', [])
        if not portfolios:
            result['summary']['error'] = "No portfolios found in cache"
            return result
        
        # Validate each portfolio
        validation_results = []
        all_symbols = set()
        total_portfolios = len(portfolios)
        
        for i, portfolio in enumerate(portfolios):
            validation = self.validate_portfolio_structure(portfolio)
            validation_results.append(validation)
            
            # Collect symbols
            if 'unique_symbols' in validation:
                all_symbols.update(validation['unique_symbols'])
            
            # Store portfolio info
            portfolio_info = {
                'index': i,
                'name': portfolio.get('name', f'Portfolio {i+1}'),
                'symbol_count': validation.get('symbol_count', 0),
                'total_allocation': validation.get('total_allocation', 0),
                'valid': validation.get('valid', False),
                'issues': validation.get('issues', []),
                'warnings': validation.get('warnings', [])
            }
            
            # Add metrics if available
            if 'expectedReturn' in portfolio:
                portfolio_info['expected_return'] = portfolio['expectedReturn']
            if 'risk' in portfolio:
                portfolio_info['risk'] = portfolio['risk']
            if 'diversificationScore' in portfolio:
                portfolio_info['diversification_score'] = portfolio['diversificationScore']
            
            result['portfolios'].append(portfolio_info)
        
        # Summary statistics
        valid_count = sum(1 for v in validation_results if v.get('valid', False))
        total_issues = sum(len(v.get('issues', [])) for v in validation_results)
        total_warnings = sum(len(v.get('warnings', [])) for v in validation_results)
        
        result['summary'] = {
            'total_portfolios': total_portfolios,
            'valid_portfolios': valid_count,
            'invalid_portfolios': total_portfolios - valid_count,
            'total_issues': total_issues,
            'total_warnings': total_warnings,
            'unique_symbols_count': len(all_symbols),
            'all_symbols': sorted(list(all_symbols))
        }
        
        return result
    
    def run_full_audit(self) -> Dict[str, Any]:
        """Run comprehensive audit of all strategy portfolios"""
        print("🔍 Starting Strategy Portfolio Cache Audit...")
        print("=" * 80)
        
        keys = self.get_all_strategy_keys()
        print(f"📊 Found {len(keys)} strategy portfolio cache keys\n")
        
        if not keys:
            return {
                'total_keys': 0,
                'audit_results': [],
                'summary': {
                    'error': 'No strategy portfolio keys found in Redis'
                }
            }
        
        audit_results = []
        summary_stats = {
            'pure_strategies': defaultdict(int),
            'personalized_strategies': defaultdict(lambda: defaultdict(int)),
            'total_portfolios': 0,
            'valid_portfolios': 0,
            'invalid_portfolios': 0,
            'total_issues': 0,
            'total_warnings': 0,
            'strategies': set(),
            'risk_profiles': set()
        }
        
        for key in keys:
            key_info = self.parse_key(key)
            data = self.get_portfolio_data(key_info['full_key'])
            
            if not data:
                print(f"⚠️  Could not retrieve data for {key_info['full_key']}")
                continue
            
            print(f"📦 Auditing: {key_info['full_key']}")
            audit_result = self.audit_portfolio_group(key_info, data)
            audit_results.append(audit_result)
            
            # Update summary stats
            strategy = key_info.get('strategy', 'unknown')
            summary_stats['strategies'].add(strategy)
            summary_stats['total_portfolios'] += audit_result['summary'].get('total_portfolios', 0)
            summary_stats['valid_portfolios'] += audit_result['summary'].get('valid_portfolios', 0)
            summary_stats['invalid_portfolios'] += audit_result['summary'].get('invalid_portfolios', 0)
            summary_stats['total_issues'] += audit_result['summary'].get('total_issues', 0)
            summary_stats['total_warnings'] += audit_result['summary'].get('total_warnings', 0)
            
            if key_info['type'] == 'pure':
                summary_stats['pure_strategies'][strategy] += audit_result['summary'].get('total_portfolios', 0)
            elif key_info['type'] == 'personalized':
                risk_profile = key_info.get('risk_profile', 'unknown')
                summary_stats['risk_profiles'].add(risk_profile)
                summary_stats['personalized_strategies'][strategy][risk_profile] += audit_result['summary'].get('total_portfolios', 0)
        
        summary_stats['strategies'] = sorted(list(summary_stats['strategies']))
        summary_stats['risk_profiles'] = sorted(list(summary_stats['risk_profiles']))
        
        return {
            'total_keys': len(keys),
            'audit_timestamp': datetime.now().isoformat(),
            'audit_results': audit_results,
            'summary': summary_stats
        }
    
    def print_audit_report(self, audit_data: Dict[str, Any]):
        """Print formatted audit report"""
        print("\n" + "=" * 80)
        print("📋 STRATEGY PORTFOLIO CACHE AUDIT REPORT")
        print("=" * 80)
        print(f"Audit Time: {audit_data['audit_timestamp']}")
        print(f"Total Cache Keys: {audit_data['total_keys']}\n")
        
        summary = audit_data['summary']
        
        if 'error' in summary:
            print(f"❌ {summary['error']}")
            return
        
        print("📊 SUMMARY STATISTICS")
        print("-" * 80)
        print(f"Total Portfolios: {summary['total_portfolios']}")
        print(f"✅ Valid Portfolios: {summary['valid_portfolios']}")
        print(f"❌ Invalid Portfolios: {summary['invalid_portfolios']}")
        print(f"⚠️  Total Issues: {summary['total_issues']}")
        print(f"⚠️  Total Warnings: {summary['total_warnings']}")
        print(f"📈 Strategies Found: {', '.join(summary['strategies'])}")
        print(f"👤 Risk Profiles Found: {', '.join(summary['risk_profiles'])}")
        print()
        
        # Pure strategies
        if summary['pure_strategies']:
            print("🔷 PURE STRATEGY PORTFOLIOS")
            print("-" * 80)
            for strategy, count in sorted(summary['pure_strategies'].items()):
                print(f"  {strategy}: {count} portfolios")
            print()
        
        # Personalized strategies
        if summary['personalized_strategies']:
            print("🔶 PERSONALIZED STRATEGY PORTFOLIOS")
            print("-" * 80)
            for strategy in sorted(summary['personalized_strategies'].keys()):
                print(f"  {strategy}:")
                for risk_profile in sorted(summary['personalized_strategies'][strategy].keys()):
                    count = summary['personalized_strategies'][strategy][risk_profile]
                    print(f"    - {risk_profile}: {count} portfolios")
            print()
        
        # Detailed results
        print("📝 DETAILED AUDIT RESULTS")
        print("=" * 80)
        
        for result in audit_data['audit_results']:
            print(f"\n🔑 Key: {result['key']}")
            print(f"   Type: {result['type']}")
            print(f"   Strategy: {result['strategy']}")
            if result.get('risk_profile'):
                print(f"   Risk Profile: {result['risk_profile']}")
            print(f"   TTL: {result['ttl_seconds']} seconds ({result['ttl_seconds'] / 3600:.1f} hours)")
            if result.get('generated_at'):
                print(f"   Generated At: {result['generated_at']}")
            
            summary_data = result['summary']
            print(f"   Total Portfolios: {summary_data['total_portfolios']}")
            print(f"   Valid: {summary_data['valid_portfolios']} | Invalid: {summary_data['invalid_portfolios']}")
            print(f"   Issues: {summary_data['total_issues']} | Warnings: {summary_data['total_warnings']}")
            print(f"   Unique Symbols: {summary_data['unique_symbols_count']}")
            
            # Show portfolio details if there are issues
            if summary_data['total_issues'] > 0 or summary_data['total_warnings'] > 0:
                print(f"\n   📋 Portfolio Details:")
                for portfolio in result['portfolios']:
                    if portfolio['issues'] or portfolio['warnings']:
                        print(f"      Portfolio {portfolio['index'] + 1}: {portfolio['name']}")
                        if portfolio['issues']:
                            for issue in portfolio['issues']:
                                print(f"        ❌ {issue}")
                        if portfolio['warnings']:
                            for warning in portfolio['warnings']:
                                print(f"        ⚠️  {warning}")
        
        print("\n" + "=" * 80)
        print("✅ Audit Complete")
        print("=" * 80)


def main():
    """Main execution"""
    try:
        auditor = StrategyPortfolioAuditor()
        audit_data = auditor.run_full_audit()
        auditor.print_audit_report(audit_data)
        
        # Save to JSON file in reports/ directory
        reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        output_file = os.path.join(reports_dir, f"strategy_portfolio_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, 'w') as f:
            json.dump(audit_data, f, indent=2, default=str)
        print(f"\n💾 Full audit data saved to: {output_file}")
        
    except ConnectionError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during audit: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Generate All Portfolios Script
Generates 60 portfolios (12 per risk profile) with updated return ranges
"""

import sys
import os
import logging
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.redis_first_data_service import RedisFirstDataService
from utils.port_analytics import PortfolioAnalytics
from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

RISK_PROFILES = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']


def main():
    print("🚀 Generating All Portfolios")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize services
    try:
        data_service = RedisFirstDataService()
        portfolio_analytics = PortfolioAnalytics()
        generator = EnhancedPortfolioGenerator(data_service, portfolio_analytics)
        
        print("✅ Services initialized")
        print()
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        return 1
    
    # Generate portfolios for each risk profile
    all_results = {}
    
    for risk_profile in RISK_PROFILES:
        print(f"{'='*80}")
        print(f"Generating portfolios for: {risk_profile.upper()}")
        print(f"{'='*80}")
        
        try:
            portfolios = generator.generate_portfolio_bucket(risk_profile, use_parallel=False)
            
            if portfolios:
                all_results[risk_profile] = {
                    'count': len(portfolios),
                    'status': 'success'
                }
                print(f"✅ Generated {len(portfolios)} portfolios for {risk_profile}")
            else:
                all_results[risk_profile] = {
                    'count': 0,
                    'status': 'failed'
                }
                print(f"❌ Failed to generate portfolios for {risk_profile}")
        
        except Exception as e:
            logger.error(f"❌ Error generating portfolios for {risk_profile}: {e}")
            all_results[risk_profile] = {
                'count': 0,
                'status': 'error',
                'error': str(e)
            }
        
        print()
    
    # Summary
    print(f"{'='*80}")
    print("GENERATION SUMMARY")
    print(f"{'='*80}")
    
    total_portfolios = sum(r['count'] for r in all_results.values())
    
    for risk_profile in RISK_PROFILES:
        result = all_results.get(risk_profile, {})
        status_icon = "✅" if result.get('status') == 'success' else "❌"
        print(f"{status_icon} {risk_profile}: {result.get('count', 0)}/12 portfolios")
    
    print()
    print(f"Total: {total_portfolios}/60 portfolios generated")
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if total_portfolios == 60:
        print("\n🎉 All portfolios generated successfully!")
        return 0
    else:
        print(f"\n⚠️  Warning: Only {total_portfolios}/60 portfolios generated")
        return 1


if __name__ == '__main__':
    sys.exit(main())

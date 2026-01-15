#!/usr/bin/env python3
"""
One-time script to:
1. Delete all portfolios for "moderate" risk profile
2. Regenerate portfolios for ALL risk profiles (including moderate)

This uses the existing, validated system (EnhancedPortfolioGenerator + RedisPortfolioManager)
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.redis_first_data_service import redis_first_data_service
from utils.port_analytics import PortfolioAnalytics
from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
from utils.redis_portfolio_manager import RedisPortfolioManager

PROFILES = [
    'very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive'
]

def main():
    print("=" * 80)
    print("Portfolio Regeneration Script")
    print("=" * 80)
    print()
    
    # Initialize services
    print("🔧 Initializing services...")
    redis_client = redis_first_data_service.redis_client
    
    if not redis_client:
        print("❌ Redis client not available. Please ensure Redis is running.")
        sys.exit(1)
    
    portfolio_manager = RedisPortfolioManager(redis_client)
    portfolio_analytics = PortfolioAnalytics()
    # Use conservative approach + Strategy 5 for aggressive profiles
    portfolio_generator = EnhancedPortfolioGenerator(redis_first_data_service, portfolio_analytics, use_conservative_approach=True)
    
    print("✅ Services initialized")
    print()
    
    # Step 1: Delete all moderate portfolios
    print("=" * 80)
    print("Step 1: Deleting existing portfolios for 'moderate' risk profile")
    print("=" * 80)
    
    moderate_keys = redis_client.keys('portfolio_bucket:moderate:*')
    if moderate_keys:
        print(f"Found {len(moderate_keys)} keys for moderate profile")
        success = portfolio_manager.clear_portfolio_bucket('moderate')
        if success:
            print(f"✅ Successfully deleted all portfolios for 'moderate' profile")
        else:
            print("⚠️  Portfolio deletion may have failed")
    else:
        print("ℹ️  No existing portfolios found for 'moderate' profile")
    
    # Also delete top_pick if it exists
    top_pick_key = 'portfolio:top_pick:moderate'
    if redis_client.exists(top_pick_key):
        redis_client.delete(top_pick_key)
        print("✅ Deleted moderate top_pick")
    
    # Also delete stats if they exist
    stats_key = 'portfolio:stats:moderate'
    if redis_client.exists(stats_key):
        redis_client.delete(stats_key)
        print("✅ Deleted moderate stats")
    
    print()
    
    # Step 2: Regenerate portfolios for ALL risk profiles
    print("=" * 80)
    print("Step 2: Regenerating portfolios for ALL risk profiles")
    print("=" * 80)
    print(f"Profiles to regenerate: {', '.join(PROFILES)}")
    print(f"Expected: 12 portfolios per profile × {len(PROFILES)} profiles = {12 * len(PROFILES)} total portfolios")
    print()
    
    results = {}
    total_portfolios = 0
    
    for profile in PROFILES:
        print(f"🔄 Regenerating portfolios for '{profile}' profile...")
        try:
            # Generate 12 portfolios for this risk profile
            portfolios = portfolio_generator.generate_portfolio_bucket(profile, use_parallel=True)
            
            if portfolios and len(portfolios) >= 12:
                total_portfolios += len(portfolios)
                results[profile] = {
                    'success': True,
                    'count': len(portfolios),
                    'timestamp': datetime.now().isoformat()
                }
                print(f"  ✅ Generated {len(portfolios)} portfolios for '{profile}'")
            else:
                results[profile] = {
                    'success': False,
                    'error': f"Only {len(portfolios) if portfolios else 0} portfolios generated (expected 12)",
                    'timestamp': datetime.now().isoformat()
                }
                print(f"  ❌ Failed to generate sufficient portfolios for '{profile}'")
        except Exception as e:
            results[profile] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            print(f"  ❌ Error generating portfolios for '{profile}': {e}")
        print()
    
    # Summary
    print("=" * 80)
    print("Regeneration Summary")
    print("=" * 80)
    
    successful_profiles = [p for p, r in results.items() if r.get('success')]
    failed_profiles = [p for p, r in results.items() if not r.get('success')]
    
    print(f"✅ Successful profiles: {len(successful_profiles)}/{len(PROFILES)}")
    for profile in successful_profiles:
        count = results[profile].get('count', 0)
        print(f"   • {profile}: {count} portfolios")
    
    if failed_profiles:
        print(f"\n❌ Failed profiles: {len(failed_profiles)}/{len(PROFILES)}")
        for profile in failed_profiles:
            error = results[profile].get('error', 'Unknown error')
            print(f"   • {profile}: {error}")
    
    print(f"\n📊 Total portfolios generated: {total_portfolios}/{12 * len(PROFILES)}")
    print()
    
    # Verify final state
    print("=" * 80)
    print("Final Verification")
    print("=" * 80)
    
    for profile in PROFILES:
        count = portfolio_manager.get_portfolio_count(profile)
        status = "✅" if count >= 12 else "❌"
        print(f"  {status} {profile}: {count}/12 portfolios")
    
    print()
    print("=" * 80)
    if len(successful_profiles) == len(PROFILES):
        print("✅ Regeneration completed successfully!")
    else:
        print("⚠️  Regeneration completed with some failures. Please review the output above.")
    print("=" * 80)

if __name__ == "__main__":
    main()

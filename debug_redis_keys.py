#!/usr/bin/env python3
"""
Debug script to check Redis keys for strategy portfolios
"""

import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from utils.redis_first_data_service import RedisFirstDataService

def debug_redis_keys():
    """Debug Redis keys for strategy portfolios"""
    print("🔍 Debugging Redis Keys for Strategy Portfolios...")
    
    try:
        # Initialize Redis service
        data_service = RedisFirstDataService()
        
        if not data_service.redis_client:
            print("❌ Redis not available")
            return
        
        # Check all keys related to strategy portfolios
        all_keys = data_service.redis_client.keys("*strategy*")
        print(f"📊 Found {len(all_keys)} keys containing 'strategy':")
        
        for key in sorted(all_keys):
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            print(f"   - {key_str}")
        
        # Check specific bucket keys
        print("\n🔍 Checking specific bucket keys:")
        
        strategies = ['diversification', 'risk', 'return']
        risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
        
        for strategy in strategies:
            # Check pure strategy bucket
            pure_bucket = f"strategy_bucket:pure:{strategy}"
            print(f"\n📦 Pure {strategy} bucket:")
            
            for i in range(5):
                portfolio_key = f"{pure_bucket}:{i}"
                exists = data_service.redis_client.exists(portfolio_key)
                print(f"   {portfolio_key}: {'✅' if exists else '❌'}")
            
            # Check personalized strategy buckets
            for risk_profile in risk_profiles:
                personalized_bucket = f"strategy_bucket:personalized:{risk_profile}:{strategy}"
                print(f"\n📦 Personalized {risk_profile}:{strategy} bucket:")
                
                for i in range(5):
                    portfolio_key = f"{personalized_bucket}:{i}"
                    exists = data_service.redis_client.exists(portfolio_key)
                    print(f"   {portfolio_key}: {'✅' if exists else '❌'}")
        
        # Check metadata keys
        print("\n🔍 Checking metadata keys:")
        metadata_keys = data_service.redis_client.keys("*strategy*metadata*")
        for key in sorted(metadata_keys):
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            print(f"   - {key_str}")
        
    except Exception as e:
        print(f"❌ Error debugging Redis keys: {e}")

if __name__ == "__main__":
    debug_redis_keys()

#!/usr/bin/env python3
"""
Test Script for StrategyPortfolioOptimizer System
Verifies the new strategy portfolio generation system works correctly
"""

import sys
import os
import logging
from datetime import datetime

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.strategy_portfolio_optimizer import StrategyPortfolioOptimizer
from utils.redis_first_data_service import redis_first_data_service
from utils.redis_portfolio_manager import RedisPortfolioManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_strategy_optimizer_creation():
    """Test 1: Verify StrategyPortfolioOptimizer can be created"""
    logger.info("🧪 Test 1: Creating StrategyPortfolioOptimizer instance...")
    
    try:
        optimizer = StrategyPortfolioOptimizer(
            data_service=redis_first_data_service,
            redis_manager=RedisPortfolioManager(redis_first_data_service.redis_client)
        )
        
        logger.info("✅ StrategyPortfolioOptimizer created successfully")
        logger.info(f"📊 Available strategies: {list(optimizer.STRATEGIES.keys())}")
        logger.info(f"📊 Risk profiles: {list(optimizer.RISK_PROFILE_CONSTRAINTS.keys())}")
        
        # Check Redis data sufficiency before proceeding
        logger.info("🔍 Checking Redis data sufficiency...")
        data_status = optimizer.check_redis_data_sufficiency()
        
        if not data_status['sufficient']:
            logger.warning(f"⚠️ Insufficient Redis data: {data_status['recommendation']}")
            logger.warning(f"   • Prices: {data_status['prices_coverage']:.1f}%")
            logger.warning(f"   • Sectors: {data_status['sectors_coverage']:.1f}%")
            logger.warning(f"   • Metrics: {data_status['metrics_coverage']:.1f}%")
            
            # Check if we can still proceed with limited data
            if data_status['prices_coverage'] < 50 or data_status['sectors_coverage'] < 50:
                logger.error("❌ Cannot proceed - insufficient cached data")
                return None
            else:
                logger.info("⚠️ Proceeding with limited data - some portfolios may be skipped")
        else:
            logger.info("✅ Sufficient Redis data available for portfolio generation")
        
        return optimizer
        
    except Exception as e:
        logger.error(f"❌ Failed to create StrategyPortfolioOptimizer: {e}")
        return None

def test_diversification_strategy(optimizer):
    """Test 2: Test Diversification strategy portfolio generation"""
    logger.info("🧪 Test 2: Testing Diversification strategy...")
    
    try:
        # Generate diversification strategy buckets
        result = optimizer.generate_strategy_portfolio_buckets('diversification')
        
        # Verify structure
        assert 'pure' in result, "Missing 'pure' key in result"
        assert 'personalized' in result, "Missing 'personalized' key in result"
        assert 'metadata' in result, "Missing 'metadata' key in result"
        
        # Verify pure portfolios
        pure_portfolios = result['pure']['diversification']
        assert len(pure_portfolios) > 0, "No pure portfolios generated"
        logger.info(f"✅ Generated {len(pure_portfolios)} pure diversification portfolios")
        
        # Verify personalized portfolios
        personalized_portfolios = result['personalized']
        assert len(personalized_portfolios) > 0, "No personalized portfolios generated"
        
        for risk_profile, portfolios in personalized_portfolios.items():
            assert len(portfolios) > 0, f"No portfolios for {risk_profile}"
            logger.info(f"✅ Generated {len(portfolios)} {risk_profile} portfolios")
        
        # Verify metadata
        metadata = result['metadata']
        assert metadata['strategy'] == 'diversification', "Wrong strategy in metadata"
        assert metadata['total_portfolios'] > 0, "No total portfolio count in metadata"
        
        logger.info("✅ Diversification strategy test passed")
        return result
        
    except Exception as e:
        logger.error(f"❌ Diversification strategy test failed: {e}")
        return None

def test_risk_strategy(optimizer):
    """Test 3: Test Risk strategy portfolio generation"""
    logger.info("🧪 Test 3: Testing Risk strategy...")
    
    try:
        # Generate risk strategy buckets
        result = optimizer.generate_strategy_portfolio_buckets('risk')
        
        # Verify structure
        assert 'pure' in result, "Missing 'pure' key in result"
        assert 'personalized' in result, "Missing 'personalized' key in result"
        
        # Verify pure portfolios
        pure_portfolios = result['pure']['risk']
        assert len(pure_portfolios) > 0, "No pure risk portfolios generated"
        logger.info(f"✅ Generated {len(pure_portfolios)} pure risk portfolios")
        
        # Verify personalized portfolios
        personalized_portfolios = result['personalized']
        for risk_profile, portfolios in personalized_portfolios.items():
            assert len(portfolios) > 0, f"No risk portfolios for {risk_profile}"
            logger.info(f"✅ Generated {len(portfolios)} {risk_profile} risk portfolios")
        
        logger.info("✅ Risk strategy test passed")
        return result
        
    except Exception as e:
        logger.error(f"❌ Risk strategy test failed: {e}")
        return None

def test_return_strategy(optimizer):
    """Test 4: Test Return strategy portfolio generation"""
    logger.info("🧪 Test 4: Testing Return strategy...")
    
    try:
        # Generate return strategy buckets
        result = optimizer.generate_strategy_portfolio_buckets('return')
        
        # Verify structure
        assert 'pure' in result, "Missing 'pure' key in result"
        assert 'personalized' in result, "Missing 'personalized' key in result"
        
        # Verify pure portfolios
        pure_portfolios = result['pure']['return']
        assert len(pure_portfolios) > 0, "No pure return portfolios generated"
        logger.info(f"✅ Generated {len(pure_portfolios)} pure return portfolios")
        
        # Verify personalized portfolios
        personalized_portfolios = result['personalized']
        for risk_profile, portfolios in personalized_portfolios.items():
            assert len(portfolios) > 0, f"No return portfolios for {risk_profile}"
            logger.info(f"✅ Generated {len(portfolios)} {risk_profile} return portfolios")
        
        logger.info("✅ Return strategy test passed")
        return result
        
    except Exception as e:
        logger.error(f"❌ Return strategy test failed: {e}")
        return None

def test_portfolio_structure(optimizer):
    """Test 5: Verify portfolio structure and content"""
    logger.info("🧪 Test 5: Verifying portfolio structure...")
    
    try:
        # Generate a sample portfolio to examine structure
        result = optimizer.generate_strategy_portfolio_buckets('diversification')
        sample_portfolio = result['pure']['diversification'][0]
        
        # Verify portfolio fields
        required_fields = ['id', 'name', 'description', 'strategy', 'type', 'risk_profile', 
                          'allocations', 'metrics', 'generated_at', 'constraints_applied']
        
        for field in required_fields:
            assert field in sample_portfolio, f"Missing field: {field}"
        
        # Verify portfolio type
        assert sample_portfolio['type'] == 'pure', "Portfolio type should be 'pure'"
        assert sample_portfolio['risk_profile'] is None, "Pure portfolio should have no risk profile"
        
        # Verify allocations
        allocations = sample_portfolio['allocations']
        assert len(allocations) > 0, "No allocations in portfolio"
        
        for allocation in allocations:
            assert 'symbol' in allocation, "Allocation missing symbol"
            assert 'allocation' in allocation, "Allocation missing weight"
            assert 'sector' in allocation, "Allocation missing sector"
        
        # Verify metrics
        metrics = sample_portfolio['metrics']
        required_metrics = ['expected_return', 'risk', 'sharpe_ratio', 'diversification_score', 
                           'sector_breakdown', 'num_stocks', 'strategy']
        
        for metric in required_metrics:
            assert metric in metrics, f"Missing metric: {metric}"
        
        logger.info("✅ Portfolio structure test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Portfolio structure test failed: {e}")
        return False

def test_pure_vs_personalized_differentiation(optimizer):
    """Test 6: Verify Pure vs Personalized portfolios are actually different"""
    logger.info("🧪 Test 6: Verifying Pure vs Personalized differentiation...")
    
    try:
        # Generate both types of portfolios
        result = optimizer.generate_strategy_portfolio_buckets('diversification')
        
        pure_portfolios = result['pure']['diversification']
        personalized_portfolios = result['personalized']['moderate']  # Use moderate as example
        
        assert len(pure_portfolios) > 0, "No pure portfolios to compare"
        assert len(personalized_portfolios) > 0, "No personalized portfolios to compare"
        
        # Compare portfolio characteristics
        pure_sample = pure_portfolios[0]
        personalized_sample = personalized_portfolios[0]
        
        # Verify they have different types
        assert pure_sample['type'] == 'pure', "First portfolio should be pure"
        assert personalized_sample['type'] == 'personalized', "Second portfolio should be personalized"
        
        # Verify they have different risk profiles
        assert pure_sample['risk_profile'] is None, "Pure portfolio should have no risk profile"
        assert personalized_sample['risk_profile'] == 'moderate', "Personalized portfolio should have risk profile"
        
        # Verify they have different constraints
        assert pure_sample['constraints_applied'] == 'none', "Pure portfolio should have no constraints"
        assert 'strategy_diversification_risk_moderate' in personalized_sample['constraints_applied'], "Personalized portfolio should have constraints"
        
        logger.info("✅ Pure vs Personalized differentiation test passed")
        logger.info(f"📊 Pure portfolio constraints: {pure_sample['constraints_applied']}")
        logger.info(f"📊 Personalized portfolio constraints: {personalized_sample['constraints_applied']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Pure vs Personalized differentiation test failed: {e}")
        return False

def main():
    """Run all tests for the StrategyPortfolioOptimizer system"""
    logger.info("🚀 Starting StrategyPortfolioOptimizer System Tests")
    logger.info("=" * 60)
    
    # Test 1: Create optimizer
    optimizer = test_strategy_optimizer_creation()
    if not optimizer:
        logger.error("❌ Cannot proceed with tests - optimizer creation failed")
        return False
    
    # Test 2-4: Test each strategy
    diversification_result = test_diversification_strategy(optimizer)
    risk_result = test_risk_strategy(optimizer)
    return_result = test_return_strategy(optimizer)
    
    if not all([diversification_result, risk_result, return_result]):
        logger.error("❌ Strategy generation tests failed")
        return False
    
    # Test 5-6: Test portfolio structure and differentiation
    structure_ok = test_portfolio_structure(optimizer)
    differentiation_ok = test_pure_vs_personalized_differentiation(optimizer)
    
    if not all([structure_ok, differentiation_ok]):
        logger.error("❌ Portfolio structure tests failed")
        return False
    
    # Summary
    logger.info("=" * 60)
    logger.info("🎉 ALL TESTS PASSED! StrategyPortfolioOptimizer System is working correctly")
    logger.info("=" * 60)
    
    # Display sample results
    logger.info("📊 Sample Results Summary:")
    logger.info(f"   • Diversification: {len(diversification_result['pure']['diversification'])} pure + {sum(len(portfolios) for portfolios in diversification_result['personalized'].values())} personalized")
    logger.info(f"   • Risk: {len(risk_result['pure']['risk'])} pure + {sum(len(portfolios) for portfolios in risk_result['personalized'].values())} personalized")
    logger.info(f"   • Return: {len(return_result['pure']['return'])} pure + {sum(len(portfolios) for portfolios in return_result['personalized'].values())} personalized")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

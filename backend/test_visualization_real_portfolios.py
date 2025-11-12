#!/usr/bin/env python3
"""
Test visualization endpoints with real portfolio recommendations
Tests different portfolios individually and jointly
"""

import requests
import json
import time
from typing import Dict, List, Any

BASE_URL = "http://localhost:8000/api/portfolio"

def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def get_portfolio_recommendations(risk_profile: str) -> List[Dict]:
    """Get portfolio recommendations for a risk profile"""
    try:
        response = requests.get(
            f"{BASE_URL}/recommendations/{risk_profile}",
            timeout=15
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️ Failed to get recommendations: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error fetching recommendations: {e}")
        return []

def test_clustering_with_real_portfolios():
    """Test clustering analysis with real portfolio recommendations"""
    print_section("TEST: Clustering Analysis with Real Portfolios")
    
    risk_profiles = ["moderate", "conservative", "aggressive"]
    results = []
    
    for risk_profile in risk_profiles:
        print(f"\n📊 Testing with {risk_profile} risk profile...")
        recommendations = get_portfolio_recommendations(risk_profile)
        
        if len(recommendations) < 2:
            print(f"   ⚠️ Insufficient recommendations ({len(recommendations)}) for {risk_profile}")
            continue
        
        # Test with first portfolio as selected
        selected_index = 0
        selected_portfolio = recommendations[selected_index].get('portfolio', [])
        
        request_data = {
            "selectedPortfolio": selected_portfolio,
            "allRecommendations": recommendations,
            "selectedPortfolioIndex": selected_index,
            "riskProfile": risk_profile
        }
        
        start_time = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/visualization/clustering-analysis",
                json=request_data,
                timeout=30
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success - {elapsed:.3f}s")
                print(f"      Points: {len(data.get('points', []))}")
                print(f"      Clusters: {len(data.get('clusters', []))}")
                print(f"      Cache Hits: {data.get('metadata', {}).get('cacheHits', 0)}")
                print(f"      Cache Misses: {data.get('metadata', {}).get('cacheMisses', 0)}")
                
                # Verify point data
                points = data.get('points', [])
                if points:
                    first_point = points[0]
                    print(f"      First Point - Label: {first_point.get('label')}, Risk: {first_point.get('risk'):.4f}, Return: {first_point.get('returnValue', 0):.4f}")
                
                results.append({
                    "risk_profile": risk_profile,
                    "success": True,
                    "elapsed": elapsed,
                    "points": len(points),
                    "clusters": len(data.get('clusters', []))
                })
            else:
                print(f"   ❌ Failed - Status {response.status_code}")
                print(f"      Error: {response.text[:200]}")
                results.append({"risk_profile": risk_profile, "success": False})
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({"risk_profile": risk_profile, "success": False})
    
    return results

def test_correlation_with_real_portfolios():
    """Test correlation matrix with tickers from real portfolios"""
    print_section("TEST: Correlation Matrix with Real Portfolio Tickers")
    
    risk_profiles = ["moderate", "conservative", "aggressive"]
    results = []
    
    for risk_profile in risk_profiles:
        print(f"\n📊 Testing with {risk_profile} risk profile...")
        recommendations = get_portfolio_recommendations(risk_profile)
        
        if not recommendations:
            print(f"   ⚠️ No recommendations for {risk_profile}")
            continue
        
        # Get tickers from first portfolio
        portfolio = recommendations[0].get('portfolio', [])
        tickers = [alloc.get('symbol') for alloc in portfolio if alloc.get('symbol')]
        
        if len(tickers) < 2:
            print(f"   ⚠️ Insufficient tickers ({len(tickers)}) for correlation")
            continue
        
        # Test with all tickers from portfolio
        tickers_str = ','.join(tickers)
        
        start_time = time.time()
        try:
            response = requests.get(
                f"{BASE_URL}/visualization/correlation-matrix",
                params={"tickers": tickers_str},
                timeout=30
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success - {elapsed:.3f}s")
                print(f"      Tickers: {len(data.get('tickers', []))}")
                print(f"      Matrix Size: {len(data.get('matrix', []))}x{len(data.get('matrix', [])[0]) if data.get('matrix') else 0}")
                print(f"      Data Points: {data.get('metadata', {}).get('dataPoints', 0)}")
                print(f"      Missing: {len(data.get('missingTickers', []))}")
                print(f"      Warnings: {len(data.get('warnings', []))}")
                
                # Verify matrix symmetry
                matrix = data.get('matrix', [])
                if matrix:
                    n = len(matrix)
                    symmetric = all(
                        abs(matrix[i][j] - matrix[j][i]) < 0.0001 
                        for i in range(n) 
                        for j in range(n)
                    )
                    diagonal_ones = all(abs(matrix[i][i] - 1.0) < 0.0001 for i in range(n))
                    print(f"      Matrix Symmetric: {symmetric}")
                    print(f"      Diagonal Ones: {diagonal_ones}")
                
                results.append({
                    "risk_profile": risk_profile,
                    "success": True,
                    "elapsed": elapsed,
                    "tickers": len(data.get('tickers', []))
                })
            else:
                print(f"   ❌ Failed - Status {response.status_code}")
                results.append({"risk_profile": risk_profile, "success": False})
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({"risk_profile": risk_profile, "success": False})
    
    return results

def test_sector_allocation_with_real_portfolios():
    """Test sector allocation with real portfolio allocations"""
    print_section("TEST: Sector Allocation with Real Portfolio Allocations")
    
    risk_profiles = ["moderate", "conservative", "aggressive"]
    results = []
    
    for risk_profile in risk_profiles:
        print(f"\n📊 Testing with {risk_profile} risk profile...")
        recommendations = get_portfolio_recommendations(risk_profile)
        
        if not recommendations:
            print(f"   ⚠️ No recommendations for {risk_profile}")
            continue
        
        # Test with first portfolio
        portfolio = recommendations[0].get('portfolio', [])
        tickers = [alloc.get('symbol') for alloc in portfolio]
        weights = [alloc.get('allocation', 0) for alloc in portfolio]
        
        if not tickers:
            print(f"   ⚠️ No tickers in portfolio")
            continue
        
        tickers_str = ','.join(tickers)
        weights_str = ','.join([str(w) for w in weights])
        
        start_time = time.time()
        try:
            response = requests.get(
                f"{BASE_URL}/visualization/sector-allocation",
                params={
                    "tickers": tickers_str,
                    "weights": weights_str,
                    "portfolioLabel": f"{risk_profile.title()} Portfolio"
                },
                timeout=30
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success - {elapsed:.3f}s")
                print(f"      Sectors: {len(data.get('sectors', []))}")
                print(f"      Total Percent: {data.get('totalPercent', 0)}%")
                print(f"      Warnings: {len(data.get('warnings', []))}")
                
                # Print top sectors
                sectors = data.get('sectors', [])[:5]
                print(f"      Top Sectors:")
                for sector in sectors:
                    print(f"         - {sector.get('sector')}: {sector.get('weight')}%")
                
                results.append({
                    "risk_profile": risk_profile,
                    "success": True,
                    "elapsed": elapsed,
                    "sectors": len(data.get('sectors', []))
                })
            else:
                print(f"   ❌ Failed - Status {response.status_code}")
                results.append({"risk_profile": risk_profile, "success": False})
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({"risk_profile": risk_profile, "success": False})
    
    return results

def test_consolidated_with_multiple_portfolios():
    """Test consolidated endpoint with different portfolios"""
    print_section("TEST: Consolidated Data with Multiple Real Portfolios")
    
    risk_profiles = ["moderate", "conservative", "aggressive"]
    results = []
    
    for risk_profile in risk_profiles:
        print(f"\n📊 Testing consolidated endpoint with {risk_profile} risk profile...")
        recommendations = get_portfolio_recommendations(risk_profile)
        
        if len(recommendations) < 2:
            print(f"   ⚠️ Insufficient recommendations ({len(recommendations)})")
            continue
        
        # Use first portfolio as selected
        selected_index = 0
        selected_portfolio = recommendations[selected_index].get('portfolio', [])
        
        # Get tickers for correlation
        tickers = [alloc.get('symbol') for alloc in selected_portfolio]
        correlation_tickers = ','.join(tickers)
        
        request_data = {
            "selectedPortfolio": selected_portfolio,
            "allRecommendations": recommendations,
            "selectedPortfolioIndex": selected_index,
            "riskProfile": risk_profile,
            "correlationTickers": correlation_tickers
        }
        
        start_time = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/visualization/data",
                json=request_data,
                timeout=60
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success - {elapsed:.3f}s")
                print(f"      Clustering Points: {len(data.get('clustering', {}).get('points', []))}")
                print(f"      Clustering Clusters: {len(data.get('clustering', {}).get('clusters', []))}")
                print(f"      Correlation Tickers: {len(data.get('correlation', {}).get('tickers', []))}")
                print(f"      Sector Count: {len(data.get('sectorAllocation', {}).get('sectors', []))}")
                print(f"      Total Warnings: {len(data.get('warnings', []))}")
                
                # Verify data consistency
                clustering = data.get('clustering', {})
                correlation = data.get('correlation', {})
                sector = data.get('sectorAllocation', {})
                
                print(f"      Data Consistency:")
                print(f"         - Clustering has data: {len(clustering.get('points', [])) > 0}")
                print(f"         - Correlation has data: {len(correlation.get('tickers', [])) > 0}")
                print(f"         - Sector has data: {len(sector.get('sectors', [])) > 0}")
                
                results.append({
                    "risk_profile": risk_profile,
                    "success": True,
                    "elapsed": elapsed
                })
            else:
                print(f"   ❌ Failed - Status {response.status_code}")
                print(f"      Error: {response.text[:200]}")
                results.append({"risk_profile": risk_profile, "success": False})
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({"risk_profile": risk_profile, "success": False})
    
    return results

def test_cross_portfolio_comparison():
    """Test comparing portfolios from different risk profiles"""
    print_section("TEST: Cross-Portfolio Comparison (Different Risk Profiles)")
    
    # Get portfolios from different risk profiles
    moderate_recs = get_portfolio_recommendations("moderate")
    conservative_recs = get_portfolio_recommendations("conservative")
    aggressive_recs = get_portfolio_recommendations("aggressive")
    
    if not (moderate_recs and conservative_recs and aggressive_recs):
        print("⚠️ Need recommendations from all three risk profiles")
        return
    
    # Create a combined recommendations list
    all_recommendations = []
    all_recommendations.extend(moderate_recs[:2])  # First 2 from moderate
    all_recommendations.extend(conservative_recs[:2])  # First 2 from conservative
    all_recommendations.extend(aggressive_recs[:2])  # First 2 from aggressive
    
    # Use first moderate portfolio as selected
    selected_portfolio = moderate_recs[0].get('portfolio', [])
    selected_index = 0
    
    request_data = {
        "selectedPortfolio": selected_portfolio,
        "allRecommendations": all_recommendations,
        "selectedPortfolioIndex": selected_index,
        "riskProfile": "moderate"
    }
    
    print(f"\n📊 Comparing portfolios across risk profiles...")
    print(f"   Selected: Moderate portfolio (index 0)")
    print(f"   Benchmarks: 2 Moderate + 2 Conservative + 2 Aggressive")
    print(f"   Total portfolios: {len(all_recommendations)}")
    
    start_time = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/visualization/clustering-analysis",
            json=request_data,
            timeout=30
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success - {elapsed:.3f}s")
            print(f"      Total Points: {len(data.get('points', []))}")
            print(f"      Clusters: {len(data.get('clusters', []))}")
            
            # Show point labels
            points = data.get('points', [])
            print(f"      Points Breakdown:")
            for point in points:
                print(f"         - {point.get('label')}: Risk={point.get('risk'):.4f}, Return={point.get('returnValue', 0):.4f}")
            
            return {"success": True, "elapsed": elapsed}
        else:
            print(f"   ❌ Failed - Status {response.status_code}")
            return {"success": False}
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False}

def main():
    """Run all tests with real portfolios"""
    print("\n" + "="*80)
    print("  VISUALIZATION ENDPOINTS - REAL PORTFOLIO TEST SUITE")
    print("="*80)
    
    # Check if backend is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("\n❌ Backend is not running. Please start it with: make backend")
            return
    except:
        print("\n❌ Backend is not running. Please start it with: make backend")
        return
    
    print("\n✅ Backend is running")
    
    # Run individual endpoint tests
    clustering_results = test_clustering_with_real_portfolios()
    correlation_results = test_correlation_with_real_portfolios()
    sector_results = test_sector_allocation_with_real_portfolios()
    
    # Run consolidated tests
    consolidated_results = test_consolidated_with_multiple_portfolios()
    
    # Run cross-portfolio comparison
    cross_comparison_result = test_cross_portfolio_comparison()
    
    # Summary
    print_section("TEST SUMMARY")
    
    all_results = {
        "clustering": clustering_results,
        "correlation": correlation_results,
        "sector": sector_results,
        "consolidated": consolidated_results,
        "cross_comparison": [cross_comparison_result] if cross_comparison_result else []
    }
    
    total_tests = sum(len(results) for results in all_results.values())
    passed_tests = sum(
        sum(1 for r in results if r.get('success', False))
        for results in all_results.values()
    )
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {total_tests - passed_tests}")
    
    # Performance summary
    print("\nPerformance Summary by Risk Profile:")
    for test_type, results in all_results.items():
        if test_type == "cross_comparison":
            continue
        print(f"\n  {test_type.upper()}:")
        for result in results:
            if result.get('success'):
                risk = result.get('risk_profile', 'unknown')
                elapsed = result.get('elapsed', 0)
                print(f"    ✅ {risk}: {elapsed:.3f}s")
    
    # Detailed results
    print("\nDetailed Results:")
    for test_type, results in all_results.items():
        print(f"\n  {test_type.upper()}:")
        for result in results:
            risk = result.get('risk_profile', 'cross-comparison')
            if result.get('success'):
                print(f"    ✅ {risk}: Success")
            else:
                print(f"    ❌ {risk}: Failed")
    
    print("\n" + "="*80)
    print("  TESTING COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()


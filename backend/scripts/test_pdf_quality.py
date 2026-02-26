#!/usr/bin/env python3
"""
Test script to generate a PDF with sample data for visual quality inspection.
Run from backend: python3 scripts/test_pdf_quality.py
Output: test_portfolio_report.pdf in the backend directory
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pdf_report_generator import PDFReportGenerator


def main():
    print("Generating test PDF with sample data...")

    # Sample portfolio data with realistic values
    sample_data = {
        "portfolioName": "Quality Test Portfolio",
        "portfolioValue": 500000.0,
        "accountType": "ISK",
        "taxYear": 2024,
        "courtageClass": "small",
        "metrics": {
            "expectedReturn": 0.0892,
            "risk": 0.1845,
            "sharpeRatio": 0.483,
        },
        "portfolio": [
            {"ticker": "AAPL", "name": "Apple Inc.", "allocation": 15.5, "sector": "Technology", "value": 77500},
            {"ticker": "MSFT", "name": "Microsoft Corp", "allocation": 12.3, "sector": "Technology", "value": 61500},
            {"ticker": "GOOGL", "name": "Alphabet Inc.", "allocation": 10.2, "sector": "Technology", "value": 51000},
            {"ticker": "JNJ", "name": "Johnson & Johnson", "allocation": 8.5, "sector": "Healthcare", "value": 42500},
            {"ticker": "PFE", "name": "Pfizer Inc.", "allocation": 7.8, "sector": "Healthcare", "value": 39000},
            {"ticker": "JPM", "name": "JPMorgan Chase", "allocation": 9.2, "sector": "Financials", "value": 46000},
            {"ticker": "BAC", "name": "Bank of America", "allocation": 6.5, "sector": "Financials", "value": 32500},
            {"ticker": "XOM", "name": "Exxon Mobil", "allocation": 8.0, "sector": "Energy", "value": 40000},
            {"ticker": "PG", "name": "Procter & Gamble", "allocation": 7.5, "sector": "Consumer Staples", "value": 37500},
            {"ticker": "KO", "name": "Coca-Cola", "allocation": 6.0, "sector": "Consumer Staples", "value": 30000},
            {"ticker": "VZ", "name": "Verizon", "allocation": 4.5, "sector": "Communication", "value": 22500},
            {"ticker": "NEE", "name": "NextEra Energy", "allocation": 4.0, "sector": "Utilities", "value": 20000},
        ],
        "includeSections": {
            "optimization": True,
            "stressTest": True,
            "goals": True,
            "rebalancing": True,
        },
        "taxData": {
            "schablon_tax": 3750.0,
            "tax_rate": 0.00375,
            "government_rate": 0.0294,
            "effective_rate": 0.00882,
        },
        "costData": {
            "total_annual_cost": 1250.0,
            "cost_breakdown": {
                "commission": 750.0,
                "spread": 350.0,
                "fx_cost": 150.0,
            },
        },
        "optimizationResults": {
            "original": {
                "expected_return": 0.0892,
                "risk": 0.1845,
                "sharpe_ratio": 0.483,
            },
            "weights_optimized_portfolio": {
                "metrics": {
                    "expected_return": 0.0945,
                    "risk": 0.1780,
                    "sharpe_ratio": 0.531,
                },
                "efficient_frontier": [
                    {"risk": 0.10, "return": 0.05},
                    {"risk": 0.12, "return": 0.065},
                    {"risk": 0.14, "return": 0.078},
                    {"risk": 0.16, "return": 0.088},
                    {"risk": 0.18, "return": 0.095},
                    {"risk": 0.20, "return": 0.102},
                    {"risk": 0.22, "return": 0.108},
                    {"risk": 0.24, "return": 0.112},
                ],
                "random_portfolios": [
                    {"risk": 0.11, "return": 0.048, "sharpe": 0.44},
                    {"risk": 0.13, "return": 0.062, "sharpe": 0.48},
                    {"risk": 0.15, "return": 0.071, "sharpe": 0.47},
                    {"risk": 0.17, "return": 0.082, "sharpe": 0.48},
                    {"risk": 0.19, "return": 0.089, "sharpe": 0.47},
                    {"risk": 0.21, "return": 0.098, "sharpe": 0.47},
                    {"risk": 0.14, "return": 0.055, "sharpe": 0.39},
                    {"risk": 0.16, "return": 0.068, "sharpe": 0.43},
                    {"risk": 0.18, "return": 0.078, "sharpe": 0.43},
                    {"risk": 0.20, "return": 0.085, "sharpe": 0.43},
                ],
            },
            "market_optimized_portfolio": {
                "metrics": {
                    "expected_return": 0.1023,
                    "risk": 0.1920,
                    "sharpe_ratio": 0.533,
                },
            },
        },
        "stressTestResults": {
            # Use API scenario names (2008_crisis, covid19) to match real frontend data
            "scenarios": {
                "2008_crisis": {
                    "metrics": {
                        "max_drawdown": -0.42,
                        "total_return": -0.15,
                        "worst_month_return": -0.18,
                    },
                    "monthly_performance": [
                        {"month": "Sep 2008", "value": 100000},
                        {"month": "Oct 2008", "value": 83000},
                        {"month": "Nov 2008", "value": 76000},
                        {"month": "Dec 2008", "value": 72000},
                        {"month": "Jan 2009", "value": 65000},
                        {"month": "Feb 2009", "value": 58000},
                        {"month": "Mar 2009", "value": 62000},
                        {"month": "Apr 2009", "value": 71000},
                        {"month": "May 2009", "value": 75000},
                        {"month": "Jun 2009", "value": 78000},
                    ],
                },
                "covid19": {
                    "metrics": {
                        "max_drawdown": -0.34,
                        "total_return": 0.12,
                        "worst_month_return": -0.12,
                    },
                    "monthly_performance": [
                        {"month": "Jan 2020", "value": 100000},
                        {"month": "Feb 2020", "value": 92000},
                        {"month": "Mar 2020", "value": 66000},
                        {"month": "Apr 2020", "value": 78000},
                        {"month": "May 2020", "value": 85000},
                        {"month": "Jun 2020", "value": 91000},
                        {"month": "Jul 2020", "value": 98000},
                        {"month": "Aug 2020", "value": 105000},
                    ],
                },
                "dot_com_bubble": {
                    "metrics": {
                        "max_drawdown": -0.48,
                        "total_return": -0.32,
                        "worst_month_return": -0.14,
                    },
                },
                "2022_rate_hikes": {
                    "metrics": {
                        "max_drawdown": -0.25,
                        "total_return": -0.18,
                        "worst_month_return": -0.09,
                    },
                },
            },
            "resilience_score": 62,
        },
        "projectionMetrics": {
            "years": [2024, 2025, 2026, 2027, 2028, 2029],
            "optimistic": [500000, 560000, 627200, 702464, 786760, 881171],
            "base": [500000, 544600, 593174, 646098, 703762, 766699],
            "pessimistic": [500000, 520000, 540800, 562432, 584929, 608326],
        },
    }

    generator = PDFReportGenerator()
    pdf_bytes = generator.generate_portfolio_report(sample_data)

    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "test_portfolio_report.pdf"
    )

    with open(output_path, "wb") as f:
        f.write(pdf_bytes)

    print(f"SUCCESS: PDF generated at {output_path}")
    print(f"File size: {len(pdf_bytes):,} bytes")
    print("\nOpen the PDF to visually inspect:")
    print("  - Chart sharpness (300 DPI)")
    print("  - Color consistency (unified palette)")
    print("  - Font rendering (Helvetica)")
    print("  - Crisis graph label ('Peak-to-Trough Drawdown')")
    return 0


if __name__ == "__main__":
    sys.exit(main())

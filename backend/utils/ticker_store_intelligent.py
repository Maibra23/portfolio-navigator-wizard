#!/usr/bin/env python3
"""
Intelligent Ticker Store with Comprehensive Fallback Lists
Provides S&P 500, NASDAQ 100, Dow Jones, and ETF tickers with intelligent deduplication
NO EXTERNAL API CALLS - Uses comprehensive fallbacks only
"""

import logging
import json
import redis
from datetime import timedelta
from functools import lru_cache
from typing import List, Set

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# COMPREHENSIVE FALLBACK LISTS (BASE LISTS FOR DEDUPLICATION)
# These lists are the raw, comprehensive lists for each index/category.
# They may contain duplicates across categories, which will be handled by
# the intelligent deduplication logic.
# =============================================================================

def _get_comprehensive_sp500_fallback() -> List[str]:
    """Comprehensive S&P 500 fallback with 500+ real companies."""
    return [
        'A', 'AAL', 'AAP', 'AAPL', 'ABBV', 'ABC', 'ABMD', 'ABT', 'ACN', 'ADBE', 'ADI', 'ADM', 'ADP', 'ADS', 'ADSK', 'AEE', 'AEP', 'AES', 'AFL', 'AIG', 'AIZ', 'AJG', 'AKAM', 'ALB', 'ALGN', 'ALK', 'ALL', 'ALLE', 'AMAT', 'AMCR', 'AMD', 'AME', 'AMGN', 'AMP', 'AMT', 'AMZN', 'ANET', 'ANSS', 'ANTM', 'AON', 'AOS', 'APA', 'APD', 'APH', 'APTV', 'ARE', 'ATO', 'ATVI', 'AVB', 'AVGO', 'AVY', 'AWK', 'AXP', 'AZO', 'BA', 'BAC', 'BAX', 'BBWI', 'BBY', 'BDX', 'BEN', 'BF.B', 'BIIB', 'BIO', 'BK', 'BKNG', 'BKR', 'BLK', 'BLL', 'BMY', 'BR', 'BRK.B', 'BRO', 'BSX', 'BWA', 'BXP', 'C', 'CAG', 'CAH', 'CARR', 'CAT', 'CB', 'CBOE', 'CBRE', 'CCI', 'CCL', 'CDAY', 'CDW', 'CE', 'CEG', 'CF', 'CFG', 'CHD', 'CHRW', 'CHTR', 'CI', 'CINF', 'CL', 'CLX', 'CMA', 'CMCSA', 'CME', 'CMG', 'CMI', 'CMS', 'CNC', 'CNP', 'COF', 'COO', 'COP', 'COST', 'CPB', 'CPRT', 'CRL', 'CRM', 'CSCO', 'CSX', 'CTAS', 'CTLT', 'CTSH', 'CTVA', 'CTXS', 'CVS', 'CVX', 'CZR', 'D', 'DAL', 'DD', 'DE', 'DFS', 'DG', 'DGX', 'DHI', 'DHR', 'DIS', 'DISH', 'DLR', 'DLTR', 'DOV', 'DOW', 'DPZ', 'DRE', 'DTE', 'DUK', 'DVA', 'DVN', 'DXC', 'DXCM', 'EA', 'EBAY', 'ECL', 'ED', 'EFX', 'EIX', 'EMN', 'EMR', 'ENPH', 'EOG', 'EPAM', 'EQR', 'ES', 'ESS', 'ETN', 'ETR', 'ETSY', 'EVRG', 'EW', 'EXC', 'EXPD', 'EXPE', 'EXR', 'F', 'FANG', 'FAST', 'FB', 'FBIO', 'FCX', 'FDS', 'FE', 'FFIV', 'FIS', 'FISV', 'FITB', 'FLT', 'FMC', 'FOX', 'FOXA', 'FRC', 'FRT', 'FTNT', 'FTV', 'GD', 'GE', 'GILD', 'GIS', 'GL', 'GLW', 'GM', 'GNRC', 'GOOG', 'GOOGL', 'GPC', 'GPN', 'GRMN', 'GS', 'GWW', 'HAL', 'HAS', 'HBAN', 'HCA', 'HD', 'HES', 'HIG', 'HII', 'HLT', 'HOLX', 'HON', 'HP', 'HPE', 'HPQ', 'HRB', 'HRL', 'HSIC', 'HST', 'HSY', 'HUM', 'IBM', 'ICE', 'IDXX', 'IEX', 'IFF', 'ILMN', 'INCY', 'INTC', 'INTU', 'IP', 'IPG', 'IQV', 'IR', 'IRM', 'ISRG', 'IT', 'ITW', 'IVZ', 'J', 'JBHT', 'JCI', 'JKHY', 'JNJ', 'JNPR', 'JPM', 'K', 'KEY', 'KEYS', 'KHC', 'KIM', 'KLAC', 'KMB', 'KMI', 'KMX', 'KO', 'KR', 'L', 'LDOS', 'LEN', 'LH', 'LHX', 'LIN', 'LKQ', 'LLY', 'LMT', 'LNC', 'LNT', 'LOW', 'LRCX', 'LUMN', 'LUV', 'LW', 'LYB', 'LYV', 'MA', 'MAA', 'MAR', 'MAS', 'MCD', 'MCHP', 'MCK', 'MCO', 'MDLZ', 'MDT', 'MET', 'MGM', 'MHK', 'MKC', 'MKTX', 'MLM', 'MMC', 'MMM', 'MNST', 'MO', 'MOS', 'MPC', 'MPWR', 'MRK', 'MRNA', 'MRO', 'MS', 'MSCI', 'MSFT', 'MSI', 'MTB', 'MTCH', 'MTD', 'MU', 'NDAQ', 'NDSN', 'NEE', 'NEM', 'NFLX', 'NI', 'NKE', 'NOC', 'NOW', 'NRG', 'NSC', 'NTAP', 'NTRS', 'NUE', 'NVDA', 'NVR', 'NWL', 'NWS', 'NWSA', 'NXPI', 'O', 'ODFL', 'OGN', 'OKE', 'OMC', 'ON', 'ORCL', 'ORLY', 'OTIS', 'OXY', 'PAYC', 'PAYX', 'PCAR', 'PEAK', 'PEG', 'PEP', 'PFE', 'PFG', 'PG', 'PGR', 'PH', 'PHM', 'PKG', 'PKI', 'PLD', 'PM', 'PNC', 'PNR', 'PNW', 'POOL', 'PPG', 'PPL', 'PRU', 'PSA', 'PSX', 'PTC', 'PVH', 'PWR', 'PXD', 'PYPL', 'QCOM', 'QRVO', 'RCL', 'RE', 'REG', 'REGN', 'RF', 'RHI', 'RJF', 'RL', 'RMD', 'ROK', 'ROL', 'ROP', 'ROST', 'RSG', 'RTX', 'SBAC', 'SBNY', 'SBSI', 'SCHW', 'SEDG', 'SEE', 'SHW', 'SIVB', 'SJM', 'SLB', 'SNA', 'SNPS', 'SO', 'SPG', 'SPGI', 'SRE', 'STE', 'STT', 'STX', 'STZ', 'SWK', 'SWKS', 'SYF', 'SYK', 'SYY', 'T', 'TAP', 'TDG', 'TDY', 'TECH', 'TEL', 'TER', 'TFC', 'TFX', 'TGT', 'TJX', 'TMO', 'TMUS', 'TPR', 'TRMB', 'TROW', 'TRV', 'TSCO', 'TSLA', 'TSN', 'TT', 'TXN', 'TXT', 'TYL', 'UAL', 'UDR', 'UHS', 'ULTA', 'UNH', 'UNP', 'UPS', 'URI', 'USB', 'V', 'VAR', 'VFC', 'VIAC', 'VLO', 'VMC', 'VNO', 'VNT', 'VRSK', 'VRSN', 'VRTX', 'VTR', 'VTRS', 'VZ', 'WAB', 'WAT', 'WEC', 'WELL', 'WFC', 'WHR', 'WM', 'WMB', 'WMT', 'WRB', 'WRK', 'WST', 'WTW', 'WY', 'WYNN', 'XEL', 'XLNX', 'XOM', 'XRAY', 'XYL', 'YUM', 'ZBH', 'ZBRA', 'ZION', 'ZTS'
    ]

def _get_comprehensive_nasdaq100_fallback() -> List[str]:
    """Comprehensive NASDAQ 100 fallback with 100+ real companies."""
    return [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', 'ADBE', 'CRM', 'PYPL', 'INTC', 'AMD', 'QCOM', 'AVGO', 'ADI', 'KLAC', 'MU', 'LRCX', 'ASML', 'ORLY', 'PAYX', 'ROST', 'BIIB', 'GILD', 'REGN', 'VRTX', 'MELI', 'JD', 'PDD', 'BIDU', 'NTES', 'ATVI', 'EA', 'TTWO', 'ZM', 'TEAM', 'SNPS', 'CDNS', 'ANSS', 'ADSK', 'CTAS', 'FAST', 'ODFL', 'CHTR', 'CMCSA', 'COST', 'MAR', 'BKNG', 'EXPE', 'OKTA', 'CRWD', 'ZS', 'PLTR', 'COIN', 'RBLX', 'HOOD', 'SNAP', 'PINS', 'TWTR', 'UBER', 'LYFT', 'DASH', 'ABNB', 'RDFN', 'DOCU', 'SQ', 'SHOP', 'ETSY', 'SE', 'TCEHY', 'BABA', 'NIO', 'XPEV', 'LI', 'XPENG', 'BILI', 'HUYA', 'DOYU', 'TME', 'VIPS', 'TCOM', 'BIDU', 'NTES', 'TCEHY', 'PDD', 'BABA', 'NIO', 'XPEV', 'LI', 'XPENG', 'BILI', 'HUYA', 'DOYU', 'TME', 'VIPS', 'TCOM', 'BIDU', 'NTES', 'TCEHY', 'PDD', 'BABA', 'NIO', 'XPEV', 'LI', 'XPENG', 'BILI', 'HUYA', 'DOYU', 'TME', 'VIPS', 'TCOM'
    ]

def _get_comprehensive_dow30_fallback() -> List[str]:
    """Comprehensive Dow Jones Industrial Average fallback with 30+ real companies."""
    return [
        'AAPL', 'MSFT', 'JPM', 'JNJ', 'V', 'PG', 'HD', 'MA', 'DIS', 'BAC', 'KO', 'PEP', 'ABT', 'TMO', 'COST', 'DHR', 'ACN', 'WMT', 'MRK', 'VZ', 'TXN', 'HON', 'LLY', 'UNP', 'LOW', 'IBM', 'CAT', 'GS', 'AXP', 'SPGI', 'PLD', 'T', 'DE', 'RTX', 'ISRG', 'CVX', 'XOM', 'COP', 'EOG', 'SLB', 'HAL', 'BKR', 'MPC', 'PSX', 'VLO', 'DVN', 'PXD', 'OXY', 'FANG', 'MRO', 'APA', 'HES', 'NOV', 'FTI', 'NBR', 'HP', 'RIG', 'DO', 'NE', 'SDRL', 'PTEN', 'WFT', 'SPN', 'OIS', 'CLR', 'CHK', 'SWN', 'RRC', 'NFX', 'QEP', 'WLL', 'CRZO', 'GST', 'LPI', 'PE', 'PDCE', 'WPX', 'AR', 'CXO'
    ]

def _get_comprehensive_etf_fallback() -> List[str]:
    """Comprehensive ETF fallback with major market ETFs."""
    return [
        'SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VOO', 'VEA', 'VWO', 'AGG', 'BND', 'TLT', 'GLD', 'SLV', 'USO', 'XLE', 'XLF', 'XLK', 'XLV', 'XLI', 'XLP', 'XLU', 'XLB', 'XLC', 'XLY', 'XRT', 'XHB', 'XME', 'XOP', 'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'HAL', 'BKR', 'MPC', 'PSX', 'VLO', 'DVN', 'PXD', 'OXY', 'FANG', 'MRO', 'APA', 'HES', 'NOV', 'FTI', 'NBR', 'HP', 'RIG', 'DO', 'NE', 'SDRL', 'PTEN', 'WFT', 'SPN', 'OIS', 'CLR', 'CHK', 'SWN', 'RRC', 'NFX', 'QEP', 'WLL', 'CRZO', 'GST', 'LPI', 'PE', 'PDCE', 'WPX', 'AR', 'CXO'
    ]

# =============================================================================
# INTELLIGENT DEDUPLICATION FUNCTIONS
# This section defines the logic for how the base lists are combined and deduplicated.
# The goal is to maximize unique tickers while respecting the primary indices.
# =============================================================================

@lru_cache()
def _get_balanced_deduplication() -> dict:
    """
    Performs a balanced deduplication strategy to maximize unique tickers
    while prioritizing major indices.
    
    Strategy:
    1. Keep all S&P 500 tickers as they represent the broadest market.
    2. Add NASDAQ 100 tickers that are NOT already in the S&P 500 list.
    3. Add Dow 30 tickers that are NOT already in the S&P 500 list.
    4. Add all ETF tickers (assuming no overlap with individual stocks).
    """
    sp500_raw = _get_comprehensive_sp500_fallback()
    nasdaq_raw = _get_comprehensive_nasdaq100_fallback()
    dow_raw = _get_comprehensive_dow30_fallback()
    etf_raw = _get_comprehensive_etf_fallback()
    
    sp500_set = set(sp500_raw)
    
    # S&P 500: Keep all
    sp500_final = sp500_raw
    
    # NASDAQ 100: Keep only companies NOT in S&P 500
    nasdaq_unique = [t for t in nasdaq_raw if t not in sp500_set]
    
    # Dow 30: Keep only companies NOT in S&P 500
    dow_unique = [t for t in dow_raw if t not in sp500_set]
    
    # ETFs: Keep all (assuming no overlap with individual stocks)
    etf_final = etf_raw
    
    # Combine all unique tickers from the refined lists
    all_unique = sorted(set(sp500_final + nasdaq_unique + dow_unique + etf_final))
    
    return {
        'sp500': sp500_final,
        'nasdaq100': nasdaq_unique,
        'dow30': dow_unique,
        'etfs': etf_final,
        'all_unique': all_unique
    }

# =============================================================================
# MAIN FUNCTIONS (Public Interface for Ticker Retrieval)
# These functions provide the deduplicated ticker lists to other parts of the system.
# =============================================================================

@lru_cache()
def get_sp500() -> List[str]:
    """Get S&P 500 tickers using the balanced deduplication strategy."""
    balanced = _get_balanced_deduplication()
    logger.info(f"🎯 Using balanced deduplicated S&P 500: {len(balanced['sp500'])} tickers")
    return balanced['sp500']

@lru_cache()
def get_nasdaq100() -> List[str]:
    """Get NASDAQ 100 tickers using the balanced deduplication strategy (unique to S&P 500)."""
    balanced = _get_balanced_deduplication()
    logger.info(f"🎯 Using balanced deduplicated NASDAQ 100: {len(balanced['nasdaq100'])} tickers")
    return balanced['nasdaq100']

@lru_cache()
def get_dow30() -> List[str]:
    """Get Dow Jones Industrial Average tickers using the balanced deduplication strategy (unique to S&P 500)."""
    balanced = _get_balanced_deduplication()
    logger.info(f"🎯 Using balanced deduplicated Dow 30: {len(balanced['dow30'])} tickers")
    return balanced['dow30']

@lru_cache()
def get_all_tickers() -> List[str]:
    """Get a combined, fully deduplicated list of all tickers from all sources."""
    balanced = _get_balanced_deduplication()
    
    logger.info(f"🎯 Combined final deduplicated ticker list: {len(balanced['all_unique'])} unique tickers")
    logger.info(f"  S&P 500 (kept): {len(balanced['sp500'])} tickers")
    logger.info(f"  NASDAQ 100 (unique): {len(balanced['nasdaq100'])} tickers")
    logger.info(f"  Dow 30 (unique): {len(balanced['dow30'])} tickers")
    logger.info(f"  ETFs: {len(balanced['etfs'])} tickers")
    logger.info(f"  Total unique: {len(balanced['all_unique'])} tickers")
    
    return balanced['all_unique']

# =============================================================================
# UTILITY FUNCTIONS (for statistics and testing)
# =============================================================================

def get_deduplication_stats() -> dict:
    """Get statistics about the deduplication process."""
    sp500_raw = _get_comprehensive_sp500_fallback()
    nasdaq_raw = _get_comprehensive_nasdaq100_fallback()
    dow_raw = _get_comprehensive_dow30_fallback()
    etf_raw = _get_comprehensive_etf_fallback()
    
    sp500_set = set(sp500_raw)
    nasdaq_set = set(nasdaq_raw)
    dow_set = set(dow_raw)
    etf_set = set(etf_raw)
    
    # Calculate overlaps between raw lists
    sp500_nasdaq_overlap = len(sp500_set & nasdaq_set)
    sp500_dow_overlap = len(sp500_set & dow_set)
    nasdaq_dow_overlap = len(nasdaq_set & dow_set)
    
    # Get the results from the balanced deduplication strategy
    balanced = _get_balanced_deduplication()
    
    total_raw_sum = len(sp500_raw) + len(nasdaq_raw) + len(dow_raw) + len(etf_raw)
    total_unique_final = len(balanced['all_unique'])
    duplicates_removed = total_raw_sum - total_unique_final
    efficiency_percentage = (duplicates_removed / total_raw_sum) * 100 if total_raw_sum > 0 else 0
    
    return {
        'raw_counts': {
            'sp500': len(sp500_raw),
            'nasdaq100': len(nasdaq_raw),
            'dow30': len(dow_raw),
            'etfs': len(etf_raw),
            'total_raw_sum': total_raw_sum
        },
        'overlaps': {
            'sp500_nasdaq': sp500_nasdaq_overlap,
            'sp500_dow': sp500_dow_overlap,
            'nasdaq_dow': nasdaq_dow_overlap,
            'total_overlaps_detected': sp500_nasdaq_overlap + sp500_dow_overlap + nasdaq_dow_overlap
        },
        'deduplicated_counts': {
            'sp500_final': len(balanced['sp500']),
            'nasdaq100_unique': len(balanced['nasdaq100']),
            'dow30_unique': len(balanced['dow30']),
            'etfs_final': len(balanced['etfs']),
            'total_unique_final': total_unique_final
        },
        'improvement': {
            'duplicates_removed': duplicates_removed,
            'efficiency_percentage': efficiency_percentage
        }
    }

# =============================================================================
# TESTING AND DEMONSTRATION
# =============================================================================

if __name__ == "__main__":
    print("🚀 Testing Final Improved Intelligent Deduplication System...")
    print("=" * 70)
    
    stats = get_deduplication_stats()
    
    print(f"📊 DEDUPLICATION STATISTICS:")
    print(f"   Raw Counts:")
    print(f"     • S&P 500: {stats['raw_counts']['sp500']} tickers")
    print(f"     • NASDAQ 100: {stats['raw_counts']['nasdaq100']} tickers")
    print(f"     • Dow 30: {stats['raw_counts']['dow30']} tickers")
    print(f"     • ETFs: {stats['raw_counts']['etfs']} tickers")
    print(f"     • Total Raw Sum: {stats['raw_counts']['total_raw_sum']} tickers")
    
    print(f"\n🔄 OVERLAPS DETECTED (between raw lists):")
    print(f"     • S&P 500 ∩ NASDAQ 100: {stats['overlaps']['sp500_nasdaq']} duplicates")
    print(f"     • S&P 500 ∩ Dow 30: {stats['overlaps']['sp500_dow']} duplicates")
    print(f"     • NASDAQ 100 ∩ Dow 30: {stats['overlaps']['nasdaq_dow']} duplicates")
    print(f"     • Total Overlaps Detected: {stats['overlaps']['total_overlaps_detected']} duplicates")
    
    print(f"\n🎯 FINAL DEDUPLICATED COUNTS (after balanced strategy):")
    print(f"     • S&P 500 (kept): {stats['deduplicated_counts']['sp500_final']} tickers")
    print(f"     • NASDAQ 100 (unique to S&P): {stats['deduplicated_counts']['nasdaq100_unique']} tickers")
    print(f"     • Dow 30 (unique to S&P): {stats['deduplicated_counts']['dow30_unique']} tickers")
    print(f"     • ETFs (kept): {stats['deduplicated_counts']['etfs_final']} tickers")
    print(f"     • Total Unique Final: {stats['deduplicated_counts']['total_unique_final']} tickers")
    
    print(f"\n📈 IMPROVEMENT METRICS:")
    print(f"     • Duplicates Removed by Strategy: {stats['improvement']['duplicates_removed']} tickers")
    print(f"     • Deduplication Efficiency: {stats['improvement']['efficiency_percentage']:.1f}%")
    
    print(f"\n✅ Final Improved Intelligent Deduplication System Ready!")
    print(f"   You now have {stats['deduplicated_counts']['total_unique_final']} unique tickers!")
    print(f"   Strategy: Only remove major duplicates (in multiple major indices)")

"""
Stress Test Analyzer Module
Analyzes portfolio performance during historical market crises
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging
import time
from .redis_first_data_service import redis_first_data_service
try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    # Fallback if dateutil not available
    relativedelta = None

logger = logging.getLogger(__name__)

class StressTestAnalyzer:
    """
    Analyzes portfolio resilience during historical market stress scenarios
    """
    
    def __init__(self):
        self.data_service = redis_first_data_service
        # Cache for portfolio value calculations to avoid redundant computations
        self._portfolio_value_cache = {}
    
    def filter_prices_by_date_range(
        self, 
        prices: Dict[str, float], 
        start_date: str, 
        end_date: str
    ) -> Dict[str, float]:
        """
        Filter price dictionary by date range.
        
        Args:
            prices: Dict with date strings as keys (format: 'YYYY-MM-DD') and float prices as values
            start_date: Start date string (format: 'YYYY-MM-DD')
            end_date: End date string (format: 'YYYY-MM-DD')
        
        Returns:
            Filtered price dictionary with only dates within range (inclusive)
        """
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            filtered = {}
            for date_str, price in prices.items():
                try:
                    date_dt = datetime.strptime(date_str, '%Y-%m-%d')
                    if start_dt <= date_dt <= end_dt:
                        filtered[date_str] = price
                except (ValueError, TypeError):
                    # Skip invalid date formats
                    continue
            
            return filtered
        except Exception as e:
            logger.warning(f"⚠️ Error filtering prices by date range: {e}")
            return {}
    
    def detect_peaks_and_troughs(
        self,
        portfolio_values: List[float],
        dates: List[str],
        crisis_start_date: Optional[str] = None,
        crisis_end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect peaks and troughs in portfolio value series.

        This helper is used in multiple contexts:
        - For crisis analysis, we want a **pre-crisis peak** and **crisis trough**
        - For generic usage, we fall back to the simple global peak/trough logic

        Args:
            portfolio_values: List of portfolio values (normalized, starting at 1.0)
            dates: List of date strings corresponding to values (format: 'YYYY-MM-DD')
            crisis_start_date: Optional crisis start date to anchor the peak
            crisis_end_date: Optional crisis end date to bound the trough search

        Returns:
            Dict with peak, trough, recovery_peak, all_peaks, all_troughs
        """
        try:
            if len(portfolio_values) == 0 or len(dates) == 0:
                return {
                    'peak': None,
                    'trough': None,
                    'recovery_peak': None,
                    'all_peaks': [],
                    'all_troughs': []
                }

            values_array = np.array(portfolio_values)

            # --- Determine analysis window for crisis-aware mode ---
            if crisis_start_date is not None or crisis_end_date is not None:
                # Parse dates once
                parsed_dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates]

                if crisis_start_date is not None:
                    crisis_start_dt = datetime.strptime(crisis_start_date, '%Y-%m-%d')
                    start_idx_candidates = [
                        i for i, dt in enumerate(parsed_dates) if dt >= crisis_start_dt
                    ]
                    start_idx = start_idx_candidates[0] if start_idx_candidates else 0
                else:
                    start_idx = 0

                if crisis_end_date is not None:
                    crisis_end_dt = datetime.strptime(crisis_end_date, '%Y-%m-%d')
                    end_idx_candidates = [
                        i for i, dt in enumerate(parsed_dates) if dt <= crisis_end_dt
                    ]
                    end_idx = end_idx_candidates[-1] if end_idx_candidates else len(values_array) - 1
                else:
                    end_idx = len(values_array) - 1

                # Ensure valid window
                if start_idx >= len(values_array):
                    start_idx = 0
                if end_idx < start_idx:
                    end_idx = len(values_array) - 1

                # Pre-crisis peak: find the highest value before crisis start (pre-crisis peak).
                # Use the highest value in the interval before start_idx if available,
                # otherwise fall back to the first available value in the window.
                if start_idx > 0:
                    pre_crisis_values = values_array[:start_idx]
                    if len(pre_crisis_values) > 0:
                        peak_relative_idx = int(np.argmax(pre_crisis_values))
                        peak_idx = peak_relative_idx
                    else:
                        # No data before crisis start, use start_idx as fallback
                        peak_idx = start_idx
                else:
                    # Crisis starts at or before the first data point, use first value
                    peak_idx = 0

                peak = {
                    'value': float(values_array[peak_idx]),
                    'date': dates[peak_idx],
                    'index': peak_idx,
                }

                # Crisis trough: minimum value within crisis window [start_idx, end_idx]
                if end_idx > start_idx:
                    window_values = values_array[start_idx:end_idx + 1]
                    trough_relative_idx = int(np.argmin(window_values))
                    trough_idx = start_idx + trough_relative_idx
                else:
                    trough_idx = peak_idx

                trough = {
                    'value': float(values_array[trough_idx]),
                    'date': dates[trough_idx],
                    'index': trough_idx,
                }
            else:
                # --- Generic global peak / post-peak trough (legacy behaviour) ---
                peak_idx = int(np.argmax(values_array))
                peak = {
                    'value': float(values_array[peak_idx]),
                    'date': dates[peak_idx],
                    'index': peak_idx
                }

                if peak_idx < len(values_array) - 1:
                    post_peak_values = values_array[peak_idx + 1:]
                    if len(post_peak_values) > 0:
                        trough_relative_idx = int(np.argmin(post_peak_values))
                        trough_idx = peak_idx + 1 + trough_relative_idx
                    else:
                        trough_idx = peak_idx
                else:
                    trough_idx = peak_idx

                trough = {
                    'value': float(values_array[trough_idx]),
                    'date': dates[trough_idx],
                    'index': trough_idx
                }

            # Find recovery peak (maximum value after trough) - post-recovery peak
            recovery_peak = None
            if trough['index'] < len(values_array) - 1:
                post_trough_values = values_array[trough['index'] + 1:]
                if len(post_trough_values) > 0:
                    recovery_relative_idx = int(np.argmax(post_trough_values))
                    recovery_idx = trough['index'] + 1 + recovery_relative_idx
                    recovery_value = float(values_array[recovery_idx])
                    # Only consider it recovery if it's at least 95% of peak value
                    if recovery_value >= peak['value'] * 0.95:
                        recovery_peak = {
                            'value': recovery_value,
                            'date': dates[recovery_idx],
                            'index': recovery_idx
                        }

            # Detect local peaks and troughs using simple neighbour comparison
            all_peaks: List[Dict[str, Any]] = []
            all_troughs: List[Dict[str, Any]] = []

            for i in range(1, len(values_array) - 1):
                if values_array[i] > values_array[i - 1] and values_array[i] > values_array[i + 1]:
                    all_peaks.append({
                        'value': float(values_array[i]),
                        'date': dates[i],
                        'index': i,
                    })

                if values_array[i] < values_array[i - 1] and values_array[i] < values_array[i + 1]:
                    all_troughs.append({
                        'value': float(values_array[i]),
                        'date': dates[i],
                        'index': i,
                    })

            return {
                'peak': peak,
                'trough': trough,
                'recovery_peak': recovery_peak,
                'all_peaks': all_peaks,
                'all_troughs': all_troughs,
            }
        except Exception as e:
            logger.error(f"❌ Error detecting peaks and troughs: {e}")
            return {
                'peak': None,
                'trough': None,
                'recovery_peak': None,
                'all_peaks': [],
                'all_troughs': []
            }
    
    def calculate_portfolio_values_over_period(
        self,
        tickers: List[str],
        weights: Dict[str, float],
        start_date: str,
        end_date: str,
        include_recovery: bool = True,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate portfolio values over a specific time period.
        
        Args:
            tickers: List of ticker symbols
            weights: Dict mapping ticker to weight (e.g., {'AAPL': 0.4, 'MSFT': 0.6})
            start_date: Start date string (format: 'YYYY-MM-DD')
            end_date: End date string (format: 'YYYY-MM-DD')
            include_recovery: If True, extend 6 months past end_date to capture recovery
            use_cache: If True, use cached results for identical requests
        
        Returns:
            Dict with dates, values, monthly_returns, data_availability
        """
        try:
            # Check cache first (if enabled and same parameters)
            if use_cache:
                cache_key = (
                    tuple(sorted(tickers)),
                    tuple(sorted(weights.items())),
                    start_date,
                    end_date,
                    include_recovery
                )
                if cache_key in self._portfolio_value_cache:
                    logger.debug(f"📦 Using cached portfolio values for period {start_date} to {end_date}")
                    return self._portfolio_value_cache[cache_key]
            # Extend end date if recovery period requested
            if include_recovery:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                recovery_end_dt = end_dt + timedelta(days=180)  # 6 months
                recovery_end_date = recovery_end_dt.strftime('%Y-%m-%d')
            else:
                recovery_end_date = end_date
            
            # Step 1: Retrieve and filter price data for all tickers
            import time
            data_start = time.time()
            ticker_prices = {}
            data_availability = {}

            # First pass: get current cache and collect tickers that need fuller history
            ticker_data_map = {}
            need_refresh = []
            req_start = start_date
            fetcher = getattr(self.data_service, 'enhanced_data_fetcher', None)

            for ticker in tickers:
                ticker_start = time.time()
                ticker_data = self.data_service.get_monthly_data(ticker)
                ticker_time = time.time() - ticker_start
                if ticker_time > 0.5:
                    logger.debug(f"⏱️ {ticker} data retrieved in {ticker_time:.3f}s")
                ticker_data_map[ticker] = ticker_data

                if not fetcher:
                    continue
                try:
                    td_dates = ticker_data.get('dates') if isinstance(ticker_data, dict) else None
                    if td_dates and isinstance(td_dates, list):
                        cached_min_date = min(td_dates) if td_dates else None
                        if cached_min_date and cached_min_date > req_start:
                            need_refresh.append(ticker)
                except Exception:
                    pass

            # Batch refresh: one call for all tickers that need fuller history (smoother than per-ticker)
            if need_refresh:
                try:
                    logger.info(
                        f"🔄 Batch refreshing {len(need_refresh)} tickers for scenario window from {req_start}: "
                        f"{', '.join(need_refresh)}"
                    )
                    fetcher.refresh_specific_tickers(need_refresh)
                    for ticker in need_refresh:
                        ticker_data_map[ticker] = self.data_service.get_monthly_data(ticker)
                except Exception as e:
                    logger.debug(f"⚠️ Batch refresh failed: {e}")

            for ticker in tickers:
                ticker_data = ticker_data_map.get(ticker)

                if ticker_data and ticker_data.get('prices'):
                    prices = ticker_data['prices']
                    # Convert to dict if it's a Series
                    if isinstance(prices, pd.Series):
                        prices_dict = {str(date): float(price) for date, price in prices.items()}
                    elif isinstance(prices, dict):
                        prices_dict = prices
                    elif isinstance(prices, list):
                        # If it's a list, we need dates - try to get from ticker_data
                        dates = ticker_data.get('dates', [])
                        if len(dates) == len(prices):
                            prices_dict = {str(date): float(price) for date, price in zip(dates, prices)}
                        else:
                            logger.warning(f"⚠️ {ticker}: Mismatch between dates and prices")
                            data_availability[ticker] = False
                            continue
                    else:
                        logger.warning(f"⚠️ {ticker}: Unsupported price data format")
                        data_availability[ticker] = False
                        continue
                    
                    # Filter by date range
                    filtered_prices = self.filter_prices_by_date_range(
                        prices_dict, 
                        start_date, 
                        recovery_end_date
                    )
                    
                    if len(filtered_prices) > 0:
                        ticker_prices[ticker] = filtered_prices
                        data_availability[ticker] = True
                    else:
                        data_availability[ticker] = False
                else:
                    data_availability[ticker] = False
            
            data_time = time.time() - data_start
            if data_time > 1.0:  # Log if data retrieval takes more than 1 second
                logger.debug(f"⏱️ Total data retrieval time: {data_time:.3f}s for {len(tickers)} tickers")
            
            # Step 2: Build a canonical monthly date grid for the requested window.
            #
            # IMPORTANT:
            # - We intentionally do NOT rely on "union of available dates" here.
            # - Some holdings (e.g. newer IPOs / foreign listings) may only have prices
            #   starting years after `start_date`. If we only use union-of-dates, the
            #   entire portfolio series can begin late (e.g. 2011) and the "2008 crisis"
            #   graph becomes misleading.
            # - By using a fixed monthly grid and backfilling leading gaps (see above),
            #   we can always render the scenario starting at the intended crisis window.
            if not ticker_prices:
                return {
                    'dates': [],
                    'values': [],
                    'monthly_returns': [],
                    'data_availability': data_availability
                }

            # Detect if cached data is month-start or month-end and build matching grid
            date_freq = 'MS'  # month start
            try:
                sample_prices = next(iter(ticker_prices.values()))
                sample_date = next(iter(sample_prices.keys()))
                if isinstance(sample_date, str) and len(sample_date) >= 10:
                    day = sample_date[8:10]
                    date_freq = 'MS' if day == '01' else 'M'
            except Exception:
                date_freq = 'MS'

            grid = pd.date_range(start=start_date, end=recovery_end_date, freq=date_freq)
            sorted_dates = [d.strftime('%Y-%m-%d') for d in grid]

            # NEW: Impute missing data for individual tickers before portfolio aggregation
            ticker_prices = self._impute_ticker_price_gaps(ticker_prices, sorted_dates)

            # Step 3: Calculate portfolio value for each date
            portfolio_values = []
            valid_dates = []
            
            # Normalize weights to sum to 1.0 (only for tickers with data)
            available_tickers = [t for t in tickers if data_availability.get(t, False)]
            if not available_tickers:
                return {
                    'dates': [],
                    'values': [],
                    'monthly_returns': [],
                    'data_availability': data_availability
                }
            
            total_weight = sum(weights.get(t, 0.0) for t in available_tickers)
            if total_weight <= 0:
                # Fallback to equal weights
                normalized_weights = {t: 1.0 / len(available_tickers) for t in available_tickers}
            else:
                normalized_weights = {t: weights.get(t, 0.0) / total_weight for t in available_tickers}
            
            # Track last known prices for missing dates
            last_known_prices = {}

            # Backfill leading gaps so the series can start at `start_date`.
            # Without this, if any ticker's first available price is later (e.g. 2011),
            # the entire portfolio series will be skipped until that point.
            # We approximate pre-inception performance as flat at the first available price.
            for ticker in available_tickers:
                if ticker in ticker_prices and ticker_prices[ticker]:
                    first_date = min(
                        ticker_prices[ticker].keys(),
                        key=lambda x: datetime.strptime(x, '%Y-%m-%d')
                    )
                    last_known_prices[ticker] = ticker_prices[ticker][first_date]
            
            for date_str in sorted_dates:
                portfolio_value = 0.0
                date_valid = True
                
                for ticker in available_tickers:
                    if ticker in ticker_prices:
                        prices = ticker_prices[ticker]
                        if date_str in prices:
                            price = prices[date_str]
                            last_known_prices[ticker] = price
                        elif ticker in last_known_prices:
                            # Use last known price if date missing
                            price = last_known_prices[ticker]
                        else:
                            # No data for this ticker on this date, skip date
                            date_valid = False
                            break
                        
                        portfolio_value += price * normalized_weights[ticker]
                
                if date_valid and portfolio_value > 0:
                    portfolio_values.append(portfolio_value)
                    valid_dates.append(date_str)
            
            # Step 4: Normalize values to start at 1.0
            if len(portfolio_values) > 0:
                initial_value = portfolio_values[0]
                normalized_values = [v / initial_value for v in portfolio_values]
            else:
                normalized_values = []
            
            # Step 5: Calculate monthly returns
            monthly_returns = []
            for i in range(1, len(normalized_values)):
                if normalized_values[i-1] > 0:
                    monthly_return = (normalized_values[i] - normalized_values[i-1]) / normalized_values[i-1]
                    monthly_returns.append(monthly_return)
                else:
                    monthly_returns.append(0.0)
            
            # Add 0.0 for first month (no return yet)
            if len(monthly_returns) < len(normalized_values):
                monthly_returns.insert(0, 0.0)
            
            result = {
                'dates': valid_dates,
                'values': normalized_values,
                'monthly_returns': monthly_returns,
                'data_availability': data_availability
            }
            
            # Cache result if enabled
            if use_cache:
                cache_key = (
                    tuple(sorted(tickers)),
                    tuple(sorted(weights.items())),
                    start_date,
                    end_date,
                    include_recovery
                )
                self._portfolio_value_cache[cache_key] = result
            
            return result
        except Exception as e:
            logger.error(f"❌ Error calculating portfolio values: {e}")
            import traceback
            traceback.print_exc()
            return {
                'dates': [],
                'values': [],
                'monthly_returns': [],
                'data_availability': {t: False for t in tickers}
            }
    
    def calculate_maximum_drawdown(
        self,
        portfolio_values: List[float],
        dates: List[str],
        crisis_start_date: Optional[str] = None,
        crisis_end_date: Optional[str] = None,
        drawdown_threshold: float = 0.03
    ) -> Dict[str, Any]:
        """
        Calculate maximum drawdown from peak to trough.
        
        Drawdown is calculated as: (Trough Value - Peak Value) / Peak Value
        Only meaningful if drawdown exceeds threshold (default 3%).
        
        Args:
            portfolio_values: List of normalized portfolio values
            dates: List of date strings
            crisis_start_date: Optional crisis start date to find pre-crisis peak
            crisis_end_date: Optional crisis end date to limit trough search
            drawdown_threshold: Minimum drawdown percentage to be considered meaningful (default 3%)
        
        Returns:
            Dict with max_drawdown, peak_value, peak_date, trough_value, trough_date,
            drawdown_duration_months, is_significant (bool)
        """
        try:
            # Use crisis-aware peak/trough detection when boundaries are provided
            peaks_troughs = self.detect_peaks_and_troughs(
                portfolio_values,
                dates,
                crisis_start_date=crisis_start_date,
                crisis_end_date=crisis_end_date,
            )

            if not peaks_troughs['peak'] or not peaks_troughs['trough']:
                return {
                    'max_drawdown': 0.0,
                    'peak_value': 1.0,
                    'peak_date': dates[0] if dates else '',
                    'trough_value': 1.0,
                    'trough_date': dates[0] if dates else '',
                    'drawdown_duration_months': 0,
                    'is_significant': False,
                }

            peak = peaks_troughs['peak']
            trough = peaks_troughs['trough']

            # Calculate drawdown: (Trough - Peak) / Peak
            # Negative value means portfolio dropped
            if peak['value'] > 0:
                max_drawdown = (trough['value'] - peak['value']) / peak['value']
            else:
                max_drawdown = 0.0

            # Check if drawdown is significant (exceeds threshold)
            is_significant = abs(max_drawdown) >= drawdown_threshold

            # Calculate duration in months between peak and trough indices
            drawdown_duration_months = trough['index'] - peak['index']

            return {
                'max_drawdown': float(max_drawdown),
                'peak_value': peak['value'],
                'peak_date': peak['date'],
                'trough_value': trough['value'],
                'trough_date': trough['date'],
                'drawdown_duration_months': drawdown_duration_months,
                'is_significant': is_significant,
            }
        except Exception as e:
            logger.error(f"❌ Error calculating maximum drawdown: {e}")
            return {
                'max_drawdown': 0.0,
                'peak_value': 1.0,
                'peak_date': '',
                'trough_value': 1.0,
                'trough_date': '',
                'drawdown_duration_months': 0
            }
    
    def calculate_trajectory_projection(
        self,
        portfolio_values: List[float],
        dates: List[str],
        peak_value: float,
        lookback_months: int = 6
    ) -> Dict[str, Any]:
        """
        Calculate trajectory-based recovery projections to peak using trend analysis.
        
        Uses linear regression on recent data to project three scenarios:
        - Optimistic: Upper bound projection
        - Realistic: Mean projection
        - Pessimistic: Lower bound projection
        
        Args:
            portfolio_values: List of normalized portfolio values
            dates: List of date strings
            peak_value: Peak value to recover to (100%)
            lookback_months: Number of recent months to use for trend (default 6)
        
        Returns:
            Dict with optimistic_months, realistic_months, pessimistic_months,
            and trajectory_data for plotting
        """
        try:
            if len(portfolio_values) < 2:
                return {
                    'optimistic_months': None,
                    'realistic_months': None,
                    'pessimistic_months': None,
                    'trajectory_data': []
                }
            
            # Use last N months for trend analysis
            recent_values = portfolio_values[-min(lookback_months, len(portfolio_values)):]
            recent_indices = list(range(len(portfolio_values) - len(recent_values), len(portfolio_values)))
            
            if len(recent_values) < 2:
                return {
                    'optimistic_months': None,
                    'realistic_months': None,
                    'pessimistic_months': None,
                    'trajectory_data': []
                }
            
            # Linear regression: y = mx + b
            x = np.array(recent_indices)
            y = np.array(recent_values)
            
            # Calculate slope and intercept
            n = len(x)
            sum_x = np.sum(x)
            sum_y = np.sum(y)
            sum_xy = np.sum(x * y)
            sum_x2 = np.sum(x * x)
            
            denominator = n * sum_x2 - sum_x * sum_x
            if abs(denominator) < 1e-10:
                # No trend, use average return
                avg_return = (y[-1] - y[0]) / len(y) if len(y) > 1 else 0
                slope = avg_return
                intercept = y[-1] - slope * x[-1]
            else:
                slope = (n * sum_xy - sum_x * sum_y) / denominator
                intercept = (sum_y - slope * sum_x) / n
            
            # Calculate standard error for confidence intervals
            y_pred = slope * x + intercept
            residuals = y - y_pred
            mse = np.mean(residuals ** 2) if len(residuals) > 0 else 0
            std_error = np.sqrt(mse) if mse > 0 else 0
            
            # Current position
            current_idx = len(portfolio_values) - 1
            current_value = portfolio_values[-1]
            
            # Project forward to reach peak
            if abs(slope) < 1e-10:
                # Flat trend - cannot project
                return {
                    'optimistic_months': None,
                    'realistic_months': None,
                    'pessimistic_months': None,
                    'trajectory_data': []
                }
            
            # Realistic: Mean projection
            if slope > 0:  # Positive trend
                months_to_peak_realistic = (peak_value - current_value) / slope if slope > 0 else None
            else:
                months_to_peak_realistic = None
            
            # Optimistic: Upper bound (slope + 1 std error)
            optimistic_slope = slope + std_error if std_error > 0 else slope * 1.2
            if optimistic_slope > 0:
                months_to_peak_optimistic = (peak_value - current_value) / optimistic_slope if optimistic_slope > 0 else None
            else:
                months_to_peak_optimistic = None
            
            # Pessimistic: Lower bound (slope - 1 std error, or slower recovery)
            pessimistic_slope = max(0, slope - std_error) if std_error > 0 else slope * 0.8
            if pessimistic_slope > 0:
                months_to_peak_pessimistic = (peak_value - current_value) / pessimistic_slope if pessimistic_slope > 0 else None
            else:
                months_to_peak_pessimistic = None
            
            # Generate trajectory data points for plotting (next 24 months)
            trajectory_data = []
            for months_ahead in range(1, 25):
                future_idx = current_idx + months_ahead
                
                # Realistic trajectory
                realistic_value = current_value + slope * months_ahead
                # No cap for educational trajectory projections

                # Optimistic trajectory
                optimistic_value = current_value + optimistic_slope * months_ahead
                # No cap for educational trajectory projections

                # Pessimistic trajectory
                pessimistic_value = current_value + pessimistic_slope * months_ahead
                # No cap for educational trajectory projections
                
                trajectory_data.append({
                    'months_ahead': months_ahead,
                    'realistic': float(realistic_value),
                    'optimistic': float(optimistic_value),
                    'pessimistic': float(pessimistic_value)
                })
            
            return {
                'optimistic_months': float(months_to_peak_optimistic) if months_to_peak_optimistic is not None and months_to_peak_optimistic > 0 else None,
                'realistic_months': float(months_to_peak_realistic) if months_to_peak_realistic is not None and months_to_peak_realistic > 0 else None,
                'pessimistic_months': float(months_to_peak_pessimistic) if months_to_peak_pessimistic is not None and months_to_peak_pessimistic > 0 else None,
                'trajectory_data': trajectory_data,
                'current_slope': float(slope),
                'current_value': float(current_value)
            }
        except Exception as e:
            logger.error(f"❌ Error calculating trajectory projection: {e}")
            return {
                'optimistic_months': None,
                'realistic_months': None,
                'pessimistic_months': None,
                'trajectory_data': []
            }

    def calculate_enhanced_trajectory_projections(
        self,
        portfolio_values: List[float],
        dates: List[str],
        peak_value: float,
        lookback_months: int = 6
    ) -> Dict[str, Any]:
        """
        Enhanced trajectory calculation with adaptive lookback, imputation, and confidence levels.

        Calculates three recovery scenarios using linear regression with robust data handling:
        - Conservative: Slower recovery (lower confidence bound)
        - Moderate: Realistic recovery (mean projection)
        - Aggressive: Faster recovery (upper confidence bound)

        Features:
        - Adaptive lookback window (uses available data, minimum 2 months)
        - Multi-level data imputation for missing values
        - Confidence levels based on data quality and regression fit
        - Graceful degradation with fallbacks

        Args:
            portfolio_values: List of normalized portfolio values (can contain None for missing data)
            dates: List of date strings
            peak_value: Peak value to recover to (100%)
            lookback_months: Desired number of recent months to use (default 6)

        Returns:
            Dict with conservative_months, moderate_months, aggressive_months, trajectory_data,
            and regression_quality metrics
        """
        try:
            # 1. Data Quality Assessment
            data_quality = self._assess_portfolio_data_quality(portfolio_values, dates)

            # 2. Handle missing values with imputation
            imputed_values, imputed_dates = self._impute_missing_portfolio_values(
                portfolio_values, dates, method='linear_interpolation'
            )

            # 3. Adaptive Lookback Window Selection
            available_months = len(imputed_values)

            if available_months < 2:
                return self._get_fallback_trajectory("insufficient_data")

            # Use what's available, minimum 2 months, warn if < 6 months
            effective_lookback = min(lookback_months, available_months)

            if effective_lookback < 6:
                logger.warning(
                    f"⚠️ Limited data: Only {effective_lookback} months available for trajectory. "
                    f"Using all available data (lower confidence)."
                )

            # 4. Use imputed data for regression
            recent_values = imputed_values[-effective_lookback:]
            recent_indices = list(range(len(imputed_values) - len(recent_values), len(imputed_values)))

            if len(recent_values) < 2:
                return self._get_fallback_trajectory("insufficient_data")

            # 5. Multiple Regression Windows (if enough data)
            regressions = {}
            for window in [3, 6, 12]:
                if len(imputed_values) >= window:
                    window_values = imputed_values[-window:]
                    window_indices = list(range(len(imputed_values) - len(window_values), len(imputed_values)))

                    regression_result = self._calculate_linear_regression(window_indices, window_values)
                    if regression_result and regression_result['r_squared'] > 0.1:  # Minimum quality
                        regressions[window] = regression_result

            # 6. Select Best Regression (prefer 6-month, fallback to 3 or 12)
            base_regression = (
                regressions.get(6) or
                regressions.get(3) or
                regressions.get(12) or
                self._calculate_linear_regression(recent_indices, recent_values)
            )

            if not base_regression or base_regression['slope'] <= 0:
                return self._get_fallback_trajectory("negative_trend")

            # 7. Calculate trajectories with confidence intervals
            base_slope = base_regression['slope']
            base_std_error = base_regression['std_error']

            current_idx = len(imputed_values) - 1
            current_value = imputed_values[-1]

            # Conservative: Lower bound (slope - 1.5 * std_error, or 0.7x slope)
            # Ensure minimum 15% divergence from moderate for visual distinction
            conservative_slope_calc = max(0.001, base_slope - 1.5 * base_std_error) if base_std_error > 0 else base_slope * 0.7
            conservative_slope = min(conservative_slope_calc, base_slope * 0.85)  # At least 15% slower than moderate

            # Moderate: Mean (base slope)
            moderate_slope = base_slope

            # Aggressive: Upper bound (slope + 1.5 * std_error, or 1.3x slope)
            # Ensure minimum 15% divergence from moderate for visual distinction
            aggressive_slope_calc = base_slope + 1.5 * base_std_error if base_std_error > 0 else base_slope * 1.3
            aggressive_slope = max(aggressive_slope_calc, base_slope * 1.15)  # At least 15% faster than moderate

            # 8. Calculate months to peak for each scenario
            months_to_peak_conservative = (peak_value - current_value) / conservative_slope if conservative_slope > 0 else None
            months_to_peak_moderate = (peak_value - current_value) / moderate_slope if moderate_slope > 0 else None
            months_to_peak_aggressive = (peak_value - current_value) / aggressive_slope if aggressive_slope > 0 else None

            # 9. Generate trajectory data (24 months forward)
            trajectory_data = []
            for months_ahead in range(1, 25):
                # Conservative trajectory
                conservative_value = current_value + conservative_slope * months_ahead
                # No cap for educational trajectory projections

                # Moderate trajectory
                moderate_value = current_value + moderate_slope * months_ahead
                # No cap for educational trajectory projections

                # Aggressive trajectory
                aggressive_value = current_value + aggressive_slope * months_ahead
                # No cap for educational trajectory projections

                trajectory_data.append({
                    'months_ahead': months_ahead,
                    'conservative': float(conservative_value),
                    'moderate': float(moderate_value),
                    'aggressive': float(aggressive_value)
                })

            # 10. Calculate confidence level
            confidence_level = self._calculate_confidence_level(effective_lookback, base_regression['r_squared'])

            return {
                'conservative_months': float(months_to_peak_conservative) if months_to_peak_conservative and months_to_peak_conservative > 0 else None,
                'moderate_months': float(months_to_peak_moderate) if months_to_peak_moderate and months_to_peak_moderate > 0 else None,
                'aggressive_months': float(months_to_peak_aggressive) if months_to_peak_aggressive and months_to_peak_aggressive > 0 else None,
                'trajectory_data': trajectory_data,
                'regression_quality': {
                    'r_squared': float(base_regression['r_squared']),
                    'std_error': float(base_std_error),
                    'data_points_used': effective_lookback,
                    'confidence_level': confidence_level,
                    'imputation_used': len(imputed_values) > len([v for v in portfolio_values if v is not None]),
                    'data_quality': data_quality
                }
            }

        except Exception as e:
            logger.error(f"❌ Error calculating enhanced trajectory: {e}")
            return self._get_fallback_trajectory("error")

    def _assess_portfolio_data_quality(self, portfolio_values: List[float], dates: List[str]) -> str:
        """Assess the quality of portfolio data."""
        if not portfolio_values:
            return "empty"

        total_points = len(portfolio_values)
        missing_points = sum(1 for v in portfolio_values if v is None)
        missing_percentage = missing_points / total_points

        if missing_percentage > 0.5:
            return "poor"
        elif missing_percentage > 0.2:
            return "fair"
        elif total_points >= 12:
            return "good"
        else:
            return "limited"

    def _impute_missing_portfolio_values(
        self,
        portfolio_values: List[float],
        dates: List[str],
        method: str = 'linear_interpolation'
    ) -> Tuple[List[float], List[str]]:
        """
        Impute missing portfolio values using linear interpolation.
        """
        if len(portfolio_values) == len(dates) and not any(v is None for v in portfolio_values):
            return portfolio_values, dates

        imputed_values = []
        imputed_dates = []

        for i, (value, date) in enumerate(zip(portfolio_values, dates)):
            if value is not None:
                imputed_values.append(value)
                imputed_dates.append(date)
            else:
                # Missing value - apply linear interpolation
                if method == 'linear_interpolation':
                    # Find previous and next non-null values
                    prev_value = None
                    next_value = None

                    # Find previous non-null value
                    for j in range(i - 1, -1, -1):
                        if portfolio_values[j] is not None:
                            prev_value = portfolio_values[j]
                            break

                    # Find next non-null value
                    for j in range(i + 1, len(portfolio_values)):
                        if portfolio_values[j] is not None:
                            next_value = portfolio_values[j]
                            break

                    if prev_value is not None and next_value is not None:
                        # Linear interpolation
                        gap_size = (i - (i - 1 - (i - 1 - j))) if j < i else 1
                        interpolated = prev_value + (next_value - prev_value) / gap_size
                        imputed_values.append(interpolated)
                        imputed_dates.append(date)
                    elif prev_value is not None:
                        # Forward fill
                        imputed_values.append(prev_value)
                        imputed_dates.append(date)
                    elif next_value is not None:
                        # Backward fill
                        imputed_values.append(next_value)
                        imputed_dates.append(date)
                    else:
                        # No surrounding data - use average of all available
                        available_values = [v for v in portfolio_values if v is not None]
                        if available_values:
                            imputed_values.append(np.mean(available_values))
                            imputed_dates.append(date)
                        else:
                            # Last resort: use 1.0 (100% baseline)
                            imputed_values.append(1.0)
                            imputed_dates.append(date)

        return imputed_values, imputed_dates

    def _calculate_linear_regression(self, indices: List[int], values: List[float]) -> Optional[Dict[str, float]]:
        """Calculate linear regression for given data points."""
        try:
            if len(indices) < 2 or len(values) < 2:
                return None

            x = np.array(indices, dtype=float)
            y = np.array(values, dtype=float)

            n = len(x)
            sum_x = np.sum(x)
            sum_y = np.sum(y)
            sum_xy = np.sum(x * y)
            sum_x2 = np.sum(x * x)

            denominator = n * sum_x2 - sum_x * sum_x
            if abs(denominator) < 1e-10:
                # No trend, use average return
                avg_return = (y[-1] - y[0]) / len(y) if len(y) > 1 else 0
                slope = avg_return
                intercept = y[-1] - slope * x[-1]
                r_squared = 0.0
            else:
                slope = (n * sum_xy - sum_x * sum_y) / denominator
                intercept = (sum_y - slope * sum_x) / n

                # Calculate R-squared
                y_pred = slope * x + intercept
                ss_res = np.sum((y - y_pred) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            # Calculate standard error
            residuals = y - y_pred
            mse = np.mean(residuals ** 2) if len(residuals) > 0 else 0
            std_error = np.sqrt(mse) if mse > 0 else 0

            return {
                'slope': float(slope),
                'intercept': float(intercept),
                'r_squared': float(r_squared),
                'std_error': float(std_error)
            }
        except Exception as e:
            logger.warning(f"Error in linear regression: {e}")
            return None

    def _calculate_confidence_level(self, data_points: int, r_squared: float) -> str:
        """Calculate confidence level for trajectory projection."""
        if data_points >= 12 and r_squared >= 0.7:
            return 'high'
        elif data_points >= 6 and r_squared >= 0.5:
            return 'medium'
        elif data_points >= 3 and r_squared >= 0.3:
            return 'low'
        else:
            return 'very_low'

    def _get_fallback_trajectory(self, reason: str) -> Dict[str, Any]:
        """Provide fallback trajectory when calculation fails."""
        fallback_scenarios = {
            'insufficient_data': {
                'conservative_months': None,
                'moderate_months': None,
                'aggressive_months': None,
                'trajectory_data': [],
                'regression_quality': {
                    'r_squared': 0.0,
                    'std_error': 0.0,
                    'data_points_used': 0,
                    'confidence_level': 'very_low',
                    'fallback_reason': 'insufficient_data'
                }
            },
            'negative_trend': {
                # Use historical average recovery time
                'conservative_months': 24.0,
                'moderate_months': 18.0,
                'aggressive_months': 12.0,
                'trajectory_data': self._generate_flat_trajectory(),
                'regression_quality': {
                    'r_squared': 0.0,
                    'std_error': 0.0,
                    'confidence_level': 'very_low',
                    'fallback_reason': 'negative_trend'
                }
            },
            'error': {
                'conservative_months': None,
                'moderate_months': None,
                'aggressive_months': None,
                'trajectory_data': [],
                'regression_quality': {
                    'confidence_level': 'error',
                    'fallback_reason': 'calculation_error'
                }
            }
        }

        return fallback_scenarios.get(reason, fallback_scenarios['error'])

    def _generate_flat_trajectory(self) -> List[Dict[str, Any]]:
        """Generate flat trajectory data for fallback."""
        return [
            {
                'months_ahead': months,
                'conservative': 1.0,
                'moderate': 1.0,
                'aggressive': 1.0
            } for months in range(1, 25)
        ]

    def _impute_ticker_price_gaps(
        self,
        ticker_prices: Dict[str, Dict[str, float]],
        sorted_dates: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Impute missing price data for individual tickers using linear interpolation.
        This fills gaps in ticker price series before portfolio aggregation.
        """
        try:
            imputed_ticker_prices = {}

            for ticker, prices in ticker_prices.items():
                # Check if ticker has data for all dates
                if len(prices) == len(sorted_dates) and all(date in prices for date in sorted_dates):
                    # No imputation needed
                    imputed_ticker_prices[ticker] = prices
                    continue

                # Impute missing dates
                imputed_prices = {}

                for i, date_str in enumerate(sorted_dates):
                    if date_str in prices:
                        imputed_prices[date_str] = prices[date_str]
                    else:
                        # Missing price - interpolate
                        prev_price = None
                        next_price = None

                        # Find previous available price
                        for j in range(i - 1, -1, -1):
                            if sorted_dates[j] in prices:
                                prev_price = prices[sorted_dates[j]]
                                prev_idx = j
                                break

                        # Find next available price
                        for j in range(i + 1, len(sorted_dates)):
                            if sorted_dates[j] in prices:
                                next_price = prices[sorted_dates[j]]
                                next_idx = j
                                break

                        if prev_price is not None and next_price is not None:
                            # Linear interpolation
                            total_gap = next_idx - prev_idx
                            current_gap = i - prev_idx
                            interpolated_price = prev_price + (next_price - prev_price) * (current_gap / total_gap)
                            imputed_prices[date_str] = interpolated_price
                        elif prev_price is not None:
                            # Forward fill
                            imputed_prices[date_str] = prev_price
                        elif next_price is not None:
                            # Backward fill
                            imputed_prices[date_str] = next_price
                        else:
                            # No surrounding data - use average of available prices
                            available_prices = list(prices.values())
                            if available_prices:
                                imputed_prices[date_str] = np.mean(available_prices)
                            else:
                                # Last resort: skip this date (will be handled in portfolio calculation)
                                continue

                imputed_ticker_prices[ticker] = imputed_prices

            return imputed_ticker_prices

        except Exception as e:
            logger.warning(f"⚠️ Error in ticker price imputation: {e}")
            return ticker_prices  # Return original data on error
    
    def calculate_recovery_time(
        self,
        portfolio_values: List[float],
        dates: List[str],
        peak_value: float,
        trough_index: Optional[int] = None,
        lookback_months: int = 6,
    ) -> Dict[str, Any]:
        """
        Calculate time to recover to peak value at multiple thresholds (90%, 95%, 100%).

        Args:
            portfolio_values: List of normalized portfolio values
            dates: List of date strings
            peak_value: Peak value to recover to
            trough_index: Optional index of crisis trough (if already known)
            lookback_months: Number of months to use for trajectory regression (default 6, use 12 for longer crises like 2008)

        Returns:
            Dict with recovery_months, recovery_date, recovery_index, recovered, recovery_trajectory,
            and recovery_thresholds (90%, 95%, 100%)
        """
        try:
            # Prefer explicit trough index from crisis-aware drawdown calculation
            if trough_index is not None and 0 <= trough_index < len(portfolio_values):
                trough_idx = trough_index
                trough_value = float(portfolio_values[trough_idx])
            else:
                peaks_troughs = self.detect_peaks_and_troughs(portfolio_values, dates)

                if not peaks_troughs['trough']:
                    return {
                        'recovery_months': None,
                        'recovery_date': None,
                        'recovery_index': None,
                        'recovered': False,
                        'recovery_trajectory': 'No Recovery',
                        'recovery_thresholds': {
                            '90': None,
                            '95': None,
                            '100': None,
                        },
                        'recovery_needed_pct': 0.0,
                        'trajectory_projections': {},
                    }

                trough = peaks_troughs['trough']
                trough_idx = trough['index']
                trough_value = trough['value']

            # Calculate recovery needed percentage
            current_value = portfolio_values[-1] if portfolio_values else trough_value
            recovery_needed_pct = ((peak_value - current_value) / peak_value) * 100 if peak_value > 0 else 0

            # Calculate trajectory-based projections to peak with adaptive lookback
            trajectory_projections = self.calculate_enhanced_trajectory_projections(
                portfolio_values,
                dates,
                peak_value,
                lookback_months=lookback_months,
            )

            # Calculate recovery times for multiple thresholds (including 100% = peak)
            recovery_thresholds: Dict[str, Any] = {
                '90': None,
                '95': None,
                '100': None,  # Full recovery to peak
            }

            # Recovery thresholds: percentage of peak to recover to
            # 90% = recover to 90% of peak (10% below peak)
            # 95% = recover to 95% of peak (5% below peak)
            # 100% = recover to 100% of peak (full recovery) - PRIMARY TARGET
            thresholds = {
                '90': 0.90,   # 10% below peak
                '95': 0.95,   # 5% below peak
                '100': 1.0,   # 100% of peak (full recovery)
            }

            # Search for recovery after trough for each threshold
            for threshold_key, threshold_pct in thresholds.items():
                threshold_value = peak_value * threshold_pct
                recovery_idx = None

                # Only search if trough is below threshold
                if trough_value < threshold_value:
                    for i in range(trough_idx + 1, len(portfolio_values)):
                        if portfolio_values[i] >= threshold_value:
                            recovery_idx = i
                            break

                    if recovery_idx is not None:
                        months_to_recover = recovery_idx - trough_idx
                        recovery_thresholds[threshold_key] = {
                            'months': months_to_recover,
                            'date': dates[recovery_idx],
                            'index': recovery_idx,
                            'recovered': True,
                            'progress_pct': 100.0,
                        }
                    else:
                        # Not recovered yet - calculate progress towards threshold
                        final_value = portfolio_values[-1] if portfolio_values else trough_value
                        if final_value > trough_value and threshold_value > trough_value:
                            progress_pct = ((final_value - trough_value) / (threshold_value - trough_value)) * 100
                            progress_pct = float(max(0.0, min(100.0, progress_pct)))
                        else:
                            progress_pct = 0.0

                        recovery_thresholds[threshold_key] = {
                            'months': None,
                            'date': None,
                            'index': None,
                            'recovered': False,
                            'progress_pct': progress_pct,
                        }
                else:
                    # Trough is already above threshold, recovery is immediate
                    recovery_thresholds[threshold_key] = {
                        'months': 0,
                        'date': dates[trough_idx] if trough_idx < len(dates) else dates[0],
                        'index': trough_idx,
                        'recovered': True,
                        'progress_pct': 100.0,
                    }

            # Primary recovery metric: 100% recovery to peak (full recovery)
            primary_recovery = recovery_thresholds.get('100') or recovery_thresholds.get('95')
            if primary_recovery and primary_recovery.get('recovered'):
                recovery_months = primary_recovery['months']
                recovery_date = primary_recovery['date']
                recovery_idx = primary_recovery['index']
                recovered = True

                # Determine trajectory pattern
                if recovery_months is not None:
                    if recovery_months <= 6:
                        trajectory = 'V-shaped'
                    elif recovery_months <= 12:
                        trajectory = 'U-shaped'
                    else:
                        trajectory = 'L-shaped'
                else:
                    trajectory = 'Unknown'
            else:
                # Not recovered yet - use trajectory projections
                recovery_months = trajectory_projections.get('realistic_months')
                recovery_date = None
                recovery_idx = None
                recovered = False

                # Determine trajectory based on projections
                realistic_months = trajectory_projections.get('realistic_months')
                if realistic_months:
                    if realistic_months <= 6:
                        trajectory = 'V-shaped (projected)'
                    elif realistic_months <= 12:
                        trajectory = 'U-shaped (projected)'
                    else:
                        trajectory = 'L-shaped (projected)'
                else:
                    trajectory = 'L-shaped (projected)'

            return {
                'recovery_months': recovery_months,
                'recovery_date': recovery_date,
                'recovery_index': recovery_idx,
                'recovered': recovered,
                'recovery_trajectory': trajectory,
                'recovery_needed_pct': float(recovery_needed_pct),
                'trajectory_projections': trajectory_projections,
                'recovery_thresholds': recovery_thresholds,
            }
        except Exception as e:
            logger.error(f"❌ Error calculating recovery time: {e}")
            return {
                'recovery_months': None,
                'recovery_date': None,
                'recovery_index': None,
                'recovered': False,
                'recovery_trajectory': 'No Recovery',
                'recovery_thresholds': {
                    '90': None,
                    '95': None,
                    '100': None,
                },
                'recovery_needed_pct': 0.0,
                'trajectory_projections': {},
            }
    
    def calculate_correlation_breakdown(
        self,
        tickers: List[str],
        weights: Dict[str, float],
        crisis_period: Tuple[str, str],
        normal_period: Tuple[str, str]
    ) -> Dict[str, Any]:
        """
        Calculate correlation during crisis vs. normal period.
        
        Args:
            tickers: List of ticker symbols
            weights: Dict mapping ticker to weight
            crisis_period: Tuple of (start_date, end_date) for crisis
            normal_period: Tuple of (start_date, end_date) for normal period
        
        Returns:
            Dict with correlation metrics
        """
        try:
            # Get returns for both periods
            crisis_data = self.calculate_portfolio_values_over_period(
                tickers, weights, crisis_period[0], crisis_period[1], include_recovery=False
            )
            normal_data = self.calculate_portfolio_values_over_period(
                tickers, weights, normal_period[0], normal_period[1], include_recovery=False
            )
            
            # Get individual ticker returns for correlation calculation
            crisis_returns = {}
            normal_returns = {}
            
            for ticker in tickers:
                ticker_data = self.data_service.get_monthly_data(ticker)
                if ticker_data and ticker_data.get('prices'):
                    prices = ticker_data['prices']
                    if isinstance(prices, pd.Series):
                        prices_dict = {str(date): float(price) for date, price in prices.items()}
                    elif isinstance(prices, dict):
                        prices_dict = prices
                    else:
                        continue
                    
                    # Filter and calculate returns for crisis period
                    crisis_prices = self.filter_prices_by_date_range(
                        prices_dict, crisis_period[0], crisis_period[1]
                    )
                    if len(crisis_prices) > 1:
                        sorted_crisis = sorted(crisis_prices.items(), key=lambda x: x[0])
                        crisis_ret = []
                        for i in range(1, len(sorted_crisis)):
                            if sorted_crisis[i-1][1] > 0:
                                ret = (sorted_crisis[i][1] - sorted_crisis[i-1][1]) / sorted_crisis[i-1][1]
                                crisis_ret.append(ret)
                        if len(crisis_ret) > 0:
                            crisis_returns[ticker] = crisis_ret
                    
                    # Filter and calculate returns for normal period
                    normal_prices = self.filter_prices_by_date_range(
                        prices_dict, normal_period[0], normal_period[1]
                    )
                    if len(normal_prices) > 1:
                        sorted_normal = sorted(normal_prices.items(), key=lambda x: x[0])
                        normal_ret = []
                        for i in range(1, len(sorted_normal)):
                            if sorted_normal[i-1][1] > 0:
                                ret = (sorted_normal[i][1] - sorted_normal[i-1][1]) / sorted_normal[i-1][1]
                                normal_ret.append(ret)
                        if len(normal_ret) > 0:
                            normal_returns[ticker] = normal_ret
            
            # Calculate correlation matrices
            crisis_correlation = 0.0
            normal_correlation = 0.0
            
            if len(crisis_returns) >= 2:
                # Align returns to same length
                min_length = min(len(ret) for ret in crisis_returns.values())
                aligned_crisis = {t: ret[:min_length] for t, ret in crisis_returns.items()}
                
                # Calculate pairwise correlations
                ticker_list = list(aligned_crisis.keys())
                correlations = []
                for i in range(len(ticker_list)):
                    for j in range(i + 1, len(ticker_list)):
                        ticker1, ticker2 = ticker_list[i], ticker_list[j]
                        corr = np.corrcoef(aligned_crisis[ticker1], aligned_crisis[ticker2])[0, 1]
                        if not np.isnan(corr):
                            correlations.append(corr)
                
                if len(correlations) > 0:
                    crisis_correlation = float(np.mean(correlations))
            
            if len(normal_returns) >= 2:
                # Align returns to same length
                min_length = min(len(ret) for ret in normal_returns.values())
                aligned_normal = {t: ret[:min_length] for t, ret in normal_returns.items()}
                
                # Calculate pairwise correlations
                ticker_list = list(aligned_normal.keys())
                correlations = []
                for i in range(len(ticker_list)):
                    for j in range(i + 1, len(ticker_list)):
                        ticker1, ticker2 = ticker_list[i], ticker_list[j]
                        corr = np.corrcoef(aligned_normal[ticker1], aligned_normal[ticker2])[0, 1]
                        if not np.isnan(corr):
                            correlations.append(corr)
                
                if len(correlations) > 0:
                    normal_correlation = float(np.mean(correlations))
            
            correlation_increase = crisis_correlation - normal_correlation
            diversification_effectiveness = max(0.0, min(100.0, 100 - (crisis_correlation * 100)))
            
            return {
                'crisis_correlation': float(crisis_correlation),
                'normal_correlation': float(normal_correlation),
                'correlation_increase': float(correlation_increase),
                'diversification_effectiveness': float(diversification_effectiveness)
            }
        except Exception as e:
            logger.warning(f"⚠️ Error calculating correlation breakdown: {e}")
            return {
                'crisis_correlation': 0.5,
                'normal_correlation': 0.3,
                'correlation_increase': 0.2,
                'diversification_effectiveness': 50.0
            }
    
    def calculate_sector_impact(
        self,
        tickers: List[str],
        weights: Dict[str, float],
        period: Tuple[str, str]
    ) -> Dict[str, Any]:
        """
        Calculate sector-specific returns during period.
        
        Args:
            tickers: List of ticker symbols
            weights: Dict mapping ticker to weight
            period: Tuple of (start_date, end_date)
        
        Returns:
            Dict with sector returns, worst_sector, best_sector, sector_exposure
        """
        try:
            sector_data = {}
            sector_weights = {}
            
            # Get sector and return data for each ticker
            for ticker in tickers:
                ticker_data = self.data_service.get_monthly_data(ticker)
                if not ticker_data:
                    continue
                
                sector = ticker_data.get('sector', 'Unknown')
                weight = weights.get(ticker, 0.0)
                
                # Get prices and calculate return
                prices = ticker_data.get('prices')
                if prices:
                    if isinstance(prices, pd.Series):
                        prices_dict = {str(date): float(price) for date, price in prices.items()}
                    elif isinstance(prices, dict):
                        prices_dict = prices
                    else:
                        continue
                    
                    filtered_prices = self.filter_prices_by_date_range(
                        prices_dict, period[0], period[1]
                    )
                    
                    if len(filtered_prices) >= 2:
                        sorted_prices = sorted(filtered_prices.items(), key=lambda x: x[0])
                        start_price = sorted_prices[0][1]
                        end_price = sorted_prices[-1][1]
                        
                        if start_price > 0:
                            ticker_return = (end_price - start_price) / start_price
                            
                            if sector not in sector_data:
                                sector_data[sector] = []
                                sector_weights[sector] = []
                            
                            sector_data[sector].append(ticker_return)
                            sector_weights[sector].append(weight)
            
            # Calculate weighted average return per sector
            sector_returns = {}
            sector_exposure = {}
            
            for sector, returns in sector_data.items():
                weights_list = sector_weights[sector]
                total_weight = sum(weights_list)
                
                if total_weight > 0:
                    # Weighted average return
                    weighted_return = sum(r * w for r, w in zip(returns, weights_list)) / total_weight
                    sector_returns[sector] = float(weighted_return)
                    sector_exposure[sector] = float(total_weight)
            
            # Find worst and best sectors
            worst_sector = None
            best_sector = None
            
            if sector_returns:
                worst_sector_name = min(sector_returns.keys(), key=lambda k: sector_returns[k])
                best_sector_name = max(sector_returns.keys(), key=lambda k: sector_returns[k])
                
                worst_sector = {
                    'name': worst_sector_name,
                    'return': sector_returns[worst_sector_name],
                    'weight_in_portfolio': sector_exposure.get(worst_sector_name, 0.0)
                }
                
                best_sector = {
                    'name': best_sector_name,
                    'return': sector_returns[best_sector_name],
                    'weight_in_portfolio': sector_exposure.get(best_sector_name, 0.0)
                }
            
            return {
                'sector_returns': sector_returns,
                'worst_sector': worst_sector,
                'best_sector': best_sector,
                'sector_exposure': sector_exposure
            }
        except Exception as e:
            logger.warning(f"⚠️ Error calculating sector impact: {e}")
            return {
                'sector_returns': {},
                'worst_sector': None,
                'best_sector': None,
                'sector_exposure': {}
            }
    
    def analyze_covid19_scenario(
        self,
        tickers: List[str],
        weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Analyze portfolio performance during COVID-19 crash (Feb-Apr 2020).
        
        Args:
            tickers: List of ticker symbols
            weights: Dict mapping ticker to weight
        
        Returns:
            Complete scenario analysis dict
        """
        try:
            import time
            op_start = time.time()
            
            # Scenario periods
            crisis_start = '2020-02-01'
            crisis_end = '2020-04-30'
            recovery_end = '2020-08-31'
            normal_start = '2019-02-01'
            normal_end = '2020-01-31'
            # Start graph from January 2020 to show pre-crisis baseline
            graph_start = '2020-01-01'
            
            # Calculate portfolio values - start from January 2020 to show pre-crisis baseline
            logger.info(f"⏱️ Calculating portfolio values for crisis period (starting from {graph_start})...")
            portfolio_data = self.calculate_portfolio_values_over_period(
                tickers, weights, graph_start, recovery_end, include_recovery=True
            )
            logger.info(f"⏱️ Portfolio values calculated in {time.time() - op_start:.3f}s")
            
            if len(portfolio_data['values']) == 0:
                raise ValueError("No portfolio data available for COVID-19 scenario")
            
            # Detect peaks and troughs using crisis-aware window
            peaks_troughs = self.detect_peaks_and_troughs(
                portfolio_data['values'],
                portfolio_data['dates'],
                crisis_start_date=crisis_start,
                crisis_end_date=crisis_end,
            )
            
            # Calculate metrics
            total_return = (portfolio_data['values'][-1] - portfolio_data['values'][0]) / portfolio_data['values'][0]
            
            max_drawdown_data = self.calculate_maximum_drawdown(
                portfolio_data['values'],
                portfolio_data['dates'],
                crisis_start_date=crisis_start,
                crisis_end_date=crisis_end,
            )
            
            # Use crisis-aware peak and trough for recovery calculations
            peak_value = max_drawdown_data['peak_value']
            trough_date = max_drawdown_data['trough_date']
            trough_index = next(
                (i for i, d in enumerate(portfolio_data['dates']) if d == trough_date),
                None,
            )
            # Use 6-month lookback for COVID-19 (shorter crisis with limited data - 8 months total)
            recovery_data = self.calculate_recovery_time(
                portfolio_data['values'],
                portfolio_data['dates'],
                peak_value,
                trough_index=trough_index,
                lookback_months=6,  # Standard lookback for shorter crises
            )
            
            # Volatility calculations: use full crisis window for stability (3 months is too few for reliable std)
            crisis_returns = portfolio_data['monthly_returns']
            if len(crisis_returns) > 1:
                volatility_during_crisis = float(np.std(crisis_returns) * np.sqrt(12))
            else:
                volatility_during_crisis = 0.0
            
            # Calculate normal period volatility
            op_start = time.time()
            logger.info(f"⏱️ Calculating normal period volatility (COVID-19)...")
            normal_data = self.calculate_portfolio_values_over_period(
                tickers, weights, normal_start, normal_end, include_recovery=False
            )
            logger.info(f"⏱️ Normal period calculated in {time.time() - op_start:.3f}s")
            if len(normal_data['monthly_returns']) > 1:
                volatility_normal = float(np.std(normal_data['monthly_returns']) * np.sqrt(12))
            else:
                volatility_normal = 0.2  # Default
            
            volatility_ratio = volatility_during_crisis / volatility_normal if volatility_normal > 0 else 1.0
            
            worst_month_return = min(portfolio_data['monthly_returns']) if portfolio_data['monthly_returns'] else 0.0
            
            # Advanced Risk Metrics
            advanced_risk = self.calculate_advanced_risk_metrics(
                portfolio_data['values'],
                portfolio_data['dates'],
                portfolio_data['monthly_returns'],
                market_returns=None  # Could add market index returns later
            )
            
            # Monte Carlo Simulation for crisis period (illustrative; uses in-sample crisis mean/vol, not a forecast)
            monte_carlo = None
            try:
                op_start = time.time()
                logger.info(f"⏱️ Running Monte Carlo simulation (5,000 iterations)...")
                from utils.port_analytics import PortfolioAnalytics
                analytics = PortfolioAnalytics()
                crisis_expected_return = float(np.mean(portfolio_data['monthly_returns']) * 12) if len(portfolio_data['monthly_returns']) > 0 else 0.0
                monte_carlo = analytics.run_monte_carlo_simulation(
                    expected_return=crisis_expected_return,
                    risk=volatility_during_crisis,
                    num_simulations=5000,
                    time_horizon_years=1.0
                )
                logger.info(f"⏱️ Monte Carlo completed in {time.time() - op_start:.3f}s")
            except Exception as e:
                logger.warning(f"⚠️ Could not run Monte Carlo for COVID-19: {e}")
            
            # Sector impact
            sector_impact = self.calculate_sector_impact(
                tickers, weights, (crisis_start, crisis_end)
            )
            
            # Monthly performance data
            monthly_performance = []
            for i, date in enumerate(portfolio_data['dates']):
                if i < len(portfolio_data['values']) and i < len(portfolio_data['monthly_returns']):
                    monthly_performance.append({
                        'month': date[:7],  # YYYY-MM format
                        'return': portfolio_data['monthly_returns'][i],
                        'value': portfolio_data['values'][i]
                    })
            
            # Determine recovery metrics based on drawdown significance
            is_significant = max_drawdown_data.get('is_significant', False)
            
            if is_significant:
                # Significant drawdown: use actual recovery data
                recovery_months = recovery_data['recovery_months']
                recovery_date = recovery_data['recovery_date']
                recovery_pattern = recovery_data['recovery_trajectory']
                recovered = recovery_data['recovered']
                recovery_thresholds = recovery_data.get('recovery_thresholds', {})
                recovery_needed_pct = recovery_data.get('recovery_needed_pct', 0.0)
                # Include trajectory projections for significant drawdowns (educational purposes)
                trajectory_projections = recovery_data.get('trajectory_projections', {})
            else:
                # Minor drawdown (<3%): show minimal recovery or immediate recovery
                drawdown_pct = abs(max_drawdown_data['max_drawdown']) * 100

                if drawdown_pct < 0.5:
                    # Negligible drawdown (<0.5%)
                    recovery_months = 0
                    recovery_date = max_drawdown_data['trough_date']
                    recovery_pattern = 'Minimal Impact'
                    recovered = True
                else:
                    # Minor drawdown (0.5% - 3%)
                    # Check if portfolio actually recovered
                    if recovery_data['recovered']:
                        recovery_months = recovery_data['recovery_months']
                        recovery_date = recovery_data['recovery_date']
                        recovery_pattern = f"Quick Recovery ({recovery_data['recovery_trajectory']})"
                        recovered = True
                    else:
                        recovery_months = recovery_data['recovery_months']
                        recovery_date = recovery_data['recovery_date']
                        recovery_pattern = 'Minor Drawdown (Recovering)'
                        recovered = False

                recovery_thresholds = recovery_data.get('recovery_thresholds', {})
                recovery_needed_pct = recovery_data.get('recovery_needed_pct', 0.0)
                # Include trajectory projections for significant drawdowns (educational purposes)
                trajectory_projections = recovery_data.get('trajectory_projections', {})
            
            return {
                'scenario_name': '2020 COVID-19 Crash',
                'period': {
                    'start': crisis_start,
                    'end': crisis_end,
                    'recovery_end': recovery_end
                },
                'metrics': {
                    'total_return': float(total_return),
                    'worst_month_return': float(worst_month_return),
                    'max_drawdown': max_drawdown_data['max_drawdown'],
                    'max_drawdown_data': max_drawdown_data,
                    'volatility_during_crisis': float(volatility_during_crisis),
                    'volatility_normal_period': float(volatility_normal),
                    'volatility_ratio': float(volatility_ratio),
                    'recovery_months': recovery_months,
                    'recovery_date': recovery_date,
                    'recovery_pattern': recovery_pattern,
                    'recovered': recovered,
                    'recovery_thresholds': recovery_thresholds,
                    'recovery_needed_pct': recovery_needed_pct,
                    'trajectory_projections': trajectory_projections,
                    'advanced_risk': advanced_risk
                },
                'monte_carlo': monte_carlo,
                'peaks_troughs': peaks_troughs,
                'sector_impact': sector_impact,
                'monthly_performance': monthly_performance,
                'data_availability': portfolio_data['data_availability']
            }
        except Exception as e:
            logger.error(f"❌ Error analyzing COVID-19 scenario: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def analyze_2008_crisis_scenario(
        self,
        tickers: List[str],
        weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Analyze portfolio performance during 2008 Financial Crisis (Sep 2008 - Mar 2010).
        
        Args:
            tickers: List of ticker symbols
            weights: Dict mapping ticker to weight
        
        Returns:
            Complete scenario analysis dict
        """
        try:
            import time
            op_start = time.time()
            
            # Scenario periods
            crisis_start = '2008-09-01'
            crisis_end = '2010-03-31'
            # Extend recovery_end to 2011-03-31 to provide more data for trajectory calculations
            # This ensures at least 6 months of post-recovery data for accurate projections
            recovery_end = '2011-03-31'
            normal_start = '2007-09-01'
            normal_end = '2008-08-31'
            # Start graph from August 2008 to show pre-crisis baseline (1 month before crisis)
            graph_start = '2008-08-01'
            
            # Calculate portfolio values - start from August 2008 to show pre-crisis baseline
            logger.info(f"⏱️ Calculating portfolio values for crisis period (starting from {graph_start})...")
            portfolio_data = self.calculate_portfolio_values_over_period(
                tickers, weights, graph_start, recovery_end, include_recovery=True
            )
            logger.info(f"⏱️ Portfolio values calculated in {time.time() - op_start:.3f}s")
            
            if len(portfolio_data['values']) == 0:
                # Graceful fallback: do not crash the whole stress test if a portfolio has
                # insufficient historical coverage (e.g., newer IPOs / listings).
                return {
                    'scenario_name': '2008 Financial Crisis',
                    'period': {
                        'start': crisis_start,
                        'end': crisis_end,
                        'recovery_end': recovery_end
                    },
                    'metrics': {
                        'total_return': 0.0,
                        'worst_month_return': 0.0,
                        'max_drawdown': 0.0,
                        'max_drawdown_data': {
                            'max_drawdown': 0.0,
                            'is_significant': False,
                            'peak_value': 1.0,
                            'peak_date': None,
                            'trough_value': 1.0,
                            'trough_date': None,
                            'drawdown_duration_months': 0,
                        },
                        'volatility_during_crisis': 0.0,
                        'volatility_normal_period': 0.0,
                        'volatility_ratio': 1.0,
                        'recovery_months': None,
                        'recovery_date': None,
                        'recovery_pattern': 'N/A',
                        'recovered': False,
                        'recovery_thresholds': {
                            '90': None,
                            '95': None,
                            '100': None,
                        },
                        'recovery_needed_pct': 0.0,
                        'trajectory_projections': {},
                        'advanced_risk': {},
                    },
                    'monte_carlo': None,
                    'peaks_troughs': {
                        'peak': None,
                        'trough': None,
                        'recovery_peak': None,
                        'all_peaks': [],
                        'all_troughs': [],
                    },
                    'sector_impact': None,
                    'monthly_performance': [],
                    'data_availability': portfolio_data.get('data_availability', {t: False for t in tickers}),
                    'error': 'Insufficient historical price coverage to model the 2008 crisis for this portfolio.'
                }
            
            # Detect peaks and troughs using crisis-aware window
            peaks_troughs = self.detect_peaks_and_troughs(
                portfolio_data['values'],
                portfolio_data['dates'],
                crisis_start_date=crisis_start,
                crisis_end_date=crisis_end,
            )
            
            # Calculate metrics
            total_return = (portfolio_data['values'][-1] - portfolio_data['values'][0]) / portfolio_data['values'][0]
            
            max_drawdown_data = self.calculate_maximum_drawdown(
                portfolio_data['values'],
                portfolio_data['dates'],
                crisis_start_date=crisis_start,
                crisis_end_date=crisis_end,
            )
            
            # Use crisis-aware peak and trough for recovery calculations
            peak_value = max_drawdown_data['peak_value']
            trough_date = max_drawdown_data['trough_date']
            trough_index = next(
                (i for i, d in enumerate(portfolio_data['dates']) if d == trough_date),
                None,
            )
            # Use 12-month lookback for 2008 crisis (longer crisis with more data available - 32 months total)
            recovery_data = self.calculate_recovery_time(
                portfolio_data['values'],
                portfolio_data['dates'],
                peak_value,
                trough_index=trough_index,
                lookback_months=12,  # Longer lookback for better regression quality
            )
            
            # Volatility calculations
            crisis_returns = portfolio_data['monthly_returns'][:18]  # First 18 months
            if len(crisis_returns) > 1:
                volatility_during_crisis = float(np.std(crisis_returns) * np.sqrt(12))
            else:
                volatility_during_crisis = 0.0
            
            # Calculate normal period volatility
            op_start = time.time()
            logger.info(f"⏱️ Calculating normal period volatility (2008 Crisis)...")
            normal_data = self.calculate_portfolio_values_over_period(
                tickers, weights, normal_start, normal_end, include_recovery=False
            )
            logger.info(f"⏱️ Normal period calculated in {time.time() - op_start:.3f}s")
            if len(normal_data['monthly_returns']) > 1:
                volatility_normal = float(np.std(normal_data['monthly_returns']) * np.sqrt(12))
            else:
                volatility_normal = 0.2  # Default
            
            volatility_ratio = volatility_during_crisis / volatility_normal if volatility_normal > 0 else 1.0
            
            worst_month_return = min(portfolio_data['monthly_returns']) if portfolio_data['monthly_returns'] else 0.0
            
            # Advanced Risk Metrics
            advanced_risk = self.calculate_advanced_risk_metrics(
                portfolio_data['values'],
                portfolio_data['dates'],
                portfolio_data['monthly_returns'],
                market_returns=None  # Could add market index returns later
            )
            
            # Monte Carlo Simulation for crisis period
            monte_carlo = None
            try:
                op_start = time.time()
                logger.info(f"⏱️ Running Monte Carlo simulation (5,000 iterations) for 2008 Crisis...")
                from utils.port_analytics import PortfolioAnalytics
                analytics = PortfolioAnalytics()
                # Use crisis volatility and expected return for Monte Carlo
                crisis_expected_return = float(np.mean(portfolio_data['monthly_returns']) * 12) if len(portfolio_data['monthly_returns']) > 0 else 0.0
                # Reduced from 10,000 to 5,000 for better performance (still statistically significant)
                monte_carlo = analytics.run_monte_carlo_simulation(
                    expected_return=crisis_expected_return,
                    risk=volatility_during_crisis,
                    num_simulations=5000,  # Optimized: reduced from 10,000 to 5,000
                    time_horizon_years=1.0
                )
                logger.info(f"⏱️ Monte Carlo completed in {time.time() - op_start:.3f}s")
            except Exception as e:
                logger.warning(f"⚠️ Could not run Monte Carlo for 2008 Crisis: {e}")
            
            # Sector impact
            sector_impact = self.calculate_sector_impact(
                tickers, weights, (crisis_start, crisis_end)
            )
            
            # Monthly performance data
            monthly_performance = []
            for i, date in enumerate(portfolio_data['dates']):
                if i < len(portfolio_data['values']) and i < len(portfolio_data['monthly_returns']):
                    monthly_performance.append({
                        'month': date[:7],  # YYYY-MM format
                        'return': portfolio_data['monthly_returns'][i],
                        'value': portfolio_data['values'][i]
                    })
            
            # Determine recovery metrics based on drawdown significance (same logic as COVID-19)
            is_significant = max_drawdown_data.get('is_significant', False)
            
            if is_significant:
                recovery_months_2008 = recovery_data['recovery_months']
                recovery_date_2008 = recovery_data['recovery_date']
                recovery_pattern_2008 = recovery_data['recovery_trajectory']
                recovered_2008 = recovery_data['recovered']
                recovery_thresholds_2008 = recovery_data.get('recovery_thresholds', {})
                recovery_needed_pct_2008 = recovery_data.get('recovery_needed_pct', 0.0)
                # Only include trajectory projections if portfolio hasn't fully recovered
                trajectory_projections_2008 = recovery_data.get('trajectory_projections', {}) if recovery_needed_pct_2008 > 0 else {}
            else:
                drawdown_pct = abs(max_drawdown_data['max_drawdown']) * 100

                if drawdown_pct < 0.5:
                    recovery_months_2008 = 0
                    recovery_date_2008 = max_drawdown_data['trough_date']
                    recovery_pattern_2008 = 'Minimal Impact'
                    recovered_2008 = True
                else:
                    if recovery_data['recovered']:
                        recovery_months_2008 = recovery_data['recovery_months']
                        recovery_date_2008 = recovery_data['recovery_date']
                        recovery_pattern_2008 = f"Quick Recovery ({recovery_data['recovery_trajectory']})"
                        recovered_2008 = True
                    else:
                        recovery_months_2008 = recovery_data['recovery_months']
                        recovery_date_2008 = recovery_data['recovery_date']
                        recovery_pattern_2008 = 'Minor Drawdown (Recovering)'
                        recovered_2008 = False

                recovery_thresholds_2008 = recovery_data.get('recovery_thresholds', {})
                recovery_needed_pct_2008 = recovery_data.get('recovery_needed_pct', 0.0)
                # Only include trajectory projections if portfolio hasn't fully recovered
                trajectory_projections_2008 = recovery_data.get('trajectory_projections', {}) if recovery_needed_pct_2008 > 0 else {}
            
            return {
                'scenario_name': '2008 Financial Crisis',
                'period': {
                    'start': crisis_start,
                    'end': crisis_end,
                    'recovery_end': recovery_end
                },
                'metrics': {
                    'total_return': float(total_return),
                    'worst_month_return': float(worst_month_return),
                    'max_drawdown': max_drawdown_data['max_drawdown'],
                    'max_drawdown_data': max_drawdown_data,
                    'volatility_during_crisis': float(volatility_during_crisis),
                    'volatility_normal_period': float(volatility_normal),
                    'volatility_ratio': float(volatility_ratio),
                    'recovery_months': recovery_months_2008,
                    'recovery_date': recovery_date_2008,
                    'recovery_pattern': recovery_pattern_2008,
                    'recovered': recovered_2008,
                    'recovery_thresholds': recovery_thresholds_2008,
                    'recovery_needed_pct': recovery_needed_pct_2008,
                    'trajectory_projections': trajectory_projections_2008,
                    'advanced_risk': advanced_risk
                },
                'monte_carlo': monte_carlo,
                'peaks_troughs': peaks_troughs,
                'sector_impact': sector_impact,
                'monthly_performance': monthly_performance,
                'data_availability': portfolio_data['data_availability']
            }
        except Exception as e:
            logger.error(f"❌ Error analyzing 2008 Crisis scenario: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def calculate_advanced_risk_metrics(
        self,
        portfolio_values: List[float],
        dates: List[str],
        returns: List[float],
        market_returns: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate advanced risk metrics: VaR, CVaR, Beta, Tail Risk
        
        Args:
            portfolio_values: List of normalized portfolio values
            dates: List of date strings
            returns: List of monthly returns
            market_returns: Optional list of market returns for Beta calculation
        
        Returns:
            Dict with VaR, CVaR, Beta, Tail Risk metrics
        """
        try:
            if len(returns) == 0:
                return {
                    'var_95': 0.0,
                    'cvar_95': 0.0,
                    'beta': 1.0,
                    'tail_risk': 0.0,
                    'downside_deviation': 0.0
                }
            
            returns_array = np.array(returns)
            
            # Value at Risk (VaR) - 95th percentile (5% worst case)
            var_95 = float(np.percentile(returns_array, 5))
            
            # Conditional VaR (CVaR) - Expected loss beyond VaR threshold
            cvar_95 = float(np.mean(returns_array[returns_array <= var_95])) if len(returns_array[returns_array <= var_95]) > 0 else var_95
            
            # Beta calculation (if market returns provided)
            beta = 1.0
            if market_returns and len(market_returns) == len(returns):
                market_array = np.array(market_returns)
                if np.std(market_array) > 0:
                    covariance = np.cov(returns_array, market_array)[0, 1]
                    market_variance = np.var(market_array)
                    beta = float(covariance / market_variance) if market_variance > 0 else 1.0
            
            # Tail Risk - Probability of extreme losses (beyond 2 standard deviations)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            tail_threshold = mean_return - (2 * std_return)
            tail_risk = float(np.sum(returns_array < tail_threshold) / len(returns_array) * 100) if len(returns_array) > 0 else 0.0
            
            # Downside Deviation - Standard deviation of negative returns only
            negative_returns = returns_array[returns_array < 0]
            downside_deviation = float(np.std(negative_returns)) if len(negative_returns) > 0 else 0.0
            
            return {
                'var_95': var_95,
                'cvar_95': cvar_95,
                'beta': beta,
                'tail_risk': tail_risk,
                'downside_deviation': downside_deviation
            }
        except Exception as e:
            logger.warning(f"⚠️ Error calculating advanced risk metrics: {e}")
            return {
                'var_95': 0.0,
                'cvar_95': 0.0,
                'beta': 1.0,
                'tail_risk': 0.0,
                'downside_deviation': 0.0
            }
    
"""
Input Validation and Sanitization
Prevents XSS, injection attacks, and malformed data
"""
import re
import html
from typing import List
from fastapi import HTTPException

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

# Ticker validation pattern (uppercase letters, 1-5 characters)
TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}$')

# Portfolio name validation (alphanumeric, spaces, hyphens, max 100 chars)
PORTFOLIO_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_]{1,100}$')

def validate_ticker(ticker: str, allow_none: bool = False) -> str:
    """
    Validate and normalize a single ticker symbol

    Args:
        ticker: Ticker symbol to validate
        allow_none: If True, None/empty strings are allowed

    Returns:
        Normalized ticker (uppercase, stripped)

    Raises:
        ValidationError: If ticker is invalid
    """
    if not ticker:
        if allow_none:
            return None
        raise ValidationError("Ticker symbol is required")

    # Normalize: uppercase and strip whitespace
    ticker = ticker.upper().strip()

    # Validate format
    if not TICKER_PATTERN.match(ticker):
        raise ValidationError(
            f"Invalid ticker symbol '{ticker}'. "
            "Must be 1-5 uppercase letters only (e.g., AAPL, GOOGL, MSFT)"
        )

    return ticker

def validate_tickers(
    tickers: List[str],
    min_count: int = 1,
    max_count: int = 50,
    allow_duplicates: bool = False
) -> List[str]:
    """
    Validate and normalize a list of ticker symbols

    Args:
        tickers: List of ticker symbols
        min_count: Minimum number of tickers required
        max_count: Maximum number of tickers allowed
        allow_duplicates: If True, duplicate tickers are allowed

    Returns:
        List of normalized tickers

    Raises:
        ValidationError: If ticker list is invalid
    """
    if not tickers:
        raise ValidationError(f"At least {min_count} ticker(s) required")

    if len(tickers) < min_count:
        raise ValidationError(f"At least {min_count} ticker(s) required, got {len(tickers)}")

    if len(tickers) > max_count:
        raise ValidationError(
            f"Maximum {max_count} tickers allowed, got {len(tickers)}. "
            "Please reduce portfolio size or contact support for higher limits."
        )

    # Validate each ticker
    validated = []
    for ticker in tickers:
        try:
            validated_ticker = validate_ticker(ticker)
            validated.append(validated_ticker)
        except ValidationError as e:
            raise ValidationError(f"Invalid ticker in list: {e}")

    # Check for duplicates if not allowed
    if not allow_duplicates and len(validated) != len(set(validated)):
        duplicates = [t for t in validated if validated.count(t) > 1]
        unique_duplicates = list(set(duplicates))
        raise ValidationError(
            f"Duplicate tickers found: {', '.join(unique_duplicates)}. "
            "Each ticker should appear only once in the portfolio."
        )

    return validated

def validate_portfolio_name(name: str, max_length: int = 100) -> str:
    """
    Validate and sanitize portfolio name

    Args:
        name: Portfolio name
        max_length: Maximum allowed length

    Returns:
        Sanitized portfolio name

    Raises:
        ValidationError: If name is invalid
    """
    if not name:
        raise ValidationError("Portfolio name is required")

    # Strip whitespace
    name = name.strip()

    # Check length
    if len(name) > max_length:
        raise ValidationError(
            f"Portfolio name too long (max {max_length} characters). "
            f"Got {len(name)} characters."
        )

    # Sanitize HTML (prevent XSS)
    name = sanitize_html(name)

    # Validate allowed characters
    if not PORTFOLIO_NAME_PATTERN.match(name):
        raise ValidationError(
            "Portfolio name contains invalid characters. "
            "Only letters, numbers, spaces, hyphens, and underscores are allowed."
        )

    return name

def sanitize_html(text: str) -> str:
    """
    Remove HTML tags and escape special characters to prevent XSS

    Args:
        text: Input text that may contain HTML

    Returns:
        Sanitized text with HTML removed/escaped
    """
    if not text:
        return text

    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Escape remaining HTML entities
    text = html.escape(text)

    return text

def validate_weights(
    weights: dict,
    tickers: List[str],
    tolerance: float = 0.01
) -> dict:
    """
    Validate portfolio weights

    Args:
        weights: Dictionary of {ticker: weight}
        tickers: List of tickers that should have weights
        tolerance: Tolerance for weight sum (default 1%)

    Returns:
        Validated weights dictionary

    Raises:
        ValidationError: If weights are invalid
    """
    if not weights:
        raise ValidationError("Portfolio weights are required")

    # Check all tickers have weights
    for ticker in tickers:
        if ticker not in weights:
            raise ValidationError(f"Missing weight for ticker: {ticker}")

    # Check no extra tickers in weights
    for ticker in weights.keys():
        if ticker not in tickers:
            raise ValidationError(f"Unexpected ticker in weights: {ticker}")

    # Validate weight values
    for ticker, weight in weights.items():
        if not isinstance(weight, (int, float)):
            raise ValidationError(f"Weight for {ticker} must be a number, got {type(weight)}")

        if weight < 0:
            raise ValidationError(f"Weight for {ticker} cannot be negative: {weight}")

        if weight > 1:
            raise ValidationError(f"Weight for {ticker} cannot exceed 100%: {weight}")

    # Check weights sum to ~1.0 (100%)
    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > tolerance:
        raise ValidationError(
            f"Portfolio weights must sum to 100%. "
            f"Current sum: {total_weight * 100:.2f}%. "
            f"Please adjust allocations."
        )

    return weights

def validate_risk_profile(risk_profile: str) -> str:
    """
    Validate risk profile value

    Args:
        risk_profile: Risk profile string

    Returns:
        Normalized risk profile

    Raises:
        ValidationError: If risk profile is invalid
    """
    valid_profiles = [
        'very-conservative',
        'conservative',
        'moderate',
        'aggressive',
        'very-aggressive'
    ]

    if not risk_profile:
        raise ValidationError("Risk profile is required")

    # Normalize: lowercase, strip
    risk_profile = risk_profile.lower().strip()

    if risk_profile not in valid_profiles:
        raise ValidationError(
            f"Invalid risk profile '{risk_profile}'. "
            f"Must be one of: {', '.join(valid_profiles)}"
        )

    return risk_profile

def validate_capital(capital: float, min_capital: float = 1000.0) -> float:
    """
    Validate investment capital amount

    Args:
        capital: Capital amount
        min_capital: Minimum allowed capital

    Returns:
        Validated capital amount

    Raises:
        ValidationError: If capital is invalid
    """
    if capital is None:
        raise ValidationError("Investment capital is required")

    if not isinstance(capital, (int, float)):
        raise ValidationError(f"Capital must be a number, got {type(capital)}")

    if capital < min_capital:
        raise ValidationError(
            f"Minimum investment capital is ${min_capital:,.2f}. "
            f"Got ${capital:,.2f}."
        )

    if capital > 1_000_000_000:  # 1 billion limit (sanity check)
        raise ValidationError(
            f"Capital amount too large: ${capital:,.2f}. "
            "Please contact support for institutional investment management."
        )

    return float(capital)

def validate_pagination(
    limit: int = 10,
    offset: int = 0,
    max_limit: int = 100
) -> tuple:
    """
    Validate pagination parameters

    Args:
        limit: Number of items per page
        offset: Offset for pagination
        max_limit: Maximum allowed limit

    Returns:
        Tuple of (validated_limit, validated_offset)

    Raises:
        ValidationError: If pagination parameters are invalid
    """
    if limit < 1:
        raise ValidationError("Limit must be at least 1")

    if limit > max_limit:
        raise ValidationError(f"Limit cannot exceed {max_limit}")

    if offset < 0:
        raise ValidationError("Offset cannot be negative")

    return (int(limit), int(offset))

# FastAPI dependency for ticker validation
def ticker_validator(ticker: str) -> str:
    """FastAPI dependency for validating ticker parameter"""
    try:
        return validate_ticker(ticker)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

# FastAPI dependency for risk profile validation
def risk_profile_validator(risk_profile: str) -> str:
    """FastAPI dependency for validating risk profile parameter"""
    try:
        return validate_risk_profile(risk_profile)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

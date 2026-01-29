#!/usr/bin/env python3
"""
Swedish Tax Calculator
Implements Swedish tax calculation logic for ISK, KF, and AF accounts
Based on Swedish tax rules for 2025 and 2026
"""

import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SwedishTaxCalculator:
    """
    Calculates Swedish tax for different account types:
    - ISK (Investeringssparkonto): Investment savings account
    - KF (Kapitalförsäkring): Capital insurance
    - AF (Aktie- och fonddepå): Traditional securities account
    """
    
    def __init__(self):
        """Initialize the tax calculator"""
        # ISK 2025 parameters
        self.ISK_2025_TAX_FREE_LEVEL = 150000.0  # SEK
        self.ISK_2025_STATSLANERANTA = 0.0196  # 1.96%
        self.ISK_2025_SCHABLONRANTA = 0.0296  # 2.96% (Statslåneränta + 1%)
        self.ISK_2025_TAX_RATE = 0.30  # 30%
        self.ISK_2025_EFFECTIVE_RATE = 0.00888  # 0.888% (Schablonränta * Tax rate)
        
        # ISK 2026 parameters
        self.ISK_2026_TAX_FREE_LEVEL = 300000.0  # SEK
        self.ISK_2026_STATSLANERANTA = 0.0255  # 2.55%
        self.ISK_2026_SCHABLONRANTA = 0.0355  # 3.55% (Statslåneränta + 1%)
        self.ISK_2026_TAX_RATE = 0.30  # 30%
        self.ISK_2026_EFFECTIVE_RATE = 0.01065  # 1.065% (Schablonränta * Tax rate)
        
        # AF account parameters
        self.AF_CAPITAL_GAINS_TAX_RATE = 0.30  # 30% on realized gains
        self.AF_DIVIDEND_TAX_RATE = 0.30  # 30% (deducted at source)
        self.AF_FUND_SCHABLON_RATE = 0.0012  # 0.12% annually on funds > 50,000 SEK
        self.AF_FUND_THRESHOLD = 50000.0  # SEK
    
    def _validate_input(self, value: float, field_name: str) -> None:
        """Validate input values"""
        if value is None:
            raise ValueError(f"{field_name} cannot be None")
        if value < 0:
            raise ValueError(f"{field_name} cannot be negative")
        if not isinstance(value, (int, float)):
            raise ValueError(f"{field_name} must be a number")
    
    def calculate_isk_tax_2025(self, capital_underlag: float) -> Dict[str, float]:
        """
        Calculate ISK tax for 2025
        
        Formula:
        - Tax-free level: 150,000 SEK
        - Schablonränta: 2.96% (Statslåneränta 1.96% + 1%)
        - Tax rate: 30%
        - Effective rate: 0.888% (Schablonränta * Tax rate)
        
        Args:
            capital_underlag: Average capital during the year (SEK)
            
        Returns:
            Dictionary with tax calculation details
        """
        self._validate_input(capital_underlag, "capital_underlag")
        
        tax_free_level = self.ISK_2025_TAX_FREE_LEVEL
        taxable_capital = max(0.0, capital_underlag - tax_free_level)
        
        # Calculate schablonintäkt (imputed income)
        schablonintakt = taxable_capital * self.ISK_2025_SCHABLONRANTA
        
        # Calculate annual tax
        annual_tax = schablonintakt * self.ISK_2025_TAX_RATE
        
        # Effective tax rate on total capital
        if capital_underlag > 0:
            effective_tax_rate = (annual_tax / capital_underlag) * 100
        else:
            effective_tax_rate = 0.0
        
        return {
            "capital_underlag": round(capital_underlag, 2),
            "tax_free_level": round(tax_free_level, 2),
            "taxable_capital": round(taxable_capital, 2),
            "schablonintakt": round(schablonintakt, 2),
            "schablonranta": round(self.ISK_2025_SCHABLONRANTA * 100, 2),
            "annual_tax": round(annual_tax, 2),
            "effective_tax_rate": round(effective_tax_rate, 3),
            "tax_rate": round(self.ISK_2025_TAX_RATE * 100, 1)
        }
    
    def calculate_isk_tax_2026(self, capital_underlag: float) -> Dict[str, float]:
        """
        Calculate ISK tax for 2026
        
        Formula:
        - Tax-free level: 300,000 SEK
        - Schablonränta: 3.55% (Statslåneränta 2.55% + 1%)
        - Tax rate: 30%
        - Effective rate: 1.065% (Schablonränta * Tax rate)
        
        Args:
            capital_underlag: Average capital during the year (SEK)
            
        Returns:
            Dictionary with tax calculation details
        """
        self._validate_input(capital_underlag, "capital_underlag")
        
        tax_free_level = self.ISK_2026_TAX_FREE_LEVEL
        taxable_capital = max(0.0, capital_underlag - tax_free_level)
        
        # Calculate schablonintäkt (imputed income)
        schablonintakt = taxable_capital * self.ISK_2026_SCHABLONRANTA
        
        # Calculate annual tax
        annual_tax = schablonintakt * self.ISK_2026_TAX_RATE
        
        # Effective tax rate on total capital
        if capital_underlag > 0:
            effective_tax_rate = (annual_tax / capital_underlag) * 100
        else:
            effective_tax_rate = 0.0
        
        return {
            "capital_underlag": round(capital_underlag, 2),
            "tax_free_level": round(tax_free_level, 2),
            "taxable_capital": round(taxable_capital, 2),
            "schablonintakt": round(schablonintakt, 2),
            "schablonranta": round(self.ISK_2026_SCHABLONRANTA * 100, 2),
            "annual_tax": round(annual_tax, 2),
            "effective_tax_rate": round(effective_tax_rate, 3),
            "tax_rate": round(self.ISK_2026_TAX_RATE * 100, 1)
        }
    
    def calculate_kf_tax(self, capital_underlag: float, year: int) -> Dict[str, float]:
        """
        Calculate KF (Kapitalförsäkring) tax
        KF uses the same calculation as ISK
        
        Args:
            capital_underlag: Average capital during the year (SEK)
            year: Tax year (2025 or 2026)
            
        Returns:
            Dictionary with tax calculation details
        """
        if year == 2025:
            return self.calculate_isk_tax_2025(capital_underlag)
        elif year == 2026:
            return self.calculate_isk_tax_2026(capital_underlag)
        else:
            raise ValueError(f"Unsupported tax year: {year}. Supported years: 2025, 2026")
    
    def calculate_af_tax(self, realized_gains: float, dividends: float, 
                        fund_holdings: float) -> Dict[str, float]:
        """
        Calculate AF (Aktie- och fonddepå) account tax
        
        Tax components:
        - Capital gains: 30% on realized gains
        - Dividends: 30% (deducted at source)
        - Fund schablon: 0.12% annually on funds > 50,000 SEK
        
        Args:
            realized_gains: Realized capital gains (SEK)
            dividends: Dividend income (SEK)
            fund_holdings: Value of fund holdings (SEK)
            
        Returns:
            Dictionary with tax calculation details
        """
        self._validate_input(realized_gains, "realized_gains")
        self._validate_input(dividends, "dividends")
        self._validate_input(fund_holdings, "fund_holdings")
        
        # Calculate capital gains tax
        capital_gains_tax = realized_gains * self.AF_CAPITAL_GAINS_TAX_RATE
        
        # Calculate dividend tax (already deducted at source, but we show it)
        dividend_tax = dividends * self.AF_DIVIDEND_TAX_RATE
        
        # Calculate fund schablon tax (only on funds > 50,000 SEK)
        taxable_fund_value = max(0.0, fund_holdings - self.AF_FUND_THRESHOLD)
        fund_schablon_tax = taxable_fund_value * self.AF_FUND_SCHABLON_RATE
        
        # Total tax
        total_tax = capital_gains_tax + dividend_tax + fund_schablon_tax
        
        return {
            "realized_gains": round(realized_gains, 2),
            "dividends": round(dividends, 2),
            "fund_holdings": round(fund_holdings, 2),
            "capital_gains_tax": round(capital_gains_tax, 2),
            "dividend_tax": round(dividend_tax, 2),
            "fund_schablon_tax": round(fund_schablon_tax, 2),
            "total_tax": round(total_tax, 2),
            "capital_gains_tax_rate": round(self.AF_CAPITAL_GAINS_TAX_RATE * 100, 1),
            "dividend_tax_rate": round(self.AF_DIVIDEND_TAX_RATE * 100, 1),
            "fund_schablon_rate": round(self.AF_FUND_SCHABLON_RATE * 100, 3),
            "fund_threshold": round(self.AF_FUND_THRESHOLD, 2)
        }
    
    def calculate_tax(self, account_type: str, tax_year: int, 
                     capital_underlag: Optional[float] = None,
                     realized_gains: Optional[float] = None,
                     dividends: Optional[float] = None,
                     fund_holdings: Optional[float] = None) -> Dict[str, any]:
        """
        Main method to calculate tax based on account type
        
        Args:
            account_type: "ISK", "KF", or "AF"
            tax_year: 2025 or 2026
            capital_underlag: For ISK/KF accounts
            realized_gains: For AF accounts
            dividends: For AF accounts
            fund_holdings: For AF accounts
            
        Returns:
            Dictionary with tax calculation results
        """
        account_type = account_type.upper()
        
        if account_type in ["ISK", "KF"]:
            if capital_underlag is None:
                raise ValueError(f"capital_underlag is required for {account_type} accounts")
            
            if account_type == "ISK":
                if tax_year == 2025:
                    result = self.calculate_isk_tax_2025(capital_underlag)
                elif tax_year == 2026:
                    result = self.calculate_isk_tax_2026(capital_underlag)
                else:
                    raise ValueError(f"Unsupported tax year: {tax_year}")
            else:  # KF
                result = self.calculate_kf_tax(capital_underlag, tax_year)
            
            result["account_type"] = account_type
            result["tax_year"] = tax_year
            return result
            
        elif account_type == "AF":
            if realized_gains is None:
                realized_gains = 0.0
            if dividends is None:
                dividends = 0.0
            if fund_holdings is None:
                fund_holdings = 0.0
            
            result = self.calculate_af_tax(realized_gains, dividends, fund_holdings)
            result["account_type"] = account_type
            result["tax_year"] = tax_year
            return result
        else:
            raise ValueError(f"Unsupported account type: {account_type}. Supported: ISK, KF, AF")

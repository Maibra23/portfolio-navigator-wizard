from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional, Dict
import re

# Valid ticker pattern supporting international formats:
# - US: AAPL, MSFT, BRK.B (1-6 letters, optional .X class)
# - Swedish OMX: RAY-B.ST, HEXA-B.ST, ABB.ST (letters, optional -X class, .XX exchange)
# - European: ALM.MC (Madrid), SAP.DE (Germany), BP.L (London)
_TICKER_PATTERN = re.compile(r'^[A-Z0-9]{1,6}(-[A-Z0-9]{1,2})?(\.[A-Z]{1,3})?$')


class PortfolioAllocation(BaseModel):
    """Portfolio allocation with validated ticker symbol and allocation percentage."""
    symbol: str = Field(..., min_length=1, max_length=12, description="Stock ticker symbol")
    allocation: float = Field(..., ge=0.0, le=100.0, description="Allocation percentage (0-100)")
    name: Optional[str] = Field(None, max_length=200, description="Company name")
    assetType: Optional[Literal['stock', 'bond', 'etf']] = None

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate and normalize ticker symbol."""
        v = v.upper().strip()
        if not v:
            raise ValueError("Symbol cannot be empty")
        if not _TICKER_PATTERN.match(v):
            raise ValueError(f"Invalid ticker symbol format: {v}")
        return v

# Reusable risk profile type
RiskProfileType = Literal['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']


class PortfolioRequest(BaseModel):
    """Portfolio generation request with validated inputs."""
    riskProfile: RiskProfileType
    capital: float = Field(..., ge=1000, le=1_000_000_000, description="Investment capital (1,000 - 1B)")
    selectedStocks: List[PortfolioAllocation]

class PortfolioResponse(BaseModel):
    portfolio: List[PortfolioAllocation]
    name: str  # Add portfolio name
    description: str  # Add portfolio description
    expectedReturn: float
    risk: float
    diversificationScore: float
    isTopPick: Optional[bool] = False  # Add Top Pick flag

# New models for enhanced portfolio system
class PortfolioValidation(BaseModel):
    isValid: bool
    canProceed: bool
    warnings: List[str]

class PortfolioMetricsRequest(BaseModel):
    """Portfolio metrics calculation request."""
    allocations: List[PortfolioAllocation]
    riskProfile: RiskProfileType

class PortfolioMetricsResponse(BaseModel):
    expectedReturn: float
    risk: float
    diversificationScore: float
    sharpeRatio: float
    totalAllocation: float
    stockCount: int
    validation: PortfolioValidation 
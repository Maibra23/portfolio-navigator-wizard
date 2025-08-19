from pydantic import BaseModel
from typing import List, Literal, Optional, Dict

class PortfolioAllocation(BaseModel):
    symbol: str
    allocation: float
    name: Optional[str] = None
    assetType: Optional[Literal['stock', 'bond', 'etf']] = None

class PortfolioRequest(BaseModel):
    riskProfile: Literal['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
    capital: float
    selectedStocks: List[PortfolioAllocation]

class PortfolioResponse(BaseModel):
    portfolio: List[PortfolioAllocation]
    name: str  # Add portfolio name
    description: str  # Add portfolio description
    expectedReturn: float
    risk: float
    diversificationScore: float

# New models for enhanced portfolio system
class PortfolioValidation(BaseModel):
    isValid: bool
    canProceed: bool
    warnings: List[str]

class PortfolioMetricsRequest(BaseModel):
    allocations: List[PortfolioAllocation]
    riskProfile: str

class PortfolioMetricsResponse(BaseModel):
    expectedReturn: float
    risk: float
    diversificationScore: float
    sharpeRatio: float
    totalAllocation: float
    stockCount: int
    validation: PortfolioValidation 
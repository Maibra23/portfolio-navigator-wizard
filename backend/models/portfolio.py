from pydantic import BaseModel
from typing import List, Literal, Optional

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
    expectedReturn: float
    risk: float
    diversificationScore: float 
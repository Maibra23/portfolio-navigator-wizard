from pydantic import BaseModel
from typing import List, Literal

class PortfolioRequest(BaseModel):
    riskProfile: Literal['conservative', 'moderate', 'aggressive']
    capital: float
    selectedStocks: List[str]

class PortfolioAllocation(BaseModel):
    symbol: str
    allocation: float

class PortfolioResponse(BaseModel):
    portfolio: List[PortfolioAllocation]
    expectedReturn: float
    risk: float 
from fastapi import APIRouter
from models.portfolio import PortfolioRequest, PortfolioResponse, PortfolioAllocation

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

@router.post("", response_model=PortfolioResponse)
def create_portfolio(data: PortfolioRequest):
    # Dummy allocation logic
    n = len(data.selectedStocks)
    allocation = 100 / n if n else 0
    portfolio = [PortfolioAllocation(symbol=s, allocation=allocation) for s in data.selectedStocks]
    return PortfolioResponse(
        portfolio=portfolio,
        expectedReturn=0.08,
        risk=0.12
    ) 
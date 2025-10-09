from fastapi.testclient import TestClient
from main import app

def test_read_root():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "FastAPI backend is running." 

def test_portfolio_endpoint():
    client = TestClient(app)
    payload = {
        "riskProfile": "moderate",
        "capital": 10000,
        "selectedStocks": ["AAPL", "GOOG"]
    }
    response = client.post("/api/portfolio", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "portfolio" in data
    assert isinstance(data["portfolio"], list)
    assert len(data["portfolio"]) == 2
    assert "expectedReturn" in data
    assert "risk" in data 
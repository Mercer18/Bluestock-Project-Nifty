"""
Unit tests for FastAPI Health Endpoint.
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "db_row_counts" in data
    assert "uptime_seconds" in data
    assert "version" in data
    
    # Verify all 10 tables are represented in row counts
    tables = [
        "companies", "profitandloss", "balancesheet", "cashflow", "analysis",
        "documents", "prosandcons", "sectors", "stock_prices", "financial_ratios"
    ]
    for table in tables:
        assert table in data["db_row_counts"]
        assert data["db_row_counts"][table] >= 0

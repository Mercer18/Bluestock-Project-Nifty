"""
Unit tests for FastAPI Screener Endpoint.
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_screener_valid_min_roe():
    response = client.get("/api/v1/screener?min_roe=15.0")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for row in data:
        assert row["roe"] >= 15.0

def test_screener_multiple_filters():
    response = client.get("/api/v1/screener?min_roe=15.0&max_de=1.0&min_fcf=0.0")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for row in data:
        assert row["roe"] >= 15.0
        # Financials are ignored for D/E check
        if row["sector"] != "Financials":
            assert row["de"] <= 1.0
        assert row["fcf"] >= 0.0

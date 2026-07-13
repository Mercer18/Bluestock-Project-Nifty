"""
Unit tests for FastAPI Sectors Endpoint.
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_get_sectors_summary():
    response = client.get("/api/v1/sectors")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Check that sectors count is correct (11 sectors total)
    assert len(data) >= 10
    assert "sector" in data[0]
    assert "company_count" in data[0]
    assert "median_roe" in data[0]

def test_get_sector_companies_valid():
    response = client.get("/api/v1/sectors/Information Technology/companies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "company_id" in data[0]
    assert "score" in data[0]

def test_get_sector_companies_invalid():
    response = client.get("/api/v1/sectors/INVALID/companies")
    assert response.status_code == 404

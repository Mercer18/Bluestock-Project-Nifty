"""
Unit tests for FastAPI Companies Endpoint.
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_get_companies_list():
    response = client.get("/api/v1/companies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 92  # Nifty 100 constituent count
    assert "company_name" in data[0]
    assert "roe_pct" in data[0]

def test_get_companies_filtered():
    response = client.get("/api/v1/companies?sector=Information Technology")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for c in data:
        assert c["broad_sector"] == "Information Technology"

def test_get_company_profile_valid():
    response = client.get("/api/v1/companies/TCS")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "TCS"
    assert data["company_name"] == "Tata Consultancy Services Ltd"
    assert "sector" in data
    assert "latest_ratios" in data

def test_get_company_profile_invalid():
    response = client.get("/api/v1/companies/INVALID")
    assert response.status_code == 404
    assert "detail" in response.json()

# tests/test_api.py

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Smart Trash Server is running"}

def test_stats_endpoint():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    # Kỳ vọng các trường chính có trong response
    assert "waste_counts" in data
    assert "daily_stats" in data
    assert "specific_waste" in data

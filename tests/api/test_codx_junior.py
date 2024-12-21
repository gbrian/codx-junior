import os
import httpx
import pytest


@pytest.fixture
def api_client():
    api_port = os.getenv('API_PORT', '8000')  # Default to 8000 if API_PORT is not set
    base_url = f"http://localhost:{api_port}"
    return httpx.Client(base_url=base_url)

def test_get_root(api_client):
    response = api_client.get("/")
    assert response.status_code == 200
    assert "Welcome to codx-junior" in response.text

def test_some_feature(api_client):
    response = api_client.get("/some-feature")
    assert response.status_code == 200
    # Add more assertions based on the expected output

@codx: --knowledge add tests for all endpoints at app.py
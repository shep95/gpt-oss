import pytest
from fastapi import status
from fastapi.testclient import TestClient
from gpt_oss.responses_api.api_server import create_api_server


@pytest.fixture
def simple_client():
    """Create a test client without harmony encoding for simple endpoint tests"""
    # Create a mock infer function that just returns 0
    def mock_infer(tokens, temperature):
        return 0
    
    # Create a mock encoding object
    class MockEncoding:
        def encode(self, text, allowed_special=None):
            return [1, 2, 3]
    
    app = create_api_server(
        infer_next_token=mock_infer,
        encoding=MockEncoding()
    )
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the /health endpoint used by Railway and other deployment platforms"""
    
    def test_health_endpoint_exists(self, simple_client):
        """Test that the health endpoint exists and responds"""
        response = simple_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
    
    def test_health_endpoint_returns_json(self, simple_client):
        """Test that the health endpoint returns JSON"""
        response = simple_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
    
    def test_health_endpoint_status(self, simple_client):
        """Test that the health endpoint returns a status field"""
        response = simple_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_health_endpoint_always_available(self, simple_client):
        """Test that health endpoint works multiple times"""
        for _ in range(5):
            response = simple_client.get("/health")
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["status"] == "healthy"

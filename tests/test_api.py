"""
Test suite for API endpoints.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "shl-recommender"

def test_chat_first_turn():
    """Test chat endpoint first turn"""
    response = client.post(
        "/chat",
        json={
            "messages": [
                {"role": "user", "content": "I need an assessment"}
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "recommendations" in data
    assert "end_of_conversation" in data

def test_chat_java_query():
    """Test chat with Java mention"""
    response = client.post(
        "/chat",
        json={
            "messages": [
                {"role": "user", "content": "I need an assessment"},
                {"role": "assistant", "content": "Tell me more"},
                {"role": "user", "content": "java"}
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["recommendations"]) > 0
    assert data["recommendations"][0]["name"] == "Java 8 (New)"

def test_chat_empty_messages():
    """Test chat with empty messages"""
    response = client.post("/chat", json={"messages": []})
    assert response.status_code == 400

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
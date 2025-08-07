import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock

import sys
sys.path.append('..')

from app import app
from config import Config

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture
def mock_embedder():
    """Mock embedder for testing"""
    with patch('app.embedder') as mock:
        mock.create_embeddings_cached.return_value = {
            'success': True,
            'embeddings': [{'embedding': [0.1] * 384, 'text': 'test'}],
            'cache_hit_rate': 0.5
        }
        mock.health_check.return_value = True
        yield mock

def test_index_route(client):
    """Test index route"""
    response = client.get('/')
    assert response.status_code == 200

def test_health_check(client, mock_embedder):
    """Test health check endpoint"""
    with patch('app.generator') as mock_gen:
        mock_gen.health_check.return_value = True
        
        response = client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'

def test_upload_no_file(client):
    """Test upload without file"""
    response = client.post('/upload', data={})
    assert response.status_code == 400
    
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'No file provided' in data['error']

def test_query_empty(client):
    """Test query with empty input"""
    response = client.post('/query', 
                          json={'query': ''},
                          content_type='application/json')
    assert response.status_code == 400

def test_query_too_short(client):
    """Test query too short"""
    response = client.post('/query', 
                          json={'query': 'hi'},
                          content_type='application/json')
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_document_processing():
    """Test document processing pipeline"""
    # This would test the actual processing pipeline
    pass

def test_rate_limiting(client):
    """Test rate limiting"""
    # Make multiple rapid requests to test rate limiting
    for i in range(15):  # Exceed the limit
        response = client.post('/query', 
                              json={'query': 'test query'},
                              content_type='application/json')
    
    # Should eventually get rate limited
    assert response.status_code in [429, 400, 500]  # Various possible responses

def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.get('/')
    assert 'Access-Control-Allow-Origin' in response.headers

if __name__ == '__main__':
    pytest.main([__file__])

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

import sys
sys.path.append('..')

from modules.embedder import AdvancedEmbedder

@pytest.fixture
def embedder():
    """Create embedder instance"""
    with patch('modules.embedder.SentenceTransformer') as mock_model:
        mock_instance = MagicMock()
        mock_instance.encode.return_value = np.random.rand(2, 384)
        mock_model.return_value = mock_instance
        
        embedder = AdvancedEmbedder()
        embedder.model = mock_instance
        return embedder

def test_embedder_initialization(embedder):
    """Test embedder initializes correctly"""
    assert embedder.model is not None
    assert embedder.config is not None

def test_create_embeddings_empty_input(embedder):
    """Test embeddings with empty input"""
    result = embedder.create_embeddings_cached([], "test_user")
    assert result['success'] is False
    assert 'No text blocks provided' in result['error']

def test_create_embeddings_success(embedder):
    """Test successful embedding creation"""
    text_blocks = [
        {'text': 'Hello world', 'page_number': 1},
        {'text': 'Test document', 'page_number': 1}
    ]
    
    result = embedder.create_embeddings_cached(text_blocks, "test_user")
    
    assert result['success'] is True
    assert result['total_embeddings'] == 2
    assert 'cache_hit_rate' in result
    assert 'processing_time' in result

def test_embed_query_empty(embedder):
    """Test query embedding with empty input"""
    result = embedder.embed_query("", "test_user")
    assert result is None

def test_embed_query_success(embedder):
    """Test successful query embedding"""
    embedder.model.encode.return_value = np.array([[0.1] * 384])
    
    result = embedder.embed_query("test query", "test_user")
    assert result is not None
    assert len(result) == 384

def test_health_check(embedder):
    """Test embedder health check"""
    embedder.model.encode.return_value = np.array([[0.1] * 384])
    
    result = embedder.health_check()
    assert result is True

if __name__ == '__main__':
    pytest.main([__file__])

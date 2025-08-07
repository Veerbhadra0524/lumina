#!/usr/bin/env python3
"""Test Phase 2 enhancements"""

from modules.retriever import Retriever
from modules.text_extractor import TextExtractor
import json

def test_hybrid_search():
    """Test hybrid search functionality"""
    print("🔍 Testing Hybrid Search...")
    
    retriever = Retriever(user_id="test_user")
    
    # Test with a sample query
    result = retriever.retrieve("machine learning", max_results=5)
    
    print(f"Search method: {result.get('search_method', 'unknown')}")
    print(f"Results found: {result.get('total_results', 0)}")
    
    for doc in result.get('documents', [])[:2]:
        print(f"- Score: {doc.get('hybrid_score', doc.get('similarity_score', 0)):.3f}")
        print(f"- Text: {doc.get('text', '')[:100]}...")

def test_semantic_chunking():
    """Test semantic chunking"""
    print("\n🧠 Testing Semantic Chunking...")
    
    extractor = TextExtractor()
    print(f"Chunking model available: {extractor.chunking_model is not None}")

if __name__ == "__main__":
    test_hybrid_search()
    test_semantic_chunking()
    print("\n✅ Phase 2 testing completed!")

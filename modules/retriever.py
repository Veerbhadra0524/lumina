import logging
from typing import Dict, Any, List
from modules.vector_store import VectorStore
from modules.embedder import Embedder

logger = logging.getLogger(__name__)

class Retriever:
    """Handles document retrieval and ranking"""
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.vector_store = VectorStore(user_id=user_id)  # User-specific store
        self.embedder = Embedder()
    
    def retrieve(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Retrieve documents for specific user"""
        try:
            if not query.strip():
                return {'success': False, 'error': 'Empty query'}
            
            query_embedding = self.embedder.embed_query(query)
            if not query_embedding:
                return {'success': False, 'error': 'Failed to create query embedding'}
            
            # Search user-specific vector store
            search_result = self.vector_store.search(query_embedding, max_results)
            
            if not search_result['success']:
                return search_result
            
            documents = search_result['documents']
            filtered_docs = self._filter_and_rank(documents, query)
            
            return {
                'success': True,
                'documents': filtered_docs,
                'query': query,
                'user_id': self.user_id,
                'total_results': len(filtered_docs)
            }
            
        except Exception as e:
            logger.error(f"Retrieval error for user {self.user_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _filter_and_rank(self, documents: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Filter and rank retrieved documents"""
        try:
            # Filter by similarity threshold
            MIN_SIMILARITY = 0.1
            filtered = [doc for doc in documents if doc.get('similarity_score', 0) > MIN_SIMILARITY]
            
            # Sort by similarity score (descending)
            filtered.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            
            # Add relevance information
            for i, doc in enumerate(filtered):
                doc['relevance_rank'] = i + 1
                doc['confidence'] = self._calculate_confidence(doc)
            
            return filtered
            
        except Exception as e:
            logger.error(f"Filtering error: {str(e)}")
            return documents
    
    def _calculate_confidence(self, document: Dict[str, Any]) -> float:
        """Calculate confidence score for a document"""
        try:
            # Base confidence from similarity
            similarity = document.get('similarity_score', 0)
            confidence = similarity
            
            # Boost confidence for high OCR confidence
            ocr_confidence = document.get('confidence', 50) / 100.0
            confidence = confidence * (0.8 + 0.2 * ocr_confidence)
            
            # Ensure confidence is between 0 and 1
            confidence = max(0.0, min(1.0, confidence))
            
            return confidence
            
        except Exception as e:
            logger.error(f"Confidence calculation error: {str(e)}")
            return 0.5

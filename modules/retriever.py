import logging
from typing import Dict, Any, List, Optional
from modules.vector_store import VectorStore
from modules.embedder import Embedder

logger = logging.getLogger(__name__)

class Retriever:
    """Simplified retriever focused on accuracy"""
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.vector_store = VectorStore(user_id=user_id)
        self.embedder = Embedder()
        
        # Phase 2 Fix: Make BM25 optional
        self.bm25_index = None
        self.use_hybrid = False  # Start with semantic only
        
        # Try to build BM25, but don't fail if it doesn't work
        try:
            self._build_bm25_index()
            self.use_hybrid = True
        except Exception as e:
            logger.info(f"BM25 disabled for user {self.user_id}: {str(e)}")
    
    def _build_bm25_index(self):
        """Safely build BM25 index"""
        try:
            if hasattr(self.vector_store, 'metadata') and self.vector_store.metadata:
                texts = []
                for doc in self.vector_store.metadata:
                    if 'text' in doc and doc['text'].strip():
                        texts.append(doc['text'])
                
                if texts:
                    from rank_bm25 import BM25Okapi
                    tokenized_docs = [doc.split() for doc in texts]
                    self.bm25_index = BM25Okapi(tokenized_docs)
                    logger.info(f"✅ Built BM25 index with {len(texts)} documents for user {self.user_id}")
            
        except Exception as e:
            logger.warning(f"BM25 index building failed: {str(e)}")
            self.bm25_index = None
    
    def retrieve(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Retrieve with focus on preserving confidence"""
        try:
            if not query.strip():
                return {'success': False, 'error': 'Empty query'}
            
            # Phase 2 Fix: Use simple semantic search by default
            if self.use_hybrid and self.bm25_index:
                return self._simplified_hybrid_retrieve(query, max_results)
            else:
                return self._semantic_retrieve(query, max_results)
                
        except Exception as e:
            logger.error(f"Retrieval error for user {self.user_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _simplified_hybrid_retrieve(self, query: str, max_results: int) -> Dict[str, Any]:
        """Phase 2 Fix: Simplified hybrid search that preserves confidence"""
        try:
            # Get semantic results
            semantic_results = self._semantic_retrieve(query, max_results * 2)
            if not semantic_results.get('success', False):
                return semantic_results
            
            semantic_docs = semantic_results.get('documents', [])
            
            # Phase 2 Fix: Light hybrid boost instead of complex scoring
            for doc in semantic_docs:
                text = doc.get('text', '').lower()
                query_lower = query.lower()
                
                # Simple keyword boost
                query_words = query_lower.split()
                word_matches = sum(1 for word in query_words if word in text)
                
                if word_matches > 0:
                    # Light boost for keyword matches (max 10% boost)
                    keyword_boost = min(0.1, (word_matches / len(query_words)) * 0.1)
                    original_score = doc.get('similarity_score', 0)
                    doc['similarity_score'] = min(1.0, original_score + keyword_boost)
                    doc['keyword_boost'] = keyword_boost
                else:
                    doc['keyword_boost'] = 0
                
                doc['search_method'] = 'light_hybrid'
            
            # Re-sort by boosted scores
            semantic_docs.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            
            # Apply simple filtering
            final_results = self._simple_filter_and_rank(semantic_docs[:max_results], query)
            
            return {
                'success': True,
                'documents': final_results,
                'query': query,
                'user_id': self.user_id,
                'total_results': len(final_results),
                'search_method': 'light_hybrid'
            }
            
        except Exception as e:
            logger.error(f"Hybrid retrieval error: {str(e)}")
            return self._semantic_retrieve(query, max_results)
    
    def _semantic_retrieve(self, query: str, max_results: int) -> Dict[str, Any]:
        """Clean semantic retrieval"""
        try:
            query_embedding = self.embedder.embed_query(query, self.user_id)
            if not query_embedding:
                return {'success': False, 'error': 'Failed to create query embedding'}
            
            search_result = self.vector_store.search(query_embedding, max_results)
            if not search_result.get('success', False):
                return search_result
            
            documents = search_result.get('documents', [])
            filtered_docs = self._simple_filter_and_rank(documents, query)
            
            return {
                'success': True,
                'documents': filtered_docs,
                'query': query,
                'user_id': self.user_id,
                'total_results': len(filtered_docs),
                'search_method': 'semantic'
            }
            
        except Exception as e:
            logger.error(f"Semantic retrieval error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _simple_filter_and_rank(self, documents: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Phase 2 Fix: Simple filtering that preserves original confidence"""
        try:
            # Phase 2 Fix: Lower threshold to include more results
            MIN_SIMILARITY = 0.05
            filtered = [doc for doc in documents if doc.get('similarity_score', 0) > MIN_SIMILARITY]
            
            # Sort by similarity
            filtered.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            
            # Phase 2 Fix: Simple confidence that preserves original scores
            for i, doc in enumerate(filtered):
                doc['relevance_rank'] = i + 1
                
                # Preserve original confidence from OCR
                original_confidence = doc.get('confidence', 0.5)
                retrieval_score = doc.get('similarity_score', 0)
                
                # Simple confidence: weighted average favoring original OCR confidence
                final_confidence = (0.7 * original_confidence + 0.3 * retrieval_score)
                
                # Don't let confidence drop too much
                doc['confidence'] = max(original_confidence * 0.8, final_confidence)
            
            return filtered
            
        except Exception as e:
            logger.error(f"Simple filtering error: {str(e)}")
            return documents

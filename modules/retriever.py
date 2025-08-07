import logging
from typing import Dict, Any, List, Optional
import numpy as np
from rank_bm25 import BM25Okapi
from modules.vector_store import VectorStore
from modules.embedder import Embedder

logger = logging.getLogger(__name__)

class Retriever:
    """Advanced retrieval with hybrid semantic-keyword search"""
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.vector_store = VectorStore(user_id=user_id)
        self.embedder = Embedder()
        
        # Phase 2: BM25 keyword search
        self.bm25_index = None
        self.document_texts = []
        self.document_metadata = []
        self._build_bm25_index()
    
    def _build_bm25_index(self):
        """Build BM25 index from existing documents"""
        try:
            # Get all documents from vector store
            if hasattr(self.vector_store, 'metadata') and self.vector_store.metadata:
                texts = []
                metadata = []
                
                for doc in self.vector_store.metadata:
                    if 'text' in doc:
                        texts.append(doc['text'])
                        metadata.append(doc)
                
                if texts:
                    # Tokenize for BM25
                    tokenized_docs = [doc.split() for doc in texts]
                    self.bm25_index = BM25Okapi(tokenized_docs)
                    self.document_texts = texts
                    self.document_metadata = metadata
                    logger.info(f"✅ Built BM25 index with {len(texts)} documents for user {self.user_id}")
                else:
                    logger.info(f"📝 No documents found for BM25 index for user {self.user_id}")
            
        except Exception as e:
            logger.warning(f"BM25 index building failed: {str(e)}")
            self.bm25_index = None
    
    def retrieve(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Enhanced retrieval with hybrid search"""
        try:
            if not query.strip():
                return {'success': False, 'error': 'Empty query'}
            
            # Phase 2: Use hybrid search if BM25 available
            if self.bm25_index and len(self.document_texts) > 0:
                return self._hybrid_retrieve(query, max_results)
            else:
                return self._semantic_retrieve(query, max_results)
                
        except Exception as e:
            logger.error(f"Retrieval error for user {self.user_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _hybrid_retrieve(self, query: str, max_results: int) -> Dict[str, Any]:
        """Phase 2: Hybrid semantic + keyword retrieval"""
        try:
            # 1. Semantic search
            semantic_results = self._semantic_retrieve(query, max_results * 2)
            if not semantic_results.get('success', False):
                return semantic_results
            
            semantic_docs = semantic_results.get('documents', [])
            
            # 2. Keyword search with BM25
            keyword_scores = self.bm25_index.get_scores(query.split())
            
            # 3. Combine scores with weighted fusion
            hybrid_results = []
            semantic_weight = 0.7
            keyword_weight = 0.3
            
            for doc in semantic_docs:
                doc_text = doc.get('text', '')
                # Find matching document in BM25 results
                keyword_score = 0
                for i, text in enumerate(self.document_texts):
                    if self._text_similarity(doc_text, text) > 0.9:
                        keyword_score = keyword_scores[i] if i < len(keyword_scores) else 0
                        break
                
                # Normalize BM25 score (simple normalization)
                max_keyword_score = max(keyword_scores) if keyword_scores.size > 0 else 1
                normalized_keyword = keyword_score / max_keyword_score if max_keyword_score > 0 else 0
                
                # Combine scores
                semantic_score = doc.get('similarity_score', 0)
                hybrid_score = (semantic_weight * semantic_score + 
                              keyword_weight * normalized_keyword)
                
                doc['hybrid_score'] = hybrid_score
                doc['keyword_score'] = normalized_keyword
                doc['search_method'] = 'hybrid'
                hybrid_results.append(doc)
            
            # Sort by hybrid score
            hybrid_results.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
            
            # Apply enhanced filtering and ranking
            final_results = self._enhanced_filter_and_rank(hybrid_results[:max_results], query)
            
            logger.info(f"🔍 Hybrid search returned {len(final_results)} results for user {self.user_id}")
            
            return {
                'success': True,
                'documents': final_results,
                'query': query,
                'user_id': self.user_id,
                'total_results': len(final_results),
                'search_method': 'hybrid'
            }
            
        except Exception as e:
            logger.error(f"Hybrid retrieval error: {str(e)}")
            # Fallback to semantic search
            return self._semantic_retrieve(query, max_results)
    
    def _semantic_retrieve(self, query: str, max_results: int) -> Dict[str, Any]:
        """Original semantic retrieval (backward compatible)"""
        try:
            query_embedding = self.embedder.embed_query(query, self.user_id)
            if not query_embedding:
                return {'success': False, 'error': 'Failed to create query embedding'}
            
            search_result = self.vector_store.search(query_embedding, max_results)
            if not search_result.get('success', False):
                return search_result
            
            documents = search_result.get('documents', [])
            filtered_docs = self._filter_and_rank(documents, query)
            
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
    
    def _filter_and_rank(self, documents: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Original filtering (backward compatible)"""
        try:
            MIN_SIMILARITY = 0.1
            filtered = [doc for doc in documents if doc.get('similarity_score', 0) > MIN_SIMILARITY]
            filtered.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            
            for i, doc in enumerate(filtered):
                doc['relevance_rank'] = i + 1
                doc['confidence'] = self._calculate_confidence(doc)
            
            return filtered
            
        except Exception as e:
            logger.error(f"Filtering error: {str(e)}")
            return documents
    
    def _enhanced_filter_and_rank(self, documents: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Phase 2: Enhanced filtering with multi-factor confidence"""
        try:
            MIN_SIMILARITY = 0.05  # Lower threshold for hybrid search
            filtered = [doc for doc in documents if doc.get('hybrid_score', doc.get('similarity_score', 0)) > MIN_SIMILARITY]
            
            # Sort by hybrid score if available, otherwise similarity
            sort_key = 'hybrid_score' if filtered and 'hybrid_score' in filtered[0] else 'similarity_score'
            filtered.sort(key=lambda x: x.get(sort_key, 0), reverse=True)
            
            for i, doc in enumerate(filtered):
                doc['relevance_rank'] = i + 1
                doc['confidence'] = self._calculate_enhanced_confidence(doc, query)
                doc['boost_applied'] = self._apply_relevance_boost(doc, query)
            
            return filtered
            
        except Exception as e:
            logger.error(f"Enhanced filtering error: {str(e)}")
            return self._filter_and_rank(documents, query)
    
    def _calculate_confidence(self, document: Dict[str, Any]) -> float:
        """Original confidence calculation (backward compatible)"""
        try:
            similarity = document.get('similarity_score', 0)
            confidence = similarity
            
            ocr_confidence = document.get('confidence', 50) / 100.0
            confidence = confidence * (0.8 + 0.2 * ocr_confidence)
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"Confidence calculation error: {str(e)}")
            return 0.5
    
    def _calculate_enhanced_confidence(self, document: Dict[str, Any], query: str) -> float:
        """Phase 2: Multi-factor confidence scoring"""
        try:
            factors = {}
            
            # Factor 1: Retrieval similarity
            factors['retrieval_score'] = document.get('hybrid_score', document.get('similarity_score', 0))
            
            # Factor 2: OCR confidence
            factors['ocr_confidence'] = document.get('confidence', 50) / 100.0
            
            # Factor 3: Text length (longer texts often more reliable)
            text_length = len(document.get('text', ''))
            factors['text_length'] = min(text_length / 200, 1.0)  # Normalize to 0-1
            
            # Factor 4: Query term overlap
            factors['query_overlap'] = self._calculate_query_overlap(document.get('text', ''), query)
            
            # Factor 5: Document recency (if available)
            factors['recency'] = 0.8  # Default neutral value
            
            # Factor 6: Keyword score boost (for hybrid search)
            factors['keyword_boost'] = document.get('keyword_score', 0) * 0.5
            
            # Weighted combination
            weights = {
                'retrieval_score': 0.35,
                'ocr_confidence': 0.20,
                'text_length': 0.10,
                'query_overlap': 0.20,
                'recency': 0.10,
                'keyword_boost': 0.05
            }
            
            final_confidence = sum(factors[factor] * weights[factor] for factor in factors)
            
            # Ensure bounds
            return max(0.05, min(0.95, final_confidence))
            
        except Exception as e:
            logger.error(f"Enhanced confidence calculation error: {str(e)}")
            return self._calculate_confidence(document)
    
    def _calculate_query_overlap(self, text: str, query: str) -> float:
        """Calculate how many query terms appear in the text"""
        try:
            query_terms = set(query.lower().split())
            text_terms = set(text.lower().split())
            
            if not query_terms:
                return 0.0
            
            overlap = len(query_terms.intersection(text_terms))
            return overlap / len(query_terms)
            
        except Exception:
            return 0.0
    
    def _apply_relevance_boost(self, document: Dict[str, Any], query: str) -> bool:
        """Apply relevance boosts for high-quality matches"""
        try:
            text = document.get('text', '').lower()
            query_lower = query.lower()
            
            # Boost for exact phrase matches
            if query_lower in text:
                current_score = document.get('hybrid_score', document.get('similarity_score', 0))
                document['hybrid_score'] = min(1.0, current_score * 1.2)
                return True
            
            # Boost for title/header indicators
            title_indicators = ['title', 'heading', 'header', 'subject']
            if any(indicator in document.get('method', '').lower() for indicator in title_indicators):
                current_score = document.get('hybrid_score', document.get('similarity_score', 0))
                document['hybrid_score'] = min(1.0, current_score * 1.1)
                return True
            
            return False
            
        except Exception:
            return False
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity for matching"""
        try:
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union)
            
        except Exception:
            return 0.0
    
    def update_bm25_index(self):
        """Rebuild BM25 index when new documents are added"""
        self._build_bm25_index()
        logger.info(f"🔄 Updated BM25 index for user {self.user_id}")

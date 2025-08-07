import os
import json
import faiss
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from config import Config

logger = logging.getLogger(__name__)

class VectorStore:
    """Handles FAISS vector database operations"""
    
    def __init__(self, user_id: str = "default"):
        self.config = Config()
        self.user_id = user_id
        
        # Create user-specific paths
        self.user_path = os.path.join(self.config.VECTOR_STORE_PATH, self.user_id)
        os.makedirs(self.user_path, exist_ok=True)
        
        self.index_path = os.path.join(self.user_path, 'faiss.index')
        self.metadata_path = os.path.join(self.user_path, 'metadata.json')
        
        self.index = None
        self.metadata = []
        self._initialize_index()

    
    def _initialize_index(self):
        """Initialize or load user-specific FAISS index"""
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
                self.index = faiss.read_index(self.index_path)
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.info(f"👤 User {self.user_id}: Loaded index with {self.index.ntotal} vectors")
            else:
                self.index = faiss.IndexFlatIP(self.config.EMBEDDING_DIMENSION)
                self.metadata = []
                logger.info(f"👤 User {self.user_id}: Created new index")
                
        except Exception as e:
            logger.error(f"Index initialization error for user {self.user_id}: {str(e)}")
            self.index = faiss.IndexFlatIP(self.config.EMBEDDING_DIMENSION)
            self.metadata = []
    
    def add_documents(self, embedding_data: List[Dict[str, Any]], upload_id: str) -> Dict[str, Any]:
        """Add document embeddings to the vector store"""
        try:
            if not embedding_data:
                return {'success': False, 'error': 'No embeddings provided'}
            
            # Prepare embeddings and metadata
            embeddings = []
            new_metadata = []
            logger.debug(f"🔍 embedding_data sample: {embedding_data[0]}")

            
            for item in embedding_data:
                embedding = np.array(item['embedding'], dtype=np.float32)
                
                # Normalize embedding for cosine similarity
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                
                embeddings.append(embedding)
                
                # Add metadata with upload info
                metadata = item['metadata'].copy()
                metadata['upload_id'] = upload_id
                metadata['text'] = item['text']
                metadata['added_at'] = str(datetime.now())
                metadata['vector_id'] = self.index.ntotal + len(new_metadata)
                
                new_metadata.append(metadata)
            
            # Convert to numpy array
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Add to index
            self.index.add(embeddings_array)
            self.metadata.extend(new_metadata)
            
            # Save updated index and metadata
            self._save_index()
            
            logger.info(f"Added {len(embeddings)} vectors to index. Total: {self.index.ntotal}")
            
            return {
                'success': True,
                'vectors_added': len(embeddings),
                'total_vectors': self.index.ntotal
            }
            
        except Exception as e:
            logger.error(f"Document addition error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def search(self, query_embedding: List[float], k: int = 5) -> Dict[str, Any]:
        """Search for similar documents"""
        try:
            if self.index.ntotal == 0:
                return {
                    'success': True,
                    'documents': [],
                    'message': 'No documents in index'
                }
            
            # Prepare query embedding
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # Normalize for cosine similarity
            norm = np.linalg.norm(query_vector)
            if norm > 0:
                query_vector = query_vector / norm
            
            # Search
            k = min(k, self.index.ntotal)  # Don't search for more than available
            distances, indices = self.index.search(query_vector, k)
            
            # Prepare results
            documents = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.metadata):
                    doc = self.metadata[idx].copy()
                    doc['similarity_score'] = float(distance)  # Cosine similarity
                    doc['rank'] = i + 1
                    documents.append(doc)
            
            return {
                'success': True,
                'documents': documents,
                'total_results': len(documents)
            }
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _save_index(self):
        """Save index and metadata to disk"""
        try:
            os.makedirs(self.config.VECTOR_STORE_PATH, exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, self.index_path)
            
            # Save metadata
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Save error: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        try:
            return {
                'total_documents': self.index.ntotal if self.index else 0,
                'embedding_dimension': self.config.EMBEDDING_DIMENSION,
                'index_type': 'FAISS IndexFlatIP',
                'metadata_entries': len(self.metadata)
            }
        except Exception as e:
            logger.error(f"Stats error: {str(e)}")
            return {'error': str(e)}
    
    def clear_index(self) -> Dict[str, Any]:
        """Clear the entire index (for testing/reset)"""
        try:
            self.index = faiss.IndexFlatIP(self.config.EMBEDDING_DIMENSION)
            self.metadata = []
            self._save_index()
            
            return {'success': True, 'message': 'Index cleared'}
            
        except Exception as e:
            logger.error(f"Clear error: {str(e)}")
            return {'success': False, 'error': str(e)}

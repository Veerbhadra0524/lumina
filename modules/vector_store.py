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
    """Enhanced FAISS vector database operations with user isolation"""
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.vector_store_path = Config.VECTOR_STORE_PATH
        
        # Initialize index and metadata as None first
        self.index = None
        self.metadata = []
        
        if user_id:
            # Create user-specific directory
            self.user_path = os.path.join(self.vector_store_path, f"user_{user_id}")
            os.makedirs(self.user_path, exist_ok=True)
            self.index_path = os.path.join(self.user_path, "faiss_index.bin")
            self.metadata_path = os.path.join(self.user_path, "metadata.json")
        else:
            # Fallback to general path
            os.makedirs(self.vector_store_path, exist_ok=True)
            self.index_path = os.path.join(self.vector_store_path, "faiss_index.bin")
            self.metadata_path = os.path.join(self.vector_store_path, "metadata.json")
        
        # Initialize the index AFTER paths are set
        self._initialize_index()
        
    def _initialize_index(self):
        """Initialize or load user-specific FAISS index"""
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
                # Load existing index
                self.index = faiss.read_index(self.index_path)
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.info(f"USER: User {self.user_id}: Loaded index with {self.index.ntotal} vectors")
            else:
                # Create new index
                self.index = faiss.IndexFlatIP(Config.EMBEDDING_DIMENSION)
                self.metadata = []
                logger.info(f"USER: User {self.user_id}: Created new index")
                
        except Exception as e:
            logger.error(f"Index initialization error for user {self.user_id}: {str(e)}")
            # Fallback to new index
            self.index = faiss.IndexFlatIP(Config.EMBEDDING_DIMENSION)
            self.metadata = []
    
    def add_documents(self, embedding_data: List[Dict[str, Any]], upload_id: str) -> Dict[str, Any]:
        """Add document embeddings to the vector store"""
        try:
            if not embedding_data:
                return {'success': False, 'error': 'No embeddings provided'}
            
            # Ensure index is initialized
            if self.index is None:
                self._initialize_index()
            
            # Prepare embeddings and metadata
            embeddings = []
            new_metadata = []
            
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
                metadata['user_id'] = self.user_id  # Ensure user isolation
                
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
            # Ensure index is initialized
            if self.index is None:
                self._initialize_index()
                
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
            k = min(k, self.index.ntotal)
            distances, indices = self.index.search(query_vector, k)
            
            # Prepare results with user filtering
            documents = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.metadata):
                    doc = self.metadata[idx].copy()
                    
                    # Double-check user isolation
                    if self.user_id and doc.get('user_id') != self.user_id:
                        continue
                    
                    doc['similarity_score'] = float(distance)
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
            # Ensure directory exists
            if self.user_id:
                os.makedirs(self.user_path, exist_ok=True)
            else:
                os.makedirs(self.vector_store_path, exist_ok=True)
            
            # Save FAISS index
            if self.index is not None:
                faiss.write_index(self.index, self.index_path)
            
            # Save metadata with user isolation
            metadata_to_save = []
            for item in self.metadata:
                # Ensure user_id is set
                if self.user_id:
                    item['user_id'] = self.user_id
                metadata_to_save.append(item)
            
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_to_save, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Save error: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        try:
            if self.index is None:
                self._initialize_index()
                
            return {
                'user_id': self.user_id,
                'total_documents': self.index.ntotal if self.index else 0,
                'embedding_dimension': Config.EMBEDDING_DIMENSION,
                'index_type': 'FAISS IndexFlatIP',
                'metadata_entries': len(self.metadata),
                'index_path': self.index_path
            }
        except Exception as e:
            logger.error(f"Stats error: {str(e)}")
            return {'error': str(e)}
    
    def clear_user_data(self) -> Dict[str, Any]:
        """Clear all data for current user"""
        try:
            self.index = faiss.IndexFlatIP(Config.EMBEDDING_DIMENSION)
            self.metadata = []
            self._save_index()
            
            logger.info(f"Cleared all data for user {self.user_id}")
            return {'success': True, 'message': f'User {self.user_id} data cleared'}
            
        except Exception as e:
            logger.error(f"Clear error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def health_check(self) -> bool:
        """Check if vector store is healthy"""
        try:
            if self.index is None:
                self._initialize_index()
            return self.index is not None
        except:
            return False

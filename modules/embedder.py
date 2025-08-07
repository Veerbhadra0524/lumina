import logging
import structlog
import numpy as np
from typing import Dict, Any, List, Optional
import time
import hashlib
import pickle
import os
from diskcache import Cache
from sentence_transformers import SentenceTransformer
import torch
from concurrent.futures import ThreadPoolExecutor
import threading

from config import Config

logger = logging.getLogger(__name__)

class Embedder:  # ✅ FIXED: Keep original class name
    """Production-ready embedder with advanced caching and optimization"""
    
    def __init__(self):
        self.config = Config()
        self.model = None
        self.cache = None
        self.lock = threading.Lock()
        self._initialize_model()
        self._setup_caching()
    
    def _initialize_model(self):
        """Initialize embedding model with optimizations"""
        try:
            logger.info(f"Loading embedding model: {self.config.EMBEDDING_MODEL}")
            
            # Load model with optimizations
            self.model = SentenceTransformer(self.config.EMBEDDING_MODEL)
            
            # GPU optimization
            if torch.cuda.is_available():
                self.model = self.model.to('cuda')
                logger.info(f"Model loaded on GPU: {torch.cuda.get_device_name()}")
            else:
                logger.info("Model loaded on CPU")
            
            # Model optimizations
            self.model.eval()  # Set to evaluation mode
            
            logger.info("✅ Embedding model initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize embedding model: {str(e)}")
            raise RuntimeError(f"Embedding model initialization failed: {str(e)}")
    
    def _setup_caching(self):
        """Setup advanced caching system"""
        try:
            cache_dir = os.path.join(self.config.VECTOR_STORE_PATH, 'embedding_cache')
            self.cache = Cache(
                directory=cache_dir,
                size_limit=512 * 1024 * 1024,  # 512MB cache limit
                timeout=30
            )
            logger.info(f"✅ Embedding cache initialized: {cache_dir}")
            
        except Exception as e:
            logger.error(f"❌ Cache initialization failed: {str(e)}")
            self.cache = None
    
    def create_embeddings(self, text_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create embeddings with intelligent caching - BACKWARD COMPATIBLE"""
        return self.create_embeddings_cached(text_blocks, "default")
    
    def create_embeddings_cached(self, text_blocks: List[Dict[str, Any]], user_id: str = "default") -> Dict[str, Any]:
        """Create embeddings with intelligent caching"""
        try:
            if not text_blocks:
                return {'success': False, 'error': 'No text blocks provided'}
            
            start_time = time.time()
            texts = [block['text'] for block in text_blocks]
            
            # Batch processing for efficiency
            embeddings = []
            cache_hits = 0
            cache_misses = 0
            
            # Process in batches
            batch_size = 32
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings, batch_cache_hits, batch_cache_misses = self._process_batch(
                    batch_texts, user_id
                )
                
                embeddings.extend(batch_embeddings)
                cache_hits += batch_cache_hits
                cache_misses += batch_cache_misses
            
            # Combine with metadata
            embedding_data = []
            for i, (text_block, embedding) in enumerate(zip(text_blocks, embeddings)):
                embedding_data.append({
                    'text': text_block['text'],
                    'embedding': embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                    'metadata': {
                        **text_block,
                        'embedding_model': self.config.EMBEDDING_MODEL,
                        'embedding_dim': len(embedding),
                        'user_id': user_id
                    }
                })
            
            processing_time = time.time() - start_time
            cache_hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
            
            logger.info(f"Embeddings created: {len(embeddings)} total, {cache_hits} cache hits, processing time: {processing_time:.2f}s")
            
            return {
                'success': True,
                'embeddings': embedding_data,
                'data': embedding_data,  # ✅ BACKWARD COMPATIBILITY
                'total_embeddings': len(embedding_data),
                'cache_hit_rate': cache_hit_rate,
                'processing_time': processing_time,
                'cache_hits': cache_hits,
                'cache_misses': cache_misses
            }
            
        except Exception as e:
            logger.error(f"Embedding creation error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _process_batch(self, texts: List[str], user_id: str) -> tuple:
        """Process batch with caching"""
        embeddings = []
        cache_hits = 0
        cache_misses = 0
        texts_to_embed = []
        cache_keys = []
        indices_to_embed = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text, user_id)
            cache_keys.append(cache_key)
            
            if self.cache:
                try:
                    cached_embedding = self.cache.get(cache_key)
                    if cached_embedding is not None:
                        embeddings.append(cached_embedding)
                        cache_hits += 1
                    else:
                        embeddings.append(None)  # Placeholder
                        texts_to_embed.append(text)
                        indices_to_embed.append(i)
                        cache_misses += 1
                except Exception as e:
                    logger.warning(f"Cache read error: {str(e)}")
                    embeddings.append(None)
                    texts_to_embed.append(text)
                    indices_to_embed.append(i)
                    cache_misses += 1
            else:
                embeddings.append(None)
                texts_to_embed.append(text)
                indices_to_embed.append(i)
                cache_misses += 1
        
        # Embed uncached texts
        if texts_to_embed:
            try:
                with self.lock:  # Thread-safe model access
                    new_embeddings = self.model.encode(
                        texts_to_embed,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                        batch_size=16
                    )
                
                # Fill in placeholders and cache results
                for idx, (embedding, original_idx) in enumerate(zip(new_embeddings, indices_to_embed)):
                    embeddings[original_idx] = embedding
                    
                    # Cache the result
                    if self.cache:
                        try:
                            self.cache.set(
                                cache_keys[original_idx], 
                                embedding,
                                expire=7 * 24 * 3600  # 7 days
                            )
                        except Exception as e:
                            logger.warning(f"Cache write error: {str(e)}")
                            
            except Exception as e:
                logger.error(f"Batch embedding error: {str(e)}")
                raise
        
        return embeddings, cache_hits, cache_misses
    
    def _get_cache_key(self, text: str, user_id: str) -> str:
        """Generate cache key for text"""
        content = f"{text}:{self.config.EMBEDDING_MODEL}:{user_id}"
        return f"embed:{hashlib.sha256(content.encode()).hexdigest()}"
    
    def embed_query(self, query: str, user_id: str = "system") -> Optional[List[float]]:
        """Embed single query with caching"""
        try:
            if not query.strip():
                return None
            
            cache_key = self._get_cache_key(query, user_id)
            
            # Check cache
            if self.cache:
                try:
                    cached_embedding = self.cache.get(cache_key)
                    if cached_embedding is not None:
                        return cached_embedding.tolist()
                except Exception as e:
                    logger.warning(f"Query cache read error: {str(e)}")
            
            # Generate embedding
            with self.lock:
                embedding = self.model.encode([query], normalize_embeddings=True)[0]
            
            # Cache result
            if self.cache:
                try:
                    self.cache.set(cache_key, embedding, expire=24 * 3600)  # 24 hours
                except Exception as e:
                    logger.warning(f"Query cache write error: {str(e)}")
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Query embedding error: {str(e)}")
            return None
    
    def health_check(self) -> bool:
        """Health check for the embedder"""
        try:
            # Quick embedding test
            test_text = "Health check test"
            with self.lock:
                embedding = self.model.encode([test_text])
            return len(embedding) > 0 and len(embedding[0]) == self.config.EMBEDDING_DIMENSION
        except Exception as e:
            logger.error(f"Embedder health check failed: {str(e)}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.cache:
            return {'cache_enabled': False}
        
        try:
            stats = {
                'cache_enabled': True,
                'cache_size': len(self.cache),
                'cache_volume': self.cache.volume(),
                'cache_directory': self.cache.directory
            }
            return stats
        except Exception as e:
            logger.warning(f"Cache stats error: {str(e)}")
            return {'cache_enabled': True, 'stats_error': str(e)}
    
    def clear_cache(self):
        """Clear embedding cache"""
        if self.cache:
            try:
                self.cache.clear()
                logger.info("Embedding cache cleared")
            except Exception as e:
                logger.error(f"Cache clear error: {str(e)}")

# Create a backward compatible alias
AdvancedEmbedder = Embedder

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import requests
import os

from config import Config

logger = logging.getLogger(__name__)

class Embedder:
    """Handles text embedding generation with fallback support"""
    
    def __init__(self):
        self.config = Config()
        self.local_model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize embedding model with proper fallback"""
        try:
            # Always try local first to avoid API issues
            logger.info(f"Loading local embedding model: {self.config.EMBEDDING_MODEL}")
            from sentence_transformers import SentenceTransformer
            self.local_model = SentenceTransformer(self.config.EMBEDDING_MODEL)
            logger.info("✅ Local embedding model loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize local model: {str(e)}")
            if self.config.HF_API_KEY:
                logger.info("🔄 Will use Hugging Face API as fallback")
            else:
                raise RuntimeError("No embedding method available! Install sentence-transformers or provide HF_API_KEY")
    
    def create_embeddings(self, text_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create embeddings for text blocks with robust error handling"""
        try:
            if not text_blocks:
                return {'success': False, 'error': 'No text blocks provided'}
            
            texts = [block['text'] for block in text_blocks]
            
            # Try local model first
            if self.local_model:
                try:
                    embeddings = self._create_local_embeddings(texts)
                    if embeddings is not None:
                        return self._package_embeddings(embeddings, text_blocks, 'local')
                except Exception as e:
                    logger.warning(f"Local embedding failed: {e}")
            
            # Fallback to API if local fails and API key exists
            if self.config.HF_API_KEY:
                try:
                    embeddings = self._create_api_embeddings_fixed(texts)
                    if embeddings is not None:
                        return self._package_embeddings(embeddings, text_blocks, 'api')
                except Exception as e:
                    logger.error(f"API embedding failed: {e}")
            
            return {'success': False, 'error': 'All embedding methods failed'}
            
        except Exception as e:
            logger.error(f"Embedding creation error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _create_local_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """Create embeddings using local model"""
        try:
            if not self.local_model:
                return None
            
            logger.info(f"🏠 Creating {len(texts)} embeddings locally")
            embeddings = self.local_model.encode(
                texts, 
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 10,
                batch_size=16
            )
            logger.info("✅ Local embeddings created successfully")
            return embeddings
            
        except Exception as e:
            logger.error(f"Local embedding error: {str(e)}")
            return None
    
    def _create_api_embeddings_fixed(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Fixed HuggingFace API implementation"""
        try:
            # Use the correct API endpoint format
            api_url = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
            
            headers = {
                "Authorization": f"Bearer {self.config.HF_API_KEY}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"🌐 Creating {len(texts)} embeddings via HF API")
            
            # Process in smaller batches to avoid timeouts
            batch_size = 5
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                payload = {
                    "inputs": batch,
                    "options": {"wait_for_model": True}
                }
                
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    batch_embeddings = response.json()
                    if isinstance(batch_embeddings, list):
                        all_embeddings.extend(batch_embeddings)
                    else:
                        logger.error(f"Unexpected API response format: {batch_embeddings}")
                        return None
                elif response.status_code == 503:
                    logger.warning("Model loading, waiting 10 seconds...")
                    import time
                    time.sleep(10)
                    # Retry once
                    response = requests.post(api_url, headers=headers, json=payload, timeout=60)
                    if response.status_code == 200:
                        batch_embeddings = response.json()
                        all_embeddings.extend(batch_embeddings)
                    else:
                        logger.error(f"API retry failed: {response.status_code}, {response.text}")
                        return None
                else:
                    logger.error(f"API error: {response.status_code}, {response.text}")
                    return None
            
            logger.info("✅ API embeddings created successfully")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"API embedding error: {str(e)}")
            return None
    
    def _package_embeddings(self, embeddings, text_blocks, source):
        packaged = []
        for i, block in enumerate(text_blocks):
            packaged.append({
                "embedding": embeddings[i],
                "text": block["text"],
                "metadata": {
                    "page": block.get("page", -1),
                    "block": block.get("block_number", i)
                }
            })
        return {
            "success": True,
            "data": packaged,   # ✅ ready to go into vectorstore
            "source": source
        }

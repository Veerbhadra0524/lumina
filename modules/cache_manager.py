import time
from typing import Any, Optional, Dict
import json
import hashlib
from diskcache import Cache
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Simple cache manager for application-wide caching"""
    
    def __init__(self):
        try:
            self.cache = Cache(
                directory='data/app_cache',
                size_limit=1024 * 1024 * 1024,  # 1GB limit
                timeout=60
            )
            logger.info(f"SUCCESS: Cache manager initialized")
        except Exception as e:
            logger.error(f"ERROR: Cache manager initialization failed: {str(e)}")
            self.cache = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.cache:
            return None
        try:
            return self.cache.get(key)
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache"""
        if not self.cache:
            return False
        try:
            return self.cache.set(key, value, expire=expire)
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.cache:
            return False
        try:
            return self.cache.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {str(e)}")
            return False
    
    def clear_user_cache(self, user_id: str) -> int:
        """Clear all cache entries for a user"""
        if not self.cache:
            return 0
        try:
            count = 0
            pattern = f"query:{user_id}:"
            
            # Find and delete user's cache entries
            for key in list(self.cache):
                if key.startswith(pattern):
                    if self.cache.delete(key):
                        count += 1
            
            logger.info(f"Cleared {count} cache entries for user {user_id}")
            return count
            
        except Exception as e:
            logger.error(f"Clear user cache error for {user_id}: {str(e)}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.cache:
            return {'cache_enabled': False}
        try:
            return {
                'cache_enabled': True,
                'size': len(self.cache),
                'volume': self.cache.volume(),
                'directory': self.cache.directory
            }
        except Exception as e:
            return {'cache_enabled': True, 'error': str(e)}
    
    def health_check(self) -> bool:
        """Health check for cache"""
        if not self.cache:
            return False
        try:
            test_key = "health_check"
            self.cache.set(test_key, "ok", expire=1)
            result = self.cache.get(test_key)
            self.cache.delete(test_key)
            return result == "ok"
        except:
            return False

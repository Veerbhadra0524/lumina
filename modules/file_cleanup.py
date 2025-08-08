import os
import shutil
import time
from datetime import datetime, timedelta
from typing import List
import logging

logger = logging.getLogger(__name__)

class FileCleanupManager:
    """Smart file cleanup with configurable retention"""
    
    def __init__(self):
        self.upload_path = "data/uploads"
        self.retention_hours = 2  # Keep files for 2 hours only
        self.max_storage_mb = 500  # Max 500MB storage
    
    def cleanup_expired_files(self, user_id: str = None) -> dict:
        """Clean up old uploaded files"""
        try:
            if not os.path.exists(self.upload_path):
                return {"cleaned": 0, "size_freed": 0}
            
            cutoff_time = time.time() - (self.retention_hours * 3600)
            cleaned_count = 0
            size_freed = 0
            
            # Clean specific user or all users
            target_users = [user_id] if user_id else os.listdir(self.upload_path)
            
            for user_folder in target_users:
                user_path = os.path.join(self.upload_path, user_folder)
                if not os.path.exists(user_path):
                    continue
                    
                for upload_folder in os.listdir(user_path):
                    upload_full_path = os.path.join(user_path, upload_folder)
                    
                    if os.path.isdir(upload_full_path):
                        folder_time = os.path.getctime(upload_full_path)
                        
                        if folder_time < cutoff_time:
                            # Calculate size before deletion
                            folder_size = self._get_folder_size(upload_full_path)
                            
                            # Delete entire upload folder
                            shutil.rmtree(upload_full_path)
                            cleaned_count += 1
                            size_freed += folder_size
                            
                            logger.info(f"CLEANUP: Deleted expired folder {upload_full_path} ({folder_size/1024/1024:.1f}MB)")
            
            return {
                "cleaned": cleaned_count,
                "size_freed_mb": round(size_freed / 1024 / 1024, 2)
            }
            
        except Exception as e:
            logger.error(f"CLEANUP ERROR: {e}")
            return {"cleaned": 0, "size_freed": 0, "error": str(e)}
    
    def _get_folder_size(self, folder_path: str) -> int:
        """Get total size of folder in bytes"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            logger.warning(f"Size calculation error: {e}")
        return total_size
    
    def get_storage_stats(self) -> dict:
        """Get current storage statistics"""
        try:
            if not os.path.exists(self.upload_path):
                return {"total_mb": 0, "user_count": 0, "upload_count": 0}
            
            total_size = self._get_folder_size(self.upload_path)
            user_folders = [f for f in os.listdir(self.upload_path) if os.path.isdir(os.path.join(self.upload_path, f))]
            
            upload_count = 0
            for user_folder in user_folders:
                user_path = os.path.join(self.upload_path, user_folder)
                upload_folders = [f for f in os.listdir(user_path) if os.path.isdir(os.path.join(user_path, f))]
                upload_count += len(upload_folders)
            
            return {
                "total_mb": round(total_size / 1024 / 1024, 2),
                "user_count": len(user_folders),
                "upload_count": upload_count,
                "max_mb": self.max_storage_mb
            }
            
        except Exception as e:
            logger.error(f"STATS ERROR: {e}")
            return {"total_mb": 0, "user_count": 0, "upload_count": 0, "error": str(e)}
    
    def force_cleanup_user(self, user_id: str) -> dict:
        """Force cleanup all files for a specific user"""
        try:
            user_path = os.path.join(self.upload_path, user_id)
            if not os.path.exists(user_path):
                return {"cleaned": 0, "size_freed_mb": 0}
            
            size_before = self._get_folder_size(user_path)
            shutil.rmtree(user_path)
            
            logger.info(f"FORCE CLEANUP: Removed all files for user {user_id} ({size_before/1024/1024:.1f}MB)")
            
            return {
                "cleaned": 1,
                "size_freed_mb": round(size_before / 1024 / 1024, 2)
            }
            
        except Exception as e:
            logger.error(f"FORCE CLEANUP ERROR: {e}")
            return {"cleaned": 0, "size_freed_mb": 0, "error": str(e)}

import os
import shutil
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from modules.firebase_manager import FirebaseManager
import logging

logger = logging.getLogger(__name__)

class SmartFileManager:
    """Intelligent file cleanup with OCR data retention"""
    
    def __init__(self):
        self.firebase = FirebaseManager()
        self.upload_folder = 'data/uploads'
        self.retention_hours = 24  # Keep files for 24 hours
    
    def cleanup_expired_files(self):
        """Clean up expired uploaded files but keep OCR data"""
        try:
            if not os.path.exists(self.upload_folder):
                return
            
            cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
            cleaned_count = 0
            
            for user_folder in os.listdir(self.upload_folder):
                user_path = os.path.join(self.upload_folder, user_folder)
                if not os.path.isdir(user_path):
                    continue
                
                # Check each upload folder
                for upload_folder in os.listdir(user_path):
                    upload_path = os.path.join(user_path, upload_folder)
                    if not os.path.isdir(upload_path):
                        continue
                    
                    # Check if folder is expired
                    folder_time = datetime.fromtimestamp(os.path.getctime(upload_path))
                    if folder_time < cutoff_time:
                        # Extract and save OCR data before deletion
                        self._preserve_ocr_data(upload_path, user_folder)
                        
                        # Delete the entire upload folder
                        shutil.rmtree(upload_path)
                        cleaned_count += 1
                        logger.info(f"FILE CLEANUP: Deleted expired folder {upload_path}")
            
            if cleaned_count > 0:
                logger.info(f"FILE CLEANUP: Cleaned up {cleaned_count} expired file folders")
                
        except Exception as e:
            logger.error(f"FILE CLEANUP ERROR: {str(e)}")
    
    def _preserve_ocr_data(self, upload_path: str, user_id: str):
        """Extract and preserve important OCR data before file deletion"""
        try:
            extracted_text_path = os.path.join(upload_path, 'extracted_text.json')
            if not os.path.exists(extracted_text_path):
                return
            
            # Load extracted text data
            with open(extracted_text_path, 'r', encoding='utf-8') as f:
                text_data = json.load(f)
            
            # Create compressed summary
            compressed_data = self._compress_ocr_data(text_data)
            
            # Store in Firebase for permanent retention
            if self.firebase.is_available() and compressed_data:
                self.firebase.db.collection('ocr_archives').add({
                    'user_id': user_id,
                    'upload_id': text_data.get('upload_id', 'unknown'),
                    'archived_at': datetime.now(),
                    'original_blocks': text_data.get('total_blocks', 0),
                    'compressed_data': compressed_data,
                    'source_folder': upload_path
                })
                
                logger.info(f"FILE ARCHIVE: Preserved OCR data for {upload_path}")
                
        except Exception as e:
            logger.error(f"FILE ARCHIVE ERROR: Failed to preserve OCR data: {str(e)}")
    
    def _compress_ocr_data(self, text_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress OCR data to minimal essential information"""
        try:
            text_blocks = text_data.get('text_blocks', [])
            if not text_blocks:
                return {}
            
            # Extract only high-confidence, meaningful text
            compressed_blocks = []
            for block in text_blocks:
                confidence = block.get('confidence', 0)
                text = block.get('text', '').strip()
                
                # Only keep high-confidence blocks with meaningful content
                if confidence > 0.7 and len(text) > 10:
                    compressed_blocks.append({
                        'text': text,
                        'confidence': round(confidence, 2),
                        'page': block.get('page_number', 0)
                    })
            
            # Create summary
            all_text = ' '.join([block['text'] for block in compressed_blocks])
            
            return {
                'summary': all_text[:1000] + '...' if len(all_text) > 1000 else all_text,
                'high_confidence_blocks': compressed_blocks[:20],  # Keep top 20 blocks
                'total_original_blocks': len(text_blocks),
                'compression_ratio': len(compressed_blocks) / len(text_blocks) if text_blocks else 0
            }
            
        except Exception as e:
            logger.error(f"OCR COMPRESSION ERROR: {str(e)}")
            return {}
    
    def get_user_archives(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's archived OCR data"""
        try:
            if not self.firebase.is_available():
                return []
            
            archives = self.firebase.db.collection('ocr_archives')\
                                     .where('user_id', '==', user_id)\
                                     .order_by('archived_at', direction=firestore.Query.DESCENDING)\
                                     .limit(50)\
                                     .stream()
            
            archive_list = []
            for archive in archives:
                archive_data = archive.to_dict()
                archive_list.append({
                    'upload_id': archive_data.get('upload_id'),
                    'archived_at': archive_data.get('archived_at'),
                    'original_blocks': archive_data.get('original_blocks', 0),
                    'summary': archive_data.get('compressed_data', {}).get('summary', ''),
                    'compression_ratio': archive_data.get('compressed_data', {}).get('compression_ratio', 0)
                })
            
            return archive_list
            
        except Exception as e:
            logger.error(f"ARCHIVE RETRIEVAL ERROR: {str(e)}")
            return []
    
    def schedule_cleanup(self):
        """Schedule automatic file cleanup (call this periodically)"""
        try:
            # Run cleanup
            self.cleanup_expired_files()
            
            # Log next cleanup time
            next_cleanup = datetime.now() + timedelta(hours=6)  # Every 6 hours
            logger.info(f"FILE SCHEDULER: Next cleanup scheduled for {next_cleanup}")
            
        except Exception as e:
            logger.error(f"FILE SCHEDULER ERROR: {str(e)}")

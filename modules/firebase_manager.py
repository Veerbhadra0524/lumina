import firebase_admin
from firebase_admin import credentials, firestore, auth
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import os

# Clean logging setup without emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FirebaseManager:
    """Firebase integration with Windows-compatible logging"""
    
    def __init__(self):
        self.db = None
        self.app = None
        self.available = False
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK with clean logging"""
        logger.info("FIREBASE: Starting Firebase initialization...")
        
        try:
            # Check if service account file exists
            service_account_path = 'firebase-service-account.json'
            logger.info(f"FIREBASE: Looking for service account file: {service_account_path}")
            
            if not os.path.exists(service_account_path):
                logger.error(f"FIREBASE ERROR: Service account file NOT FOUND: {service_account_path}")
                logger.error("FIREBASE FIX: Download service account JSON from Firebase Console")
                logger.error("FIREBASE FIX: Rename it to 'firebase-service-account.json' and place in project root")
                return
            
            logger.info(f"FIREBASE: Service account file found: {service_account_path}")
            
            # Check if already initialized
            if firebase_admin._apps:
                self.app = firebase_admin.get_app()
                logger.info("FIREBASE: Using existing Firebase app")
            else:
                logger.info("FIREBASE: Initializing new Firebase app...")
                cred = credentials.Certificate(service_account_path)
                self.app = firebase_admin.initialize_app(cred)
                logger.info("FIREBASE: Firebase app initialized successfully")
            
            # Initialize Firestore
            logger.info("FIREBASE: Initializing Firestore client...")
            self.db = firestore.client()
            self.available = True
            logger.info("FIREBASE: Firestore client initialized successfully")
            
            # Test connection
            logger.info("FIREBASE: Testing Firebase connection...")
            test_ref = self.db.collection('_test').document('connection_test')
            test_ref.set({'test': True, 'timestamp': datetime.now()})
            test_ref.delete()  # Clean up
            logger.info("FIREBASE: Firebase connection test PASSED")
            
        except FileNotFoundError as e:
            logger.error(f"FIREBASE ERROR: Service account file error: {str(e)}")
            self.available = False
        except Exception as e:
            logger.error(f"FIREBASE ERROR: Firebase initialization failed: {str(e)}")
            logger.error(f"FIREBASE ERROR: Error type: {type(e).__name__}")
            self.available = False
    
    def is_available(self):
        """Check if Firebase is available with logging"""
        if self.available:
            logger.debug("FIREBASE: Firebase is available")
        else:
            logger.warning("FIREBASE WARNING: Firebase is NOT available - running in fallback mode")
        return self.available
    
    def verify_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Verify Firebase ID token with detailed logging"""
        if not self.is_available():
            logger.error("FIREBASE ERROR: Cannot verify token - Firebase not available")
            return None
            
        try:
            logger.info("FIREBASE: Verifying Firebase ID token...")
            decoded_token = auth.verify_id_token(id_token)
            user_email = decoded_token.get('email', 'unknown')
            user_uid = decoded_token.get('uid', 'unknown')
            
            logger.info(f"FIREBASE: Token verified successfully for user: {user_email} (UID: {user_uid})")
            return decoded_token
            
        except auth.InvalidIdTokenError:
            logger.error("FIREBASE ERROR: Invalid ID token provided")
            return None
        except auth.ExpiredIdTokenError:
            logger.error("FIREBASE ERROR: ID token has expired")
            return None
        except Exception as e:
            logger.error(f"FIREBASE ERROR: Token verification failed: {str(e)}")
            return None
    
    def create_user_record(self, user_data: Dict[str, Any]) -> bool:
        """Create user record with logging"""
        if not self.is_available():
            logger.warning("FIREBASE WARNING: Cannot create user record - Firebase not available")
            return False
            
        try:
            user_id = user_data['uid']
            user_email = user_data.get('email', 'unknown')
            
            logger.info(f"FIREBASE: Creating user record for: {user_email} (UID: {user_id})")
            
            user_doc = {
                'uid': user_id,
                'email': user_email,
                'name': user_data.get('name', ''),
                'created_at': datetime.now(),
                'document_count': 0,
                'query_count': 0,
                'last_login': datetime.now()
            }
            
            self.db.collection('users').document(user_id).set(user_doc, merge=True)
            logger.info(f"FIREBASE: User record created/updated successfully for: {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"FIREBASE ERROR: Failed to create user record: {str(e)}")
            return False
    
    def store_document_data(self, user_id: str, doc_data: Dict[str, Any]) -> str:
        """Store document with logging"""
        if not self.is_available():
            logger.warning("FIREBASE WARNING: Cannot store document - Firebase not available")
            return ""
            
        try:
            filename = doc_data.get('filename', 'unknown')
            
            # FIX: Handle text_blocks properly
            text_blocks = doc_data.get('text_blocks', [])
            if isinstance(text_blocks, int):
                text_count = text_blocks
            else:
                text_count = len(text_blocks) if text_blocks else 0
            
            logger.info(f"FIREBASE: Storing document for user {user_id}: {filename} ({text_count} text blocks)")
            
            doc_ref = self.db.collection('user_documents').add({
                'user_id': user_id,
                'filename': filename,
                'text_blocks_count': text_count,
                'upload_time': datetime.now(),
                'file_type': doc_data.get('file_type', 'unknown'),
                'text_summary': self._create_text_summary(text_blocks) if not isinstance(text_blocks, int) else "Processed text content"
            })
            
            # Update user document count
            from firebase_admin import firestore
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({'document_count': firestore.Increment(1)})
            
            doc_id = doc_ref[1].id
            logger.info(f"FIREBASE: Document stored successfully: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"FIREBASE ERROR: Failed to store document: {str(e)}")
            return ""

        
    
    
    
    def _create_text_summary(self, text_blocks: List[Dict]) -> str:
        """Create summary for storage"""
        if not text_blocks:
            return ""
        
        # Get first 500 characters as summary
        all_text = " ".join([block.get('text', '') for block in text_blocks[:5]])
        return all_text[:500] + "..." if len(all_text) > 500 else all_text
    
    def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get user analytics with logging"""
        if not self.is_available():
            return {}
            
        try:
            logger.info(f"FIREBASE: Getting analytics for user: {user_id}")
            user_doc = self.db.collection('users').document(user_id).get()
            
            if user_doc.exists:
                data = user_doc.to_dict()
                logger.info(f"FIREBASE: Analytics retrieved for user: {user_id}")
                return {
                    'document_count': data.get('document_count', 0),
                    'query_count': data.get('query_count', 0),
                    'member_since': data.get('created_at'),
                    'last_login': data.get('last_login')
                }
            else:
                logger.warning(f"FIREBASE WARNING: No user document found for: {user_id}")
                return {}
                
        except Exception as e:
            logger.error(f"FIREBASE ERROR: Failed to get analytics: {str(e)}")
            return {}

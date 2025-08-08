import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from modules.firebase_manager import FirebaseManager
import logging

logger = logging.getLogger(__name__)

class ChatHistoryManager:
    """Complete chat history management with Firebase storage"""
    
    def __init__(self):
        self.firebase = FirebaseManager()
    
    def create_conversation(self, user_id: str) -> str:
        """Create a new conversation thread"""
        try:
            conversation_id = hashlib.md5(f"{user_id}_{datetime.now()}".encode()).hexdigest()[:12]
            
            conversation_data = {
                'conversation_id': conversation_id,
                'user_id': user_id,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'title': 'New Conversation',
                'message_count': 0
            }
            
            if self.firebase.is_available():
                self.firebase.db.collection('conversations').document(conversation_id).set(conversation_data)
                logger.info(f"CHAT: Created conversation {conversation_id} for user {user_id}")
            
            return conversation_id
            
        except Exception as e:
            logger.error(f"CHAT ERROR: Failed to create conversation: {str(e)}")
            return f"local_{hashlib.md5(f'{user_id}_{datetime.now()}'.encode()).hexdigest()[:8]}"
    
    def add_message(self, conversation_id: str, role: str, content: str, metadata: Dict = None) -> bool:
        """Add message to conversation and update title"""
        try:
            message_data = {
                'conversation_id': conversation_id,
                'role': role,
                'content': content,
                'timestamp': datetime.now(),
                'metadata': metadata or {}
            }
            
            if self.firebase.is_available():
                from firebase_admin import firestore
                
                # Add message
                self.firebase.db.collection('messages').add(message_data)
                
                # Update conversation
                conversation_ref = self.firebase.db.collection('conversations').document(conversation_id)
                
                # Get current conversation data
                conv_doc = conversation_ref.get()
                if conv_doc.exists:
                    conv_data = conv_doc.to_dict()
                    message_count = conv_data.get('message_count', 0) + 1
                    
                    # Update title based on first user message
                    title = conv_data.get('title', 'New Conversation')
                    if role == 'user' and message_count <= 2:  # First user message
                        title = content[:50] + "..." if len(content) > 50 else content
                    
                    # Update conversation
                    conversation_ref.update({
                        'updated_at': datetime.now(),
                        'message_count': message_count,
                        'title': title
                    })
                
                logger.info(f"CHAT: Added {role} message to conversation {conversation_id}")
                return True
            else:
                logger.warning("CHAT WARNING: Firebase not available")
                return False
                
        except Exception as e:
            logger.error(f"CHAT ERROR: Failed to add message: {str(e)}")
            return False
  
    
    def get_user_conversations(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's conversation history with enhanced isolation"""
        try:
            if not self.firebase.is_available():
                return []
            
            if not user_id:
                logger.warning("CHAT SECURITY: No user_id provided")
                return []
            
            from firebase_admin import firestore
            
            # Enhanced query with explicit user filtering
            conversations = self.firebase.db.collection('conversations')\
                                        .where('user_id', '==', user_id)\
                                        .order_by('updated_at', direction=firestore.Query.DESCENDING)\
                                        .limit(limit)\
                                        .stream()
            
            conversation_list = []
            for conv in conversations:
                conv_data = conv.to_dict()
                
                # Double-check user ownership
                if conv_data.get('user_id') != user_id:
                    logger.warning(f"CHAT SECURITY: Conversation ownership mismatch {conv.id}")
                    continue
                
                conversation_list.append({
                    'conversation_id': conv_data['conversation_id'],
                    'title': conv_data.get('title', 'New Conversation'),
                    'updated_at': conv_data['updated_at'].isoformat() if hasattr(conv_data['updated_at'], 'isoformat') else str(conv_data['updated_at']),
                    'message_count': conv_data.get('message_count', 0),
                    'user_id': conv_data.get('user_id')  # Include for verification
                })
            
            logger.info(f"CHAT: Retrieved {len(conversation_list)} conversations for user {user_id}")
            return conversation_list
            
        except Exception as e:
            logger.error(f"CHAT ERROR: Failed to get conversations: {str(e)}")
            return []

    def get_conversation_messages(self, conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get messages with enhanced user verification"""
        try:
            if not self.firebase.is_available():
                return []
            
            # Verify conversation ownership first
            conv_doc = self.firebase.db.collection('conversations').document(conversation_id).get()
            if not conv_doc.exists:
                logger.warning(f"CHAT SECURITY: Conversation {conversation_id} not found")
                return []
            
            conv_data = conv_doc.to_dict()
            if conv_data.get('user_id') != user_id:
                logger.warning(f"CHAT SECURITY: User {user_id} attempted to access conversation {conversation_id} owned by {conv_data.get('user_id')}")
                return []
            
            from firebase_admin import firestore
            
            messages = self.firebase.db.collection('messages')\
                                    .where('conversation_id', '==', conversation_id)\
                                    .order_by('timestamp', direction=firestore.Query.ASCENDING)\
                                    .stream()
            
            message_list = []
            for msg in messages:
                msg_data = msg.to_dict()
                message_list.append({
                    'role': msg_data['role'],
                    'content': msg_data['content'],
                    'timestamp': msg_data['timestamp'].isoformat() if hasattr(msg_data['timestamp'], 'isoformat') else str(msg_data['timestamp']),
                    'metadata': msg_data.get('metadata', {}),
                    'conversation_id': conversation_id  # Verify conversation ID
                })
            
            logger.info(f"CHAT: Retrieved {len(message_list)} messages for conversation {conversation_id}")
            return message_list
            
        except Exception as e:
            logger.error(f"CHAT ERROR: Failed to get messages: {str(e)}")
            return []

    
    
    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete conversation and all messages"""
        try:
            if not self.firebase.is_available():
                return False
            
            # Verify ownership
            conv_doc = self.firebase.db.collection('conversations').document(conversation_id).get()
            if not conv_doc.exists or conv_doc.to_dict().get('user_id') != user_id:
                return False
            
            # Delete messages
            messages = self.firebase.db.collection('messages')\
                                     .where('conversation_id', '==', conversation_id)\
                                     .stream()
            
            for msg in messages:
                msg.reference.delete()
            
            # Delete conversation
            self.firebase.db.collection('conversations').document(conversation_id).delete()
            
            logger.info(f"CHAT: Deleted conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"CHAT ERROR: Failed to delete conversation: {str(e)}")
            return False

from flask import Blueprint, request, jsonify, session, render_template
from modules.chat_history import ChatHistoryManager
from modules.retriever import Retriever
from modules.generator import Generator
import hashlib
import logging

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)

# Initialize components
chat_history = ChatHistoryManager()
generator = Generator()

def require_auth(f):
    """Auth decorator"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'firebase_user' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    return session.get('firebase_user', {})

@chat_bp.route('/')
def chat_interface():
    """Main chat interface with sidebar"""
    user = get_current_user()
    if not user:
        return render_template('index.html', show_auth=True)
    return render_template('chat.html', user=user)

@chat_bp.route('/history')
@require_auth
def get_history():
    """Get user's conversation history"""
    user = get_current_user()
    try:
        conversations = chat_history.get_user_conversations(user['uid'])
        return jsonify({'success': True, 'conversations': conversations})
    except Exception as e:
        logger.error(f'Get history error: {e}')
        return jsonify({'success': False, 'error': 'Failed to get history'}), 500

@chat_bp.route('/conversation/<conversation_id>')
@require_auth
def get_conversation(conversation_id):
    """Get specific conversation messages"""
    user = get_current_user()
    try:
        messages = chat_history.get_conversation_messages(conversation_id, user['uid'])
        return jsonify({
            'success': True,
            'messages': messages,
            'conversation_id': conversation_id
        })
    except Exception as e:
        logger.error(f'Get conversation error: {e}')
        return jsonify({'success': False, 'error': 'Failed to get conversation'}), 500

@chat_bp.route('/new', methods=['POST'])
@require_auth
def new_conversation():
    """Create new conversation"""
    user = get_current_user()
    try:
        conversation_id = chat_history.create_conversation(user['uid'])
        return jsonify({
            'success': True,
            'conversation_id': conversation_id,
            'message': 'New conversation started'
        })
    except Exception as e:
        logger.error(f'New conversation error: {e}')
        return jsonify({'success': False, 'error': 'Failed to create conversation'}), 500

@chat_bp.route('/send', methods=['POST'])
@require_auth
def send_message():
    """Send message with history storage"""
    user = get_current_user()
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        
        if not message:
            return jsonify({'success': False, 'error': 'Message required'}), 400
        
        # Create conversation if none exists
        if not conversation_id:
            conversation_id = chat_history.create_conversation(user['uid'])
        
        # Save user message
        chat_history.add_message(conversation_id, 'user', message)
        
        # Process query
        retriever = Retriever(user_id=user['uid'])
        retrieval_result = retriever.retrieve(message)
        
        if retrieval_result.get('success', False):
            documents = retrieval_result.get('documents', [])
            generation_result = generator.generate_answer(message, documents)
            
            if generation_result.get('success', False):
                assistant_response = generation_result.get('answer', '')
                
                # Save assistant response
                chat_history.add_message(conversation_id, 'assistant', assistant_response, {
                    'sources': documents[:3],
                    'confidence': generation_result.get('confidence', 0.8)
                })
                
                return jsonify({
                    'success': True,
                    'response': assistant_response,
                    'conversation_id': conversation_id,
                    'sources': documents[:3],
                    'confidence': generation_result.get('confidence', 0.8)
                })
        
        # Fallback response
        fallback = "I don't have enough information to answer that question. Please upload some documents first."
        chat_history.add_message(conversation_id, 'assistant', fallback)
        
        return jsonify({
            'success': True,
            'response': fallback,
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        logger.error(f'Chat send error: {e}')
        return jsonify({'success': False, 'error': 'Failed to process message'}), 500

@chat_bp.route('/delete/<conversation_id>', methods=['DELETE'])
@require_auth
def delete_conversation(conversation_id):
    """Delete conversation"""
    user = get_current_user()
    try:
        success = chat_history.delete_conversation(conversation_id, user['uid'])
        if success:
            return jsonify({'success': True, 'message': 'Conversation deleted'})
        return jsonify({'success': False, 'error': 'Failed to delete'}), 400
    except Exception as e:
        logger.error(f'Delete conversation error: {e}')
        return jsonify({'success': False, 'error': 'Failed to delete conversation'}), 500

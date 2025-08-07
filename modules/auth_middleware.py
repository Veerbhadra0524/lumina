from functools import wraps
from flask import request, jsonify, session
from modules.firebase_manager import FirebaseManager
import logging

logger = logging.getLogger(__name__)
firebase_manager = FirebaseManager()

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for Firebase token in headers
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user_data = firebase_manager.verify_token(token)
            
            if user_data:
                # Set user in session
                session['firebase_user'] = {
                    'uid': user_data['uid'],
                    'email': user_data.get('email'),
                    'name': user_data.get('name', 'User')
                }
                return f(*args, **kwargs)
        
        # Check for existing session (backward compatibility)
        if 'firebase_user' in session:
            return f(*args, **kwargs)
        
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    return decorated_function

def get_current_user():
    """Get current authenticated user"""
    return session.get('firebase_user', {})

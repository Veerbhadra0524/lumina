from flask import Blueprint, request, jsonify, session
from modules.firebase_manager import FirebaseManager
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

firebase_manager = FirebaseManager()

@auth_bp.route('/verify', methods=['POST'])
def verify():
    try:
        data = request.get_json() or {}
        token = data.get('token')
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 400

        user_data = firebase_manager.verify_token(token)
        if not user_data:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        firebase_manager.create_user_record(user_data)

        session['firebase_user'] = {
            'uid': user_data['uid'],
            'email': user_data.get('email'),
            'name': user_data.get('name')
        }
        return jsonify({
            'success': True, 
            'user': session['firebase_user'], 
            'message': 'Authentication successful'
        })

    except Exception as e:
        logger.error(f'Auth verify error: {e}')
        return jsonify({'success': False, 'error': 'Authentication failed'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('firebase_user', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@auth_bp.route('/status')
def status():
    user = session.get('firebase_user')
    return jsonify({
        'success': True, 
        'authenticated': bool(user), 
        'user': user or {}
    })

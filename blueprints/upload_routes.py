from flask import Blueprint, request, jsonify, session, render_template
from modules.firebase_manager import FirebaseManager
import logging

logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__)

firebase_manager = FirebaseManager()

def require_auth(f):
    """Simple auth decorator for upload routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'firebase_user' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    return session.get('firebase_user', {})

@upload_bp.route('/', methods=['GET'])
@require_auth
def upload_page():
    user = get_current_user()
    return render_template('upload.html', user=user)

@upload_bp.route('/', methods=['POST'])
@require_auth
def handle_upload():
    from flask import current_app
    user = get_current_user()
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    try:
        # Import from app context to avoid circular imports
        with current_app.app_context():
            from app import doc_processor, _process_document_sync
            
            if not doc_processor.validate_file(file):
                return jsonify({'success': False, 'error': 'Invalid file type or size'}), 400

            # Process document
            result = _process_document_sync(file, user['uid'])

            # Store metadata in Firebase if successful
            if result.get('success') and firebase_manager.is_available():
                doc_id = firebase_manager.store_document_data(user['uid'], {
                    'filename': file.filename,
                    'text_blocks': result.get('text_blocks', []),
                    'processing_time': result.get('processing_time'),
                    'file_type': 'unknown'
                })
                result['firebase_doc_id'] = doc_id

            return jsonify(result)

    except Exception as e:
        logger.error(f'Upload error: {e}')
        return jsonify({'success': False, 'error': 'Failed to upload document'}), 500

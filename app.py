import os
import time
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify, render_template, session, redirect
from flask_cors import CORS
from dotenv import load_dotenv

# Clean logging setup (NO EMOJIS)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Import components
from config import Config
from modules.document_processor import DocumentProcessor
from modules.text_extractor import TextExtractor
from modules.embedder import Embedder
from modules.vector_store import VectorStore
from modules.retriever import Retriever  
from modules.generator import Generator
from modules.monitoring import PerformanceMonitor
from modules.cache_manager import CacheManager
from modules.firebase_manager import FirebaseManager
from modules.file_cleanup import FileCleanupManager


# Initialize Firebase
firebase_manager = FirebaseManager()

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Initialize components
doc_processor = DocumentProcessor()
text_extractor = TextExtractor()
embedder = Embedder()
generator = Generator()
monitor = PerformanceMonitor()
cache_manager = CacheManager()
# Initialize cleanup manager
cleanup_manager = FileCleanupManager()


# After your existing component initialization, add this:
from blueprints.chat_routes import chat_bp
from blueprints.upload_routes import upload_bp

# Register blueprints properly
app.register_blueprint(chat_bp, url_prefix='/chat')
app.register_blueprint(upload_bp, url_prefix='/upload')


# Create directories
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.VECTOR_STORE_PATH, exist_ok=True)

def get_user_session_id() -> str:
    if 'user_id' not in session:
        raw = f"{request.remote_addr}_{datetime.now(timezone.utc)}"
        session['user_id'] = hashlib.md5(raw.encode()).hexdigest()[:12]
    return session['user_id']

@app.before_request
def before_request():
    request.start_time = time.time()
    if 'user_id' not in session:
        get_user_session_id()

@app.after_request  
def after_request(response):
    duration = time.time() - request.start_time
    monitor.record_request(
        endpoint=request.endpoint,
        method=request.method, 
        status_code=response.status_code,
        duration=duration,
        user_id=session.get('user_id', 'anonymous')
    )
    return response

# MAIN ROUTES (Keep these in app.py to avoid circular imports)
@app.route('/')
def index():
    """Home page - redirect authenticated users to chat"""
    user = session.get('firebase_user')
    if user:
        # Redirect authenticated users to chat interface
        return redirect('/chat')
    else:
        # Show landing page for unauthenticated users
        return render_template('landing.html')

@app.route('/chat')
def chat_page():
    user = session.get('firebase_user') 
    if not user:
        return render_template('index.html', show_auth=True)
    return render_template('chat.html', user=user)

# AUTHENTICATION ROUTES
@app.route('/auth/verify', methods=['POST'])
def verify_auth():
    """Verify Firebase token and create session"""
    try:
        data = request.get_json() or {}
        token = data.get('token')
        name = data.get('name', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 400

        user_data = firebase_manager.verify_token(token)
        if not user_data:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Create/update user record
        user_data['name'] = name or user_data.get('name', '')
        firebase_manager.create_user_record(user_data)

        # Set session
        session['firebase_user'] = {
            'uid': user_data['uid'],
            'email': user_data.get('email', ''),
            'name': user_data.get('name', '')
        }
        
        logger.info(f"User authenticated successfully: {user_data.get('email')}")
        
        return jsonify({
            'success': True,
            'user': session['firebase_user'],
            'message': 'Authentication successful'
        })

    except Exception as e:
        logger.error(f"Auth verification error: {e}")
        return jsonify({'success': False, 'error': 'Authentication failed'}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    """Logout user and clear session"""
    user_email = session.get('firebase_user', {}).get('email', 'unknown')
    session.pop('firebase_user', None)
    logger.info(f"User logged out: {user_email}")
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/auth/status')
def auth_status():
    """Check authentication status"""
    user = session.get('firebase_user')
    return jsonify({
        'success': True,
        'authenticated': bool(user),
        'user': user or {}
    })



# UPLOAD ROUTE (Fixed)
@app.route('/upload', methods=['GET', 'POST'])
def upload_document():
    """Handle document uploads with proper authentication"""
    if request.method == 'GET':
        return render_template('upload.html')
    
    # Check authentication - MORE FORGIVING CHECK
    user = session.get('firebase_user')
    if not user or not user.get('uid'):
        logger.warning(f"Upload attempt without authentication. Session: {session}")
        return jsonify({
            'success': False, 
            'error': 'Authentication required',
            'code': 'AUTH_REQUIRED'
        }), 401

    try:
        # File validation
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if not doc_processor.validate_file(file):
            return jsonify({
                'success': False, 
                'error': 'Invalid file type or size. Supported: PDF, PPTX, PNG, JPG (Max 16MB)'
            }), 400

        logger.info(f"Processing upload for user {user['uid']}: {file.filename}")

        # Process document
        result = _process_document_sync(file, user['uid'])
        
        # Store metadata in Firebase if successful
        if result.get('success') and firebase_manager.is_available():
            doc_id = firebase_manager.store_document_data(user['uid'], {
                'filename': file.filename,
                'text_blocks': result.get('text_blocks', 0),  # FIX: Pass count instead of list
                'file_type': 'unknown',
                'processing_time': result.get('processing_time', 0)
            })
            result['firebase_doc_id'] = doc_id

        logger.info(f"Upload completed for user {user['uid']}: {result.get('success', False)}")
        return jsonify(result)

    except Exception as e:
        logger.error(f'Upload error for user {user["uid"]}: {e}')
        return jsonify({'success': False, 'error': 'Upload processing failed'}), 500

    # After successful upload, run cleanup
    try:
        cleanup_result = cleanup_manager.cleanup_expired_files()
        logger.info(f"CLEANUP: Auto cleanup completed: {cleanup_result}")
    except Exception as e:
        logger.warning(f"CLEANUP WARNING: Auto cleanup failed: {e}")
    
    return jsonify(result)


# QUERY ROUTE (Fixed - this was missing!)
@app.route('/query', methods=['POST'])
def process_query():
    user = session.get('firebase_user')
    if not user:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401

    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        
        if not query or len(query) < 3:
            return jsonify({'success': False, 'error': 'Query too short'}), 400

        # Check cache
        cache_key = f"query:{user['uid']}:{hashlib.md5(query.encode()).hexdigest()}"
        cached = cache_manager.get(cache_key)
        if cached:
            cached['from_cache'] = True
            return jsonify(cached)

        # Retrieve and generate
        retriever = Retriever(user_id=user['uid'])
        retrieval = retriever.retrieve(query)
        
        if not retrieval.get('success'):
            return jsonify({'success': False, 'error': 'Retrieval failed'}), 500

        generation = generator.generate_answer(query, retrieval['documents'])
        if not generation.get('success'):
            return jsonify({'success': False, 'error': 'Generation failed'}), 500

        result = {
            'success': True,
            'answer': generation['answer'],
            'sources': retrieval['documents'][:3],
            'confidence': generation.get('confidence', 0.8),
            'from_cache': False
        }

        cache_manager.set(cache_key, result, expire=3600)
        return jsonify(result)

    except Exception as e:
        logger.error(f'Query error: {e}')
        return jsonify({'success': False, 'error': 'Query processing failed'}), 500

def _process_document_sync(file, user_id: str) -> Dict[str, Any]:
    start = time.time()
    try:
        vs = VectorStore(user_id=user_id)
        upload_id = doc_processor.generate_upload_id()

        # Process pipeline
        pr = doc_processor.process_document(file, upload_id)
        if not pr.get('success'):
            return {'success': False, 'error': pr.get('error')}
            
        te = text_extractor.extract_text(upload_id)
        if not te.get('success'):
            return {'success': False, 'error': te.get('error')}
            
        blocks = te.get('text_blocks', [])
        if not blocks:
            return {'success': False, 'error': 'No text extracted'}

        emb = embedder.create_embeddings_cached(blocks, user_id)
        if not emb.get('success'):
            return {'success': False, 'error': emb.get('error')}
            
        vectors = emb.get('embeddings', [])
        if not vectors:
            return {'success': False, 'error': 'Embedding failed'}

        st = vs.add_documents(vectors, upload_id)
        if not st.get('success'):
            return {'success': False, 'error': st.get('error')}

        return {
            'success': True,
            'upload_id': upload_id,
            'text_blocks': len(blocks),
            'processing_time': round(time.time() - start, 2)
        }

    except Exception as e:
        logger.error(f"Processing failed for {user_id}: {e}")
        return {'success': False, 'error': str(e)}


@app.route('/cleanup/stats')
def cleanup_stats():
    """Get storage statistics"""
    user = session.get('firebase_user')
    if not user:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    stats = cleanup_manager.get_storage_stats()
    return jsonify({'success': True, 'stats': stats})

@app.route('/cleanup/user', methods=['POST'])
def cleanup_user_files():
    """Clean up current user's files"""
    user = session.get('firebase_user')
    if not user:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        result = cleanup_manager.force_cleanup_user(user['uid'])
        return jsonify({'success': True, 'cleanup': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/admin/cleanup-user-data', methods=['POST'])
def cleanup_user_data():
    """Admin endpoint to clean up user data isolation issues"""
    user = session.get('firebase_user')
    if not user:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        # Clean up vector store for current user
        vector_store = VectorStore(user_id=user['uid'])
        cleanup_result = vector_store.clear_user_data()
        
        # Get stats
        stats = vector_store.get_stats()
        
        return jsonify({
            'success': True,
            'cleanup_result': cleanup_result,
            'stats': stats,
            'message': 'User data cleanup completed'
        })
        
    except Exception as e:
        logger.error(f'User data cleanup error: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/user-stats')
def get_user_stats():
    """Get current user's data statistics"""
    user = session.get('firebase_user')
    if not user:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        vector_store = VectorStore(user_id=user['uid'])
        stats = vector_store.get_stats()
        
        # Get chat history count
        from modules.chat_history import ChatHistoryManager
        chat_history = ChatHistoryManager()
        conversations = chat_history.get_user_conversations(user['uid'])
        
        return jsonify({
            'success': True,
            'user_id': user['uid'],
            'vector_store_stats': stats,
            'conversation_count': len(conversations),
            'conversations': conversations
        })
        
    except Exception as e:
        logger.error(f'User stats error: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'service': 'Lumina RAG'})

if __name__ == '__main__':
    logger.info("Starting Lumina RAG application...")
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000, threaded=True)

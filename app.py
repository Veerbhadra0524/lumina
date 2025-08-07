import os
import time
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from functools import wraps
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────────────
# 🔧 Enhanced Logging Configuration
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()  # Load environment variables from .env

# Ensure logs directory exists
LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

# Configure root logger (Windows-safe)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),                 # Log to console
        logging.FileHandler(f'{LOG_DIR}/app.log')  # Log to file logs/app.log
    ]
)
logger = logging.getLogger(__name__)
logger.info("APP: Starting Lumina RAG application initialization...")

# ──────────────────────────────────────────────────────────────────────────────
# Import application components
# ──────────────────────────────────────────────────────────────────────────────
from config import Config
from modules.document_processor import DocumentProcessor
from modules.text_extractor    import TextExtractor
from modules.embedder          import Embedder
from modules.vector_store      import VectorStore
from modules.retriever         import Retriever
from modules.generator         import Generator
from modules.monitoring        import PerformanceMonitor
from modules.cache_manager     import CacheManager

# ──────────────────────────────────────────────────────────────────────────────
# 🔧 Firebase Integration & Auth Middleware
# ──────────────────────────────────────────────────────────────────────────────
from modules.firebase_manager  import FirebaseManager
from modules.auth_middleware   import require_auth, get_current_user

logger.info("APP: Initializing Firebase manager...")
firebase_manager = FirebaseManager()
if firebase_manager.is_available():
    logger.info("APP: Firebase integration: ENABLED")
else:
    logger.warning("APP: Firebase integration: DISABLED - App will run in local mode")

# ──────────────────────────────────────────────────────────────────────────────
# Flask App Initialization
# ──────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Ensure upload and vector store directories exist
os.makedirs(Config.UPLOAD_FOLDER,     exist_ok=True)
os.makedirs(Config.VECTOR_STORE_PATH, exist_ok=True)

# Thread pool for any asynchronous tasks
executor = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)

# ──────────────────────────────────────────────────────────────────────────────
# Component Instantiation
# ──────────────────────────────────────────────────────────────────────────────
doc_processor = DocumentProcessor()
text_extractor = TextExtractor()
embedder       = Embedder()
generator      = Generator()
monitor        = PerformanceMonitor()
cache_manager  = CacheManager()

# ──────────────────────────────────────────────────────────────────────────────
# Helper: Create or retrieve a per-user session ID
# ──────────────────────────────────────────────────────────────────────────────
def get_user_session_id() -> str:
    if 'user_id' not in session:
        raw = f"{request.remote_addr}_{datetime.now(timezone.utc)}"
        session['user_id'] = hashlib.md5(raw.encode()).hexdigest()[:12]
        logger.info(f"Created new session ID: {session['user_id']}")
    return session['user_id']

# ──────────────────────────────────────────────────────────────────────────────
# Request Timing & Metrics
# ──────────────────────────────────────────────────────────────────────────────
@app.before_request
def before_request():
    request.start_time = time.time()
    if 'user_id' not in session:
        get_user_session_id()

@app.after_request
def after_request(response):
    duration = time.time() - request.start_time
    monitor.record_request(
        endpoint    = request.endpoint,
        method      = request.method,
        status_code = response.status_code,
        duration    = duration,
        user_id     = session.get('user_id', 'anonymous')
    )
    return response

# ──────────────────────────────────────────────────────────────────────────────
# Authentication Routes
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/auth/verify', methods=['POST'])
def verify_auth():
    """
    Verify Firebase ID token, create or update user in Firebase,
    and store user info in session.
    """
    try:
        data  = request.get_json() or {}
        token = data.get('token')
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 400

        user_data = firebase_manager.verify_token(token)
        if not user_data:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        # Create or update user record in Firebase
        firebase_manager.create_user_record(user_data)

        session['firebase_user'] = {
            'uid':   user_data['uid'],
            'email': user_data.get('email', ''),
            'name':  user_data.get('name', '')
        }
        return jsonify({
            'success': True,
            'user':    session['firebase_user'],
            'message': 'Authentication successful'
        })

    except Exception as e:
        logger.error(f"Auth verification error: {e}")
        return jsonify({'success': False, 'error': 'Authentication failed'}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    """Remove Firebase user from session"""
    session.pop('firebase_user', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/auth/status')
def auth_status():
    """Return authentication status and user info (if logged in)"""
    user = session.get('firebase_user')
    return jsonify({
        'success':       True,
        'authenticated': bool(user),
        'user':          user or {}
    })

# ──────────────────────────────────────────────────────────────────────────────
# Main Chat Interface
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ──────────────────────────────────────────────────────────────────────────────
# Document Upload (Protected)
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/upload', methods=['GET', 'POST'])
@require_auth
def upload_document():
    """
    Handle document uploads: validate, process, extract text,
    embed, store in FAISS, and log metadata to Firebase.
    """
    user = get_current_user()

    if request.method == 'GET':
        return render_template('upload.html')

    # --- 1) Validate file presence ---
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    if not doc_processor.validate_file(file):
        return jsonify({'success': False, 'error': 'Invalid file type/size'}), 400

    # --- 2) Process document synchronously ---
    result = _process_document_sync(file, user['uid'])

    # --- 3) Store document metadata in Firebase ---
    if result.get('success') and firebase_manager.is_available():
        doc_id = firebase_manager.store_document_data(user['uid'], {
            'filename':    file.filename,
            'text_blocks': result.get('text_blocks', []),
            'processing_time': result.get('processing_time')
        })
        result['firebase_doc_id'] = doc_id

    return jsonify(result), (200 if result.get('success') else 500)

# ──────────────────────────────────────────────────────────────────────────────
# Query Processing (Protected)
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/query', methods=['POST'])
@require_auth
def process_query():
    """
    Handle user queries: caching, retrieval, answer generation,
    and logging each query to Firebase.
    """
    user  = get_current_user()
    data  = request.get_json() or {}
    query = data.get('query', '').strip()
    if not query or len(query) < 3:
        return jsonify({'success': False, 'error': 'Query too short or empty'}), 400

    # --- 1) Check cache ---
    cache_key = f"query:{user['uid']}:{hashlib.md5(query.encode()).hexdigest()}"
    cached   = cache_manager.get(cache_key)
    if cached:
        cached['from_cache'] = True
        return jsonify(cached)

    # --- 2) Retrieve & generate answer ---
    retriever = Retriever(user_id=user['uid'])
    retrieval  = retriever.retrieve(query)
    if not retrieval.get('success'):
        return jsonify({'success': False, 'error': retrieval.get('error')}), 500

    gen = generator.generate_answer(query, retrieval['documents'])
    if not gen.get('success'):
        return jsonify({'success': False, 'error': gen.get('error')}), 500

    result = {
        'success':        True,
        'answer':         gen['answer'],
        'sources':        retrieval['documents'][:3],
        'confidence':     gen.get('confidence', 0),
        'method':         gen.get('method'),
        'from_cache':     False,
        'user_id':        user['uid'],
        'documents_found': len(retrieval['documents'])
    }

    # --- 3) Cache & log to Firebase ---
    cache_manager.set(cache_key, result, expire=3600)
    if firebase_manager.is_available():
        firebase_manager.store_query_log(user['uid'], query, result['answer'], result['sources'])

    return jsonify(result)

# ──────────────────────────────────────────────────────────────────────────────
# User History & Analytics (Protected)
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/history')
@require_auth
def get_history():
    """Fetch a list of this user’s uploaded documents from Firebase."""
    user      = get_current_user()
    documents = firebase_manager.get_user_documents(user['uid'])
    return jsonify({'success': True, 'documents': documents, 'user': user})

@app.route('/analytics')
@require_auth
def get_analytics():
    """
    Fetch analytics data from Firebase.
    Admin users (by email) see global data; others see only their own.
    """
    user     = get_current_user()
    is_admin = (user.get('email') == Config.ADMIN_EMAIL)
    analytics = firebase_manager.get_analytics_data(None if is_admin else user['uid'])
    return jsonify({'success': True, 'analytics': analytics, 'is_admin': is_admin})

# ──────────────────────────────────────────────────────────────────────────────
# Status, Clear, and Health Endpoints (unchanged)
# ──────────────────────────────────────────────────────────────────────────────
# ... your existing /status, /clear, /health routes go here exactly as before ...

# ──────────────────────────────────────────────────────────────────────────────
# Synchronous document processing helper
# ──────────────────────────────────────────────────────────────────────────────
def _process_document_sync(file, user_id: str) -> Dict[str, Any]:
    start = time.time()
    try:
        vs = VectorStore(user_id=user_id)
        upload_id = doc_processor.generate_upload_id()

        # Process → Extract → Embed → Store
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
            'success':        True,
            'upload_id':      upload_id,
            'text_blocks':    len(blocks),
            'processing_time': round(time.time() - start, 2),
            'cache_hit_rate': emb.get('cache_hit_rate', 0)
        }

    except Exception as e:
        logger.error(f"Document processing failed for {user_id}: {e}")
        return {'success': False, 'error': str(e)}

# ──────────────────────────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    logger.info("APP: Initialization complete, launching Flask server...")
    app.run(
        debug   = Config.DEBUG,
        host    = '0.0.0.0',
        port    = 5000,
        threaded= True
    )

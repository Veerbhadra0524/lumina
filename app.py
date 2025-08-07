from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import os
import logging
from datetime import datetime, timezone
import hashlib
import time
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
load_dotenv()

from config import Config
from modules.document_processor import DocumentProcessor
from modules.text_extractor import TextExtractor
from modules.embedder import Embedder  # ✅ CORRECT: Import Embedder
from modules.vector_store import VectorStore
from modules.retriever import Retriever
from modules.generator import Generator
from modules.monitoring import PerformanceMonitor
from modules.cache_manager import CacheManager

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create data directories
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.VECTOR_STORE_PATH, exist_ok=True)

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=4)

# Initialize components
doc_processor = DocumentProcessor()
text_extractor = TextExtractor()
embedder = Embedder()  # ✅ CORRECT: Use Embedder class
generator = Generator()
monitor = PerformanceMonitor()
cache_manager = CacheManager()

def get_user_session_id() -> str:
    """Generate or retrieve user session ID"""
    if 'user_id' not in session:
        raw_data = f"{request.remote_addr}_{datetime.now(timezone.utc)}"
        session['user_id'] = hashlib.md5(raw_data.encode()).hexdigest()[:12]
        logger.info(f"Created new user session: {session['user_id']}")
    return session['user_id']

@app.before_request
def before_request():
    """Set up request context"""
    request.start_time = time.time()
    
    # Ensure user session
    if 'user_id' not in session:
        get_user_session_id()

@app.after_request
def after_request(response):
    """Log request metrics"""
    duration = time.time() - request.start_time
    monitor.record_request(
        endpoint=request.endpoint,
        method=request.method,
        status_code=response.status_code,
        duration=duration,
        user_id=session.get('user_id', 'anonymous')
    )
    
    return response

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_document():
    """Enhanced document upload with async processing"""
    if request.method == 'GET':
        return render_template('upload.html')
    
    user_id = get_user_session_id()
    
    try:
        # Validate request
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Validate file
        if not doc_processor.validate_file(file):
            return jsonify({
                'success': False, 
                'error': 'Invalid file type or size. Supported: PDF, PPTX, PNG, JPG (Max 16MB)'
            }), 400
        
        # Process document
        result = _process_document_sync(file, user_id)
        
        if result['success']:
            logger.info(f"Document upload completed for user {user_id}")
            return jsonify(result)
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Processing failed')}), 500
            
    except Exception as e:
        logger.error(f"Upload error for user {user_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Processing failed'}), 500

def _process_document_sync(file, user_id: str) -> Dict[str, Any]:
    """Synchronous document processing function"""
    start_time = time.time()
    
    try:
        # Create user-specific vector store
        vector_store = VectorStore(user_id=user_id)
        
        # Generate upload ID
        upload_id = doc_processor.generate_upload_id()
        
        # Step 1: Process document
        process_result = doc_processor.process_document(file, upload_id)
        if not process_result.get('success', False):
            return {'success': False, 'error': process_result.get('error', 'Document processing failed')}
        
        # Step 2: Extract text
        text_result = text_extractor.extract_text(upload_id)
        if not text_result.get('success', False):
            return {'success': False, 'error': text_result.get('error', 'Text extraction failed')}
        
        text_blocks = text_result.get('text_blocks', [])
        if not text_blocks:
            return {'success': False, 'error': 'No text blocks extracted from document'}
        
        # Step 3: Generate embeddings
        embedding_result = embedder.create_embeddings_cached(text_blocks, user_id)
        if not embedding_result.get('success', False):
            return {'success': False, 'error': embedding_result.get('error', 'Embedding generation failed')}
        
        embeddings = embedding_result.get('embeddings', [])
        if not embeddings:
            return {'success': False, 'error': 'No embeddings generated'}
        
        # Step 4: Store in vector database
        store_result = vector_store.add_documents(embeddings, upload_id)
        if not store_result.get('success', False):
            return {'success': False, 'error': store_result.get('error', 'Vector storage failed')}
        
        processing_time = time.time() - start_time
        
        return {
            'success': True,
            'upload_id': upload_id,
            'message': f'Document processed successfully. {len(text_blocks)} text blocks extracted.',
            'text_blocks': len(text_blocks),
            'processing_time': round(processing_time, 2),
            'cache_hit_rate': embedding_result.get('cache_hit_rate', 0)
        }
        
    except Exception as e:
        logger.error(f"Document processing error for user {user_id}: {str(e)}")
        return {'success': False, 'error': f'Processing failed: {str(e)}'}

@app.route('/query', methods=['POST'])
def process_query():
    """Enhanced query processing with caching"""
    user_id = get_user_session_id()
    
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'success': False, 'error': 'Query is required'}), 400
        
        if len(query) < 3:
            return jsonify({'success': False, 'error': 'Query too short (minimum 3 characters)'}), 400
        
        # Check cache first
        cache_key = f"query:{user_id}:{hashlib.md5(query.encode()).hexdigest()}"
        cached_result = cache_manager.get(cache_key)
        
        if cached_result:
            cached_result['from_cache'] = True
            return jsonify(cached_result)
        
        # Create user-specific retriever
        retriever = Retriever(user_id=user_id)
        
        # Retrieve relevant documents
        retrieval_result = retriever.retrieve(query)
        if not retrieval_result.get('success', False):
            return jsonify({
                'success': False, 
                'error': retrieval_result.get('error', 'Document retrieval failed')
            }), 500
        
        documents = retrieval_result.get('documents', [])
        
        # Generate answer
        generation_result = generator.generate_answer(query, documents)
        if not generation_result.get('success', False):
            return jsonify({
                'success': False, 
                'error': generation_result.get('error', 'Answer generation failed')
            }), 500
        
        result = {
            'success': True,
            'answer': generation_result.get('answer', ''),
            'sources': documents[:3],  # Top 3 sources
            'confidence': generation_result.get('confidence', 0.8),
            'user_id': user_id,
            'documents_found': len(documents),
            'method': generation_result.get('method', 'unknown'),
            'from_cache': False
        }
        
        # Cache the result (expire in 1 hour)
        cache_manager.set(cache_key, result, expire=3600)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Query processing error for user {user_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Query processing failed'}), 500

@app.route('/status')
def get_status():
    """Enhanced system status with metrics"""
    user_id = get_user_session_id()
    
    try:
        vector_store = VectorStore(user_id=user_id)
        stats = vector_store.get_stats()
        system_metrics = monitor.get_metrics()
        
        return jsonify({
            'success': True,
            'status': 'running',
            'user_id': user_id,
            'documents_indexed': stats.get('total_documents', 0),
            'embedding_model': Config.EMBEDDING_MODEL,
            'use_local_llm': Config.USE_LOCAL_LLM,
            'gemini_api_configured': bool(Config.GEMINI_API_KEY),
            'system_metrics': system_metrics,
            'cache_stats': cache_manager.get_stats()
        })
    except Exception as e:
        logger.error(f"Status error for user {user_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/clear', methods=['POST'])
def clear_user_data():
    """Clear user data with confirmation"""
    user_id = get_user_session_id()
    
    try:
        vector_store = VectorStore(user_id=user_id)
        result = vector_store.clear_index()
        
        # Clear user's cache
        cache_manager.clear_user_cache(user_id)
        
        if result.get('success', False):
            logger.info(f"Cleared user data for {user_id}")
            return jsonify({
                'success': True,
                'message': f'Cleared all data for user {user_id}'
            })
        else:
            return jsonify({
                'success': False, 
                'error': result.get('error', 'Failed to clear data')
            }), 500
    except Exception as e:
        logger.error(f"Clear error for user {user_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to clear user data'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for load balancers"""
    try:
        # Quick health checks
        embedding_healthy = embedder.health_check()
        generator_healthy = hasattr(generator, 'health_check') and generator.health_check() or True
        
        health_status = {
            'status': 'healthy' if all([embedding_healthy, generator_healthy]) else 'unhealthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'components': {
                'embedder': 'healthy' if embedding_healthy else 'unhealthy',
                'generator': 'healthy' if generator_healthy else 'unhealthy',
                'cache': 'healthy' if cache_manager.health_check() else 'unhealthy'
            }
        }
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 503

if __name__ == '__main__':
    logger.info(f"Starting Lumina RAG application")
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000, threaded=True)

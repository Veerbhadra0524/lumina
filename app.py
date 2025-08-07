from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import os
import logging
from datetime import datetime, timezone
import hashlib

from dotenv import load_dotenv
load_dotenv()

from config import Config
from modules.document_processor import DocumentProcessor
from modules.text_extractor import TextExtractor
from modules.embedder import Embedder
from modules.vector_store import VectorStore
from modules.retriever import Retriever
from modules.generator import Generator


import hashlib

def get_user_session_id():
    """Get or create user session ID"""
    if 'user_id' not in session:
        # Create unique session ID
        session['user_id'] = hashlib.md5(
            f"{request.remote_addr}_{datetime.now()}".encode()
        ).hexdigest()[:12]
    return session['user_id']

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

# Initialize components that DON'T need request context
doc_processor = DocumentProcessor()
text_extractor = TextExtractor()
embedder = Embedder()
generator = Generator()

@app.before_request
def ensure_user_session():
    """Ensure user has a session ID before any request processing"""
    if 'user_id' not in session:
        raw = f"{request.remote_addr}_{datetime.now(timezone.utc)}".encode()
        session['user_id'] = hashlib.md5(raw).hexdigest()[:12]
        logger.info(f"Created new user session: {session['user_id']}")

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_document():
    """Document upload and processing"""
    if request.method == 'GET':
        return render_template('upload.html')
    
    # ✅ CORRECT - Create user-specific vector store inside request context
    user_id = session.get('user_id', 'default')
    vector_store = VectorStore(user_id=user_id)
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file
        if not doc_processor.validate_file(file):
            return jsonify({'error': 'Invalid file type or size'}), 400
        
        # Process document
        upload_id = doc_processor.generate_upload_id()
        result = doc_processor.process_document(file, upload_id)
        
        if not result.get('success', False):
            return jsonify({'error': result.get('error', 'Document processing failed')}), 500
        
        # Extract text
        text_result = text_extractor.extract_text(upload_id)
        if not text_result.get('success', False):
            return jsonify({'error': text_result.get('error', 'Text extraction failed')}), 500
        
        # Generate embeddings
        text_blocks = text_result.get('text_blocks', [])
        if not text_blocks:
            return jsonify({'error': 'No text blocks extracted from document'}), 500
            
        result = embedder.create_embeddings(text_blocks)
        if result["success"]:
            vector_store.add_documents(result["data"], upload_id)

            
    
        # Store in user-specific vector database
        embeddings = result.get('data', [])
        if not embeddings:
            return jsonify({'error': 'No embeddings generated'}), 500
            
        store_result = vector_store.add_documents(embeddings, upload_id)
        if not store_result.get('success', False):
            return jsonify({'error': store_result.get('error', 'Vector storage failed')}), 500
        
        return jsonify({
            'success': True,
            'upload_id': upload_id,
            'message': f'Document processed successfully. {len(text_blocks)} text blocks extracted.',
            'text_blocks': len(text_blocks),
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Upload error for user {user_id}: {str(e)}")
        return jsonify({'error': 'Processing failed'}), 500

@app.route('/query', methods=['POST'])
def process_query():
    """Process user query and return answer"""
    # ✅ CORRECT - Create user-specific retriever inside request context
    user_id = session.get('user_id', 'default')
    retriever = Retriever(user_id=user_id)
    
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        if len(query) < 3:
            return jsonify({'error': 'Query too short'}), 400
        
        # Retrieve relevant documents from user's vector store
        retrieval_result = retriever.retrieve(query)
        if not retrieval_result.get('success', False):
            return jsonify({'error': retrieval_result.get('error', 'Document retrieval failed')}), 500
        
        # Generate answer using retrieved documents
        documents = retrieval_result.get('documents', [])
        generation_result = generator.generate_answer(query, documents)
        
        if not generation_result.get('success', False):
            return jsonify({'error': generation_result.get('error', 'Answer generation failed')}), 500
        
        return jsonify({
            'success': True,
            'answer': generation_result.get('answer', ''),
            'sources': documents[:3],  # Top 3 sources
            'confidence': generation_result.get('confidence', 0.8),
            'user_id': user_id,
            'documents_found': len(documents)
        })
        
    except Exception as e:
        logger.error(f"Query error for user {user_id}: {str(e)}")
        return jsonify({'error': 'Query processing failed'}), 500

@app.route('/status')
def get_status():
    """Get system status for current user"""
    user_id = session.get('user_id', 'default')
    vector_store = VectorStore(user_id=user_id)
    
    try:
        stats = vector_store.get_stats()
        return jsonify({
            'success': True,
            'status': 'running',
            'user_id': user_id,
            'documents_indexed': stats.get('total_documents', 0),
            'embedding_model': Config.EMBEDDING_MODEL,
            'use_local_llm': Config.USE_LOCAL_LLM,
            'gemini_api_configured': bool(Config.GEMINI_API_KEY)
        })
    except Exception as e:
        logger.error(f"Status error for user {user_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/clear', methods=['POST'])
def clear_user_data():
    """Clear current user's vector store"""
    user_id = session.get('user_id', 'default')
    vector_store = VectorStore(user_id=user_id)
    
    try:
        result = vector_store.clear_index()
        if result.get('success', False):
            return jsonify({
                'success': True,
                'message': f'Cleared all data for user {user_id}'
            })
        else:
            return jsonify({'error': result.get('error', 'Failed to clear data')}), 500
    except Exception as e:
        logger.error(f"Clear error for user {user_id}: {str(e)}")
        return jsonify({'error': 'Failed to clear user data'}), 500

if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000)

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # File upload settings
    UPLOAD_FOLDER = 'data/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'.pdf', '.pptx', '.png', '.jpg', '.jpeg'}
    
    # Vector store settings
    VECTOR_STORE_PATH = 'data/vector_store'
    EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
    EMBEDDING_DIMENSION = 384
    
    # OCR settings
    OCR_ENGINE = 'tesseract'
    MIN_TEXT_LENGTH = 3
    
    # Generation settings
    USE_LOCAL_LLM = os.getenv('USE_LOCAL_LLM', 'False').lower() == 'true'
    
    # API keys - UPDATED
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # NEW: Gemini API key
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')   # Keep for backward compatibility
    HF_API_KEY = os.getenv('HF_API_KEY')
    
    # Local model settings
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    LOCAL_MODEL_NAME = os.getenv('LOCAL_MODEL_NAME', 'llama3.2:3b')

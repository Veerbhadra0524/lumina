from flask import Blueprint, jsonify
import logging

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

@api_bp.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'Lumina RAG API'})

@api_bp.route('/status')
def status():
    return jsonify({'status': 'ok', 'message': 'API is running'})

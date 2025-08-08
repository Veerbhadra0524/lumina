from flask import Flask
from flask_cors import CORS
import logging

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Import and register blueprints AFTER app creation
    from blueprints.main_routes import main_bp
    from blueprints.auth_routes import auth_bp
    from blueprints.chat_routes import chat_bp
    from blueprints.upload_routes import upload_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')  
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(upload_bp, url_prefix='/upload')
    
    return app

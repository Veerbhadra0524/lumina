from flask import Blueprint, render_template, session
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page, optionally shows user info if logged in"""
    user = session.get('firebase_user')
    return render_template('index.html', user=user)

@main_bp.route('/chat')
def chat():
    user = session.get('firebase_user')
    if not user:
        return render_template('index.html', show_auth=True)
    return render_template('chat.html', user=user)

@main_bp.route('/profile')
def profile():
    user = session.get('firebase_user')
    if not user:
        return render_template('index.html', show_auth=True)
    return render_template('profile.html', user=user)

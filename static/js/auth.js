import { signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut, onAuthStateChanged } 
from 'https://www.gstatic.com/firebasejs/10.3.0/firebase-auth.js';

class AuthManager {
    constructor() {
        this.currentUser = null;
        this.setupEventListeners();
        this.checkAuthState();
    }
    
    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
        
        // Form submissions
        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });
        
        document.getElementById('register-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRegister();
        });
        
        // Logout
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.handleLogout();
        });
    }
    
    checkAuthState() {
        onAuthStateChanged(window.firebaseAuth, (user) => {
            if (user) {
                this.handleAuthSuccess(user);
            } else {
                this.showAuthModal();
            }
        });
    }
    
    async handleLogin() {
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        
        this.showLoading(true);
        this.clearError();
        
        try {
            const userCredential = await signInWithEmailAndPassword(window.firebaseAuth, email, password);
            const token = await userCredential.user.getIdToken();
            
            // Verify with backend
            const response = await fetch('/auth/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token })
            });
            
            const result = await response.json();
            if (result.success) {
                this.handleAuthSuccess(userCredential.user);
            } else {
                this.showError(result.error || 'Login failed');
            }
            
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    async handleRegister() {
        const name = document.getElementById('register-name').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        
        if (password.length < 6) {
            this.showError('Password must be at least 6 characters');
            return;
        }
        
        this.showLoading(true);
        this.clearError();
        
        try {
            const userCredential = await createUserWithEmailAndPassword(window.firebaseAuth, email, password);
            const token = await userCredential.user.getIdToken();
            
            // Verify with backend
            const response = await fetch('/auth/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    token,
                    name: name
                })
            });
            
            const result = await response.json();
            if (result.success) {
                this.handleAuthSuccess(userCredential.user);
            } else {
                this.showError(result.error || 'Registration failed');
            }
            
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    async handleLogout() {
        try {
            await signOut(window.firebaseAuth);
            
            // Logout from backend
            await fetch('/auth/logout', { method: 'POST' });
            
            this.showAuthModal();
        } catch (error) {
            console.error('Logout error:', error);
        }
    }
    
    handleAuthSuccess(user) {
        this.currentUser = user;
        document.getElementById('auth-modal').style.display = 'none';
        document.getElementById('main-app').style.display = 'block';
        document.getElementById('user-name').textContent = `Welcome, ${user.displayName || user.email}!`;
    }
    
    showAuthModal() {
        document.getElementById('auth-modal').style.display = 'block';
        document.getElementById('main-app').style.display = 'none';
    }
    
    switchTab(tab) {
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
        
        if (tab === 'login') {
            document.getElementById('login-form').style.display = 'block';
            document.getElementById('register-form').style.display = 'none';
            document.getElementById('auth-title').textContent = 'Welcome Back';
        } else {
            document.getElementById('login-form').style.display = 'none';
            document.getElementById('register-form').style.display = 'block';
            document.getElementById('auth-title').textContent = 'Create Account';
        }
    }
    
    showError(message) {
        const errorEl = document.getElementById('auth-error');
        errorEl.textContent = message;
        errorEl.style.display = 'block';
    }
    
    clearError() {
        document.getElementById('auth-error').style.display = 'none';
    }
    
    showLoading(show) {
        document.getElementById('auth-loading').style.display = show ? 'block' : 'none';
    }
}

// Initialize when DOM loads
document.addEventListener('DOMContentLoaded', () => {
    new AuthManager();
});

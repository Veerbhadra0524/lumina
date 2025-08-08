// Authentication Manager - Fixed for Compat SDK
class AuthManager {
    constructor() {
        this.auth = null;
        this.currentUser = null;
        this.initialized = false;
        
        // Wait for Firebase to be ready
        if (window.firebaseAuth) {
            this.initializeAuth();
        } else {
            window.addEventListener('firebaseReady', () => {
                this.initializeAuth();
            });
        }
    }
    
    initializeAuth() {
        this.auth = window.firebaseAuth;
        this.initialized = true;
        
        console.log('Auth Manager: Firebase ready');
        console.log('Available methods:', Object.getOwnPropertyNames(this.auth));
        
        // Set up auth state listener
        this.auth.onAuthStateChanged((user) => {
            console.log('Auth state changed:', user?.email || 'logged out');
            this.currentUser = user;
            if (user) {
                this.handleAuthSuccess(user);
            }
        });
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.bindEvents());
        } else {
            this.bindEvents();
        }
    }
    
    bindEvents() {
        // Login form
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleLogin();
            });
        }
        
        // Register form  
        const registerForm = document.getElementById('register-form');
        if (registerForm) {
            registerForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleRegister();
            });
        }
        
        // Auth buttons
        const authButtons = [
            'login-btn', 'register-btn', 'get-started-btn', 'signup-btn'
        ];
        
        authButtons.forEach(id => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.onclick = () => this.showAuthModal();
            }
        });
        
        // Logout
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.onclick = () => this.handleLogout();
        }
        
        // Tab switching
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const isLogin = btn.textContent.trim().toLowerCase() === 'login';
                this.switchTab(isLogin ? 'login' : 'register');
            });
        });
        
        // Modal close
        this.setupModalClose();
        
        console.log('Auth Manager: Event listeners bound');
    }
    
    setupModalClose() {
        const modal = document.getElementById('auth-modal');
        if (!modal) return;
        
        // Close button
        const closeBtn = document.getElementById('modal-close') || 
                         modal.querySelector('.modal-close') ||
                         this.createCloseButton(modal);
        
        closeBtn.onclick = () => this.hideAuthModal();
        
        // Click outside to close
        modal.addEventListener('click', (e) => {
            if (e.target === modal || e.target.classList.contains('modal-overlay')) {
                this.hideAuthModal();
            }
        });
        
        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.style.display === 'flex') {
                this.hideAuthModal();
            }
        });
    }
    
    createCloseButton(modal) {
        const closeBtn = document.createElement('button');
        closeBtn.className = 'modal-close';
        closeBtn.innerHTML = '×';
        closeBtn.style.cssText = `
            position: absolute;
            top: 15px;
            right: 20px;
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #666;
            z-index: 1001;
        `;
        modal.appendChild(closeBtn);
        return closeBtn;
    }
    
    async handleLogin() {
        if (!this.initialized || !this.auth) {
            this.showError('Firebase not ready. Please refresh the page.');
            return;
        }
        
        const email = document.getElementById('login-email')?.value?.trim();
        const password = document.getElementById('login-password')?.value;
        
        if (!email || !password) {
            this.showError('Please fill in all fields');
            return;
        }
        
        this.showLoading(true);
        this.clearError();
        
        try {
            console.log('Attempting login with:', email);
            
            // Use compat SDK method
            const userCredential = await this.auth.signInWithEmailAndPassword(email, password);
            const token = await userCredential.user.getIdToken();
            
            console.log('Firebase login successful, verifying with backend...');
            
            // Send to backend
            const response = await fetch('/auth/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('Backend verification successful');
                this.hideAuthModal();
                setTimeout(() => location.reload(), 500);
            } else {
                this.showError(result.error || 'Login failed');
            }
            
        } catch (error) {
            console.error('Login error:', error);
            this.showError(this.getErrorMessage(error));
        } finally {
            this.showLoading(false);
        }
    }
    
    async handleRegister() {
        if (!this.initialized || !this.auth) {
            this.showError('Firebase not ready. Please refresh the page.');
            return;
        }
        
        const name = document.getElementById('register-name')?.value?.trim();
        const email = document.getElementById('register-email')?.value?.trim();
        const password = document.getElementById('register-password')?.value;
        
        if (!name || !email || !password) {
            this.showError('Please fill in all fields');
            return;
        }
        
        if (password.length < 6) {
            this.showError('Password must be at least 6 characters');
            return;
        }
        
        this.showLoading(true);
        this.clearError();
        
        try {
            console.log('Attempting registration with:', email);
            
            // Use compat SDK method
            const userCredential = await this.auth.createUserWithEmailAndPassword(email, password);
            
            // Update profile
            await userCredential.user.updateProfile({ displayName: name });
            
            const token = await userCredential.user.getIdToken();
            
            console.log('Firebase registration successful, verifying with backend...');
            
            // Send to backend
            const response = await fetch('/auth/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, name })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('Backend verification successful');
                this.hideAuthModal();
                setTimeout(() => location.reload(), 500);
            } else {
                this.showError(result.error || 'Registration failed');
            }
            
        } catch (error) {
            console.error('Registration error:', error);
            this.showError(this.getErrorMessage(error));
        } finally {
            this.showLoading(false);
        }
    }
    
    async handleLogout() {
        try {
            if (this.auth) {
                await this.auth.signOut();
            }
            await fetch('/auth/logout', { method: 'POST' });
            location.reload();
        } catch (error) {
            console.error('Logout error:', error);
        }
    }
    
    handleAuthSuccess(user) {
        this.hideAuthModal();
        
        // Update UI
        const userNameSpan = document.getElementById('user-name');
        if (userNameSpan) {
            userNameSpan.textContent = user.displayName || user.email;
        }
    }
    
    showAuthModal() {
        const modal = document.getElementById('auth-modal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }
    
    hideAuthModal() {
        const modal = document.getElementById('auth-modal');
        if (modal) {
            modal.style.display = 'none';
        }
        this.clearError();
        this.clearForms();
    }
    
    switchTab(tab) {
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');
        const authTitle = document.getElementById('auth-title');
        const tabBtns = document.querySelectorAll('.tab-btn');
        
        this.clearError();
        
        // Update tabs
        tabBtns.forEach(btn => btn.classList.remove('active'));
        
        if (tab === 'login') {
            loginForm.style.display = 'block';
            registerForm.style.display = 'none';
            authTitle.textContent = 'Welcome Back';
            document.querySelector('[data-tab="login"]').classList.add('active');
        } else {
            loginForm.style.display = 'none';
            registerForm.style.display = 'block';
            authTitle.textContent = 'Create Account';
            document.querySelector('[data-tab="register"]').classList.add('active');
        }
    }
    
    clearForms() {
        const inputs = document.querySelectorAll('#auth-modal input');
        inputs.forEach(input => input.value = '');
    }
    
    showError(message) {
        const errorEl = document.getElementById('auth-error');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }
    }
    
    clearError() {
        const errorEl = document.getElementById('auth-error');
        if (errorEl) {
            errorEl.style.display = 'none';
        }
    }
    
    showLoading(show) {
        const loadingEl = document.getElementById('auth-loading');
        if (loadingEl) {
            loadingEl.style.display = show ? 'block' : 'none';
        }
    }
    
    getErrorMessage(error) {
        const messages = {
            'auth/user-not-found': 'No account found with this email',
            'auth/wrong-password': 'Incorrect password',
            'auth/email-already-in-use': 'Account already exists with this email',
            'auth/weak-password': 'Password must be at least 6 characters',
            'auth/invalid-email': 'Please enter a valid email address'
        };
        return messages[error.code] || error.message || 'An error occurred';
    }
}

// Initialize immediately
window.authManager = new AuthManager();

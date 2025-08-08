// Firebase SDK v8 (Compat) - More reliable for this use case
console.log('Loading Firebase v8 SDK...');

// Load Firebase v8 SDK
const firebaseScript = document.createElement('script');
firebaseScript.src = 'https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js';
firebaseScript.onload = function() {
    console.log('Firebase app loaded, loading auth...');
    
    const authScript = document.createElement('script');
    authScript.src = 'https://www.gstatic.com/firebasejs/8.10.1/firebase-auth.js';
    authScript.onload = function() {
        console.log('Firebase auth loaded, initializing...');
        
        // For Firebase JS SDK v7.20.0 and later, measurementId is optional
        const firebaseConfig = {
        apiKey: "AIzaSyCvPH-81OTzZuMN2bEyBX4TrXAWp7V1Rqs",
        authDomain: "lumina-rag.firebaseapp.com",
        projectId: "lumina-rag",
        storageBucket: "lumina-rag.firebasestorage.app",
        messagingSenderId: "1066185476466",
        appId: "1:1066185476466:web:2e714b7455322ed16575eb",
        measurementId: "G-EK8T8QCT57"
        };
        
        // Initialize Firebase
        firebase.initializeApp(firebaseConfig);
        
        // Make auth available globally
        window.firebaseAuth = firebase.auth();
        window.firebaseApp = firebase;
        
        console.log('Firebase initialized successfully');
        console.log('Auth methods available:', typeof window.firebaseAuth.signInWithEmailAndPassword);
        
        // Dispatch ready event
        window.dispatchEvent(new CustomEvent('firebaseReady'));
    };
    
    document.head.appendChild(authScript);
};

document.head.appendChild(firebaseScript);

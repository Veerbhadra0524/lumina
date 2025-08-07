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

console.log("🔥 Initializing Firebase with config:", firebaseConfig);

// Initialize Firebase
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.3.0/firebase-app.js';
import { getAuth } from 'https://www.gstatic.com/firebasejs/10.3.0/firebase-auth.js';

try {
    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    window.firebaseAuth = auth;
    console.log("✅ Firebase initialized successfully");
} catch (error) {
    console.error("❌ Firebase initialization error:", error);
}

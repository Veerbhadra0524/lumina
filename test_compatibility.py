import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from modules.firebase_manager import FirebaseManager

print("Testing Firebase connection...")
firebase = FirebaseManager()

if firebase.is_available():
    print("SUCCESS: Firebase is working correctly!")
else:
    print("FAILED: Firebase connection failed")
    print("Make sure firebase-service-account.json exists in project root")

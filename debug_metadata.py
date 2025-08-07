import os
import json
from config import Config

def debug_upload_metadata(upload_id):
    """Debug metadata structure for an upload"""
    config = Config()
    upload_dir = os.path.join(config.UPLOAD_FOLDER, upload_id)
    metadata_path = os.path.join(upload_dir, 'metadata.json')
    
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        print(f"📋 Metadata for upload {upload_id}:")
        print(f"   Keys: {list(metadata.keys())}")
        
        if 'pages' in metadata:
            print(f"   Pages count: {len(metadata['pages'])}")
            for i, page in enumerate(metadata['pages']):
                print(f"   Page {i} keys: {list(page.keys())}")
                if 'path' in page:
                    print(f"   Page {i} path: {page['path']}")
                    print(f"   Path exists: {os.path.exists(page['path'])}")
        else:
            print("   ❌ No 'pages' key found!")
    else:
        print(f"❌ Metadata file not found: {metadata_path}")

# Usage: debug_upload_metadata("your-upload-id")

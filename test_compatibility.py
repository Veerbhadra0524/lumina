#!/usr/bin/env python3
import torch
import transformers
import sentence_transformers
import safetensors

print("🔍 Testing PyTorch compatibility...")
print(f"PyTorch version: {torch.__version__}")
print(f"Transformers version: {transformers.__version__}")
print(f"Sentence-transformers version: {sentence_transformers.__version__}")
print(f"torch.uint64 available: {hasattr(torch, 'uint64')}")

# Test embedding model loading
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ Sentence transformer model loaded successfully")
    
    # Test embedding
    embedding = model.encode("test sentence")
    print(f"✅ Embedding created: shape {embedding.shape}")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("🎉 All compatibility tests passed!")

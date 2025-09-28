# 🌌 Lumina RAG

**AI-Powered Retrieval-Augmented Generation for Documents**

Transform static documents (PDFs, PPTX, images) into an **interactive knowledge base** with natural language querying. Lumina RAG combines **OCR, vector embeddings, hybrid search, and multi-modal LLMs** to deliver contextual answers with source citations.

---

## 🚀 Features

* 📄 **Multi-format Support**: PDF, PPTX, PNG, JPG
* 🔍 **Hybrid Semantic Search**: FAISS vector search + keyword matching
* 🧠 **AI-Powered Q\&A**: Google Gemini (Vision) + local LLM fallback
* ✨ **Advanced OCR**: Tesseract with preprocessing (denoising, deskewing, grayscale)
* 💬 **Real-time Chat UI**: Responsive, modern web interface with history & typing indicators
* 🔐 **Secure Authentication**: Firebase OAuth (Google, GitHub, Email)
* 🗑️ **Data Privacy**: User-isolated vector stores + auto file cleanup
* 📊 **Confidence Scoring**: Every response comes with relevance & source attribution

---

## 🏗️ Architecture

**Layered, cloud-native design for scalability & security**

* **Presentation Layer** → Chat interface, upload UI, auth pages
* **API Layer (Flask)** → Auth, chat, upload & health endpoints
* **Business Logic Layer** → OCR, embeddings, hybrid retrieval, AI generation
* **Data Layer** → FAISS vector DB + Firebase Firestore + caching

🔄 **Data Flow**:
Upload → OCR & preprocessing → Chunking → Embeddings → FAISS → Query → Hybrid retrieval → AI response (Gemini / local LLM) → Answer + citations

---

## 🛠️ Tech Stack

**Frontend**: HTML5/CSS3, JavaScript (ES6+), Firebase SDK, responsive UI
**Backend**: Python 3.9, Flask 2.x, Gunicorn/uWSGI, Docker
**Core AI/ML**: Tesseract OCR, SentenceTransformers (MiniLM), FAISS, OpenCV
**LLM Layer**: Google Gemini API (Vision), Hugging Face Transformers, PyTorch, Ollama
**Infra**: Firebase Auth + Firestore, DiskCache, GPU acceleration (CUDA)

---

## ⚙️ Installation

```bash
# Clone repo
git clone https://github.com/adarshv0524/lumina-rag.git
cd lumina-rag

# Create env & install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables (`.env`)

```ini
# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_API_KEY=your-api-key

# Gemini API
GEMINI_API_KEY=your-gemini-api-key

# Flask
FLASK_ENV=production
UPLOAD_FOLDER=data/uploads
VECTOR_STORE_PATH=data/vectors
MAX_CONTENT_LENGTH=16777216
```

### Run

```bash
flask run
```

---

## 📖 Example Usage

```text
Q: "What are the main findings in this research paper?"
A: Summarized results with page citations.

Q: "Show me the financial performance metrics from the quarterly report."
A: Extracted tables & key metrics with references.
```

---


## 🤝 Contributing

1. Fork & clone the repo
2. Create a feature branch
3. Implement & test your changes
4. Submit a PR 🚀

---

## 📜 License

MIT License


---
### **Adarsh Verma**

# Lumina RAG - Minimal Multimodal RAG System

A streamlined Retrieval-Augmented Generation system for chatting with your documents.

## Features

- 📄 **Document Processing**: PDF, PowerPoint, and image support
- 🔍 **OCR Integration**: Extract text using Tesseract
- 🧠 **Smart Embeddings**: Sentence transformers for semantic search
- 💾 **Vector Storage**: FAISS for fast similarity search
- 🌐 **Flexible Generation**: Support for both cloud and local models
- 🎨 **Modern UI**: Clean web interface for document upload and chat



cwd


lumina-rag/
├── 📁 app/
│   ├── __init__.py
│   ├── main.py                    # Main Flask application
│   └── 📁 api/
│       ├── __init__.py
│       ├── v1/
│       │   ├── __init__.py
│       │   ├── documents.py       # Document upload endpoints
│       │   ├── queries.py         # Query processing endpoints
│       │   ├── analytics.py       # Analytics endpoints
│       │   └── health.py          # Health check endpoints
│       └── middleware/
│           ├── __init__.py
│           ├── auth.py            # Authentication middleware
│           ├── rate_limiter.py    # Rate limiting
│           └── cors.py            # CORS handling
│
├── 📁 modules/                    # Your existing core modules
│   ├── __init__.py
│   ├── document_processor.py     # ✅ NEED THIS
│   ├── text_extractor.py         # ✅ NEED THIS  
│   ├── embedder.py               # ✅ NEED THIS
│   ├── vector_store.py           # ✅ NEED THIS
│   ├── retriever.py              # ✅ NEED THIS
│   ├── generator.py              # ✅ NEED THIS
│   ├── monitoring.py             # ✅ NEED THIS
│   ├── cache_manager.py          # ✅ NEED THIS
│   └── ocr_optimizer.py          # ✅ NEED THIS
│
├── 📁 infrastructure/             # Phase 3 NEW
│   ├── 📁 redis/
│   │   ├── __init__.py
│   │   ├── redis_client.py       # Redis connection management
│   │   ├── session_store.py      # Redis-backed sessions
│   │   └── cache_layer.py        # Distributed caching
│   ├── 📁 monitoring/
│   │   ├── __init__.py
│   │   ├── metrics_collector.py  # Real-time metrics
│   │   ├── dashboard.py          # Analytics dashboard
│   │   └── alerting.py           # Alert management
│   └── 📁 security/
│       ├── __init__.py
│       ├── oauth_handler.py      # OAuth2 implementation
│       ├── jwt_manager.py        # JWT token management
│       └── pii_detector.py       # PII detection & redaction
│
├── 📁 deployment/                 # Phase 3 NEW
│   ├── 📁 docker/
│   │   ├── Dockerfile            # Multi-stage Docker build
│   │   ├── docker-compose.yml    # Local development setup
│   │   └── .dockerignore         # Docker ignore file
│   ├── 📁 kubernetes/
│   │   ├── namespace.yaml        # K8s namespace
│   │   ├── deployment.yaml       # Application deployment
│   │   ├── service.yaml          # Service configuration
│   │   ├── configmap.yaml        # Configuration management
│   │   ├── secret.yaml           # Secrets management
│   │   ├── hpa.yaml              # Horizontal Pod Autoscaler
│   │   └── ingress.yaml          # Ingress configuration
│   └── 📁 terraform/
│       ├── main.tf               # Infrastructure as code
│       ├── variables.tf          # Variable definitions
│       └── outputs.tf            # Output definitions
│
├── 📁 frontend/                   # Phase 3 Enhanced
│   ├── 📁 static/
│   │   ├── 📁 css/
│   │   │   ├── style.css         # ✅ NEED THIS
│   │   │   └── dashboard.css     # NEW: Analytics dashboard
│   │   ├── 📁 js/
│   │   │   ├── main.js           # ✅ NEED THIS
│   │   │   ├── dashboard.js      # NEW: Real-time analytics
│   │   │   ├── auth.js           # NEW: Authentication
│   │   │   └── websockets.js     # NEW: Real-time updates
│   │   └── 📁 images/
│   └── 📁 templates/
│       ├── base.html             # Base template
│       ├── index.html            # ✅ NEED THIS
│       ├── upload.html           # ✅ NEED THIS
│       ├── dashboard.html        # NEW: Analytics dashboard
│       └── login.html            # NEW: Authentication
│
├── 📁 tests/                      # Phase 3 Enhanced
│   ├── __init__.py
│   ├── 📁 unit/
│   │   ├── test_embedder.py      # ✅ NEED EXISTING TESTS
│   │   ├── test_retriever.py
│   │   ├── test_generator.py
│   │   └── test_redis_cache.py   # NEW
│   ├── 📁 integration/
│   │   ├── test_api.py
│   │   ├── test_auth_flow.py     # NEW
│   │   └── test_dashboard.py     # NEW
│   ├── 📁 performance/
│   │   ├── test_load.py          # NEW: Load testing
│   │   ├── test_memory.py        # NEW: Memory testing
│   │   └── benchmarks.py         # NEW: Performance benchmarks
│   └── 📁 fixtures/
│       ├── sample_documents/     # Test documents
│       └── mock_data/            # Mock responses
│
├── 📁 scripts/                    # Phase 3 Enhanced
│   ├── setup_dev.py              # Development setup
│   ├── deploy.py                 # Deployment script
│   ├── benchmark.py              # Performance testing
│   ├── backup_vectors.py         # Vector database backup
│   └── health_check.py           # System health validation
│
├── 📁 config/                     # Phase 3 Enhanced
│   ├── __init__.py
│   ├── settings.py               # ✅ NEED YOUR CONFIG
│   ├── redis_config.py           # NEW: Redis configuration
│   ├── k8s_config.py             # NEW: Kubernetes settings
│   └── security_config.py        # NEW: Security settings
│
├── 📁 data/                       # Your existing data
│   ├── 📁 uploads/               # ✅ User uploaded documents
│   ├── 📁 vector_store/          # ✅ FAISS indexes per user
│   ├── 📁 app_cache/             # ✅ Application cache
│   ├── 📁 logs/                  # NEW: Structured logs
│   └── 📁 metrics/               # NEW: Metrics storage
│
├── 📁 docs/                       # Phase 3 NEW
│   ├── api/
│   │   ├── openapi.yaml          # API documentation
│   │   └── postman_collection.json
│   ├── deployment/
│   │   ├── kubernetes_guide.md   # K8s deployment guide
│   │   └── redis_setup.md        # Redis setup guide
│   └── development/
│       ├── contributing.md       # Development guidelines
│       └── testing.md            # Testing guidelines
│
├── 📁 .github/                    # Phase 3 NEW
│   └── 📁 workflows/
│       ├── ci.yml                # Continuous Integration
│       ├── cd.yml                # Continuous Deployment
│       └── performance.yml       # Performance testing
│
├── requirements.txt               # ✅ NEED THIS
├── requirements-dev.txt           # NEW: Development requirements
├── Dockerfile                     # NEW: Production container
├── docker-compose.yml             # NEW: Local development
├── .env.example                   # NEW: Environment template
├── .gitignore                     # Enhanced gitignore
├── Makefile                       # NEW: Build automation
├── pyproject.toml                 # NEW: Python project config
└── README.md                      # Enhanced documentation


# 📚 AIRC Chatbot - System Flow Architecture

## 🎯 Tổng quan hệ thống

Hệ thống AIRC Internal Chatbot là một giải pháp RAG (Retrieval-Augmented Generation) được xây dựng theo kiến trúc **Microservices**, gồm 3 services chính:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AIRC CHATBOT SYSTEM                               │
│                      https://ragairc.neovort.shop                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────┐  │
│   │   📱 UI     │     │   🔐 AUTH   │     │         🧠 CORE             │  │
│   │  (Next.js)  │────▶│  (FastAPI)  │     │        (FastAPI)            │  │
│   │  Port 3000  │     │  Port 8001  │     │        Port 8000            │  │
│   └─────────────┘     └─────────────┘     └─────────────────────────────┘  │
│         │                    │                         │                    │
│         │                    ▼                         ▼                    │
│         │            ┌─────────────┐     ┌─────────────────────────────┐   │
│         │            │  MongoDB    │     │     Infrastructure          │   │
│         │            │  (Auth DB)  │     │  ┌─────┐ ┌──────┐ ┌──────┐ │   │
│         │            └─────────────┘     │  │Mongo│ │Qdrant│ │Redis │ │   │
│         │                                │  │ DB  │ │ VDB  │ │Queue │ │   │
│         │                                │  └─────┘ └──────┘ └──────┘ │   │
│         │                                └─────────────────────────────┘   │
│         │                                              │                    │
│         │                                              ▼                    │
│         │                                     ┌─────────────────┐           │
│         │                                     │    👷 Worker    │           │
│         │                                     │  (Background)   │           │
│         └─────────────────────────────────────┴─────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Service 1: AUTH SERVICE (Port 8001)

### 📁 Cấu trúc thư mục

```
airc_internal_chatbot_auth/
├── 📄 Dockerfile                    # Build image
├── 📄 requirements.txt              # Python dependencies
├── 📄 .env.example                  # Environment template
│
├── 📂 app/
│   ├── 📄 __init__.py
│   ├── 📄 main.py                   # ⭐ FastAPI entry point
│   │
│   ├── 📂 api/                      # API Layer
│   │   ├── 📄 dependencies.py       # Dependency Injection (get_current_user)
│   │   └── 📂 v1/
│   │       ├── 📄 auth.py           # 🔑 /api/auth/* (login, register, me)
│   │       └── 📄 rbac.py           # 👥 /api/rbac/* (roles, permissions, users)
│   │
│   ├── 📂 core/                     # Core Configuration
│   │   ├── 📄 settings.py           # ⚙️ Pydantic Settings (env vars)
│   │   ├── 📄 database.py           # 🗄️ MongoDB connection
│   │   ├── 📄 rate_limiter.py       # 🚦 Rate limiting middleware
│   │   ├── 📄 security_middleware.py # 🛡️ Security headers, sanitization
│   │   └── 📄 validators.py         # ✅ Input validation
│   │
│   ├── 📂 models/                   # Pydantic Schemas
│   │   ├── 📄 user.py               # 👤 User schemas (UserCreate, UserInDB, Token)
│   │   ├── 📄 rbac.py               # 🔒 Role, Permission schemas
│   │   └── 📄 database.py           # 📊 Database models
│   │
│   ├── 📂 repositories/             # Data Access Layer
│   │   ├── 📄 base_repository.py    # 🏗️ Base CRUD operations
│   │   ├── 📄 user_repository.py    # 👤 User DB operations
│   │   └── 📄 rbac_repository.py    # 🔒 Role/Permission DB operations
│   │
│   └── 📂 services/                 # Business Logic Layer
│       ├── 📄 auth_service.py       # 🔐 Login, Register, Password hashing
│       ├── 📄 jwt_service.py        # 🎫 JWT token create/verify
│       └── 📄 rbac_service.py       # 👥 RBAC permission checking
│
└── 📂 k8s/                          # Kubernetes manifests
    ├── 📄 deployment.yaml
    ├── 📄 service.yaml
    └── 📄 configmap.yaml
```

### 🔄 Luồng xử lý Authentication

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AUTH FLOW - LOGIN                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1️⃣ User Input                                                             │
│     ┌──────────┐    POST /api/auth/login                                   │
│     │ Browser  │ ────────────────────────▶ ┌───────────────┐               │
│     │ (email,  │                           │ api/v1/auth.py│               │
│     │ password)│                           │   login()     │               │
│     └──────────┘                           └───────┬───────┘               │
│                                                    │                        │
│  2️⃣ Business Logic                                ▼                        │
│                                            ┌───────────────┐               │
│                                            │ AuthService   │               │
│                                            │   login()     │               │
│                                            └───────┬───────┘               │
│                                                    │                        │
│  3️⃣ Database Query                                ▼                        │
│                                            ┌───────────────┐               │
│                                            │UserRepository │               │
│                                            │get_by_email() │               │
│                                            └───────┬───────┘               │
│                                                    │                        │
│  4️⃣ Password Verify                               ▼                        │
│                                            ┌───────────────┐               │
│                                            │ pbkdf2_sha256│               │
│                                            │   verify()    │               │
│                                            └───────┬───────┘               │
│                                                    │                        │
│  5️⃣ Token Generation                              ▼                        │
│                                            ┌───────────────┐               │
│                                            │  JWTService   │               │
│                                            │create_token() │               │
│                                            └───────┬───────┘               │
│                                                    │                        │
│  6️⃣ Response                                      ▼                        │
│     ┌──────────┐    {access_token: "eyJ..."}                               │
│     │ Browser  │ ◀──────────────────────── Token Response                  │
│     │          │    (Lưu vào localStorage)                                 │
│     └──────────┘                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 🔄 Luồng xử lý RBAC (Permission Check)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RBAC FLOW - PERMISSION CHECK                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Request với JWT Token                                                      │
│     ┌──────────┐    Authorization: Bearer eyJ...                           │
│     │  Client  │ ─────────────────────────▶ ┌────────────────┐             │
│     │          │                            │ dependencies.py│             │
│     └──────────┘                            │get_current_user│             │
│                                             └───────┬────────┘             │
│                                                     │                       │
│                                                     ▼                       │
│                                             ┌────────────────┐             │
│                                             │  JWTService    │             │
│                                             │ decode_token() │             │
│                                             │ ➜ user_id      │             │
│                                             │ ➜ role         │             │
│                                             └───────┬────────┘             │
│                                                     │                       │
│                                                     ▼                       │
│                                             ┌────────────────┐             │
│                                             │  RBACService   │             │
│                                             │check_permission│             │
│                                             └───────┬────────┘             │
│                                                     │                       │
│           ┌─────────────────────────────────────────┼───────────────────┐  │
│           │                                         │                    │  │
│           ▼                                         ▼                    │  │
│   ┌───────────────┐                        ┌───────────────┐            │  │
│   │ Admin Role?   │───Yes──▶ ✅ GRANTED    │ Check in DB   │            │  │
│   │ (bypass all)  │                        │ role_permissions│           │  │
│   └───────────────┘                        └───────┬───────┘            │  │
│                                                    │                     │  │
│                                        Has permission? ──Yes──▶ ✅       │  │
│                                                    │                     │  │
│                                                   No                     │  │
│                                                    ▼                     │  │
│                                              ❌ 403 Forbidden            │  │
│                                                                          │  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Service 2: CORE SERVICE (Port 8000)

### 📁 Cấu trúc thư mục

```
airc_internal_chatbot_core/
├── 📄 Dockerfile                    # Build image
├── 📄 requirements.txt              # Python dependencies
├── 📄 worker.py                     # ⭐ Background Worker (RQ/ARQ)
├── 📄 .env.example                  # Environment template
│
├── 📂 app/
│   ├── 📄 __init__.py
│   ├── 📄 main.py                   # ⭐ FastAPI entry point
│   │
│   ├── 📂 api/                      # API Layer
│   │   ├── 📄 dependencies.py       # Auth verification từ Auth Service
│   │   └── 📂 v1/
│   │       ├── 📄 chat.py           # 💬 /api/v1/chat/* (ask question)
│   │       ├── 📄 chatbots.py       # 🤖 /api/v1/chatbots/* (CRUD chatbots)
│   │       ├── 📄 datasets.py       # 📚 /api/v1/datasets/* (CRUD datasets)
│   │       ├── 📄 files.py          # 📁 /api/v1/files/* (upload, view)
│   │       ├── 📄 sessions.py       # 📝 /api/v1/sessions/* (chat history)
│   │       └── 📄 stats.py          # 📊 /api/v1/stats/* (dashboard stats)
│   │
│   ├── 📂 core/                     # Core Configuration
│   │   ├── 📄 config.py             # ⚙️ Pydantic Settings
│   │   ├── 📄 database.py           # 🗄️ MongoDB connection
│   │   └── 📄 queues.py             # 📬 Redis queue setup
│   │
│   ├── 📂 models/                   # Pydantic Schemas
│   │   ├── 📄 auth.py               # 🔐 User context from JWT
│   │   ├── 📄 schemas.py            # 📊 Chat request/response schemas
│   │   ├── 📄 chatbot_schemas.py    # 🤖 Chatbot schemas
│   │   ├── 📄 dataset.py            # 📚 Dataset schemas
│   │   ├── 📄 database.py           # 🗄️ Database collection models
│   │   └── 📄 enums.py              # 📋 Status enums (FileStatus, etc.)
│   │
│   ├── 📂 repositories/             # Data Access Layer
│   │   ├── 📄 base_repository.py    # 🏗️ Base CRUD operations
│   │   ├── 📄 chatbot_repository.py # 🤖 Chatbot DB operations
│   │   ├── 📄 dataset_repository.py # 📚 Dataset DB operations
│   │   ├── 📄 dataset_file_repository.py # 📁 Dataset-File link
│   │   ├── 📄 file_repository.py    # 📁 File metadata DB
│   │   ├── 📄 chunk_repository.py   # 📝 Text chunks DB
│   │   └── 📄 session_repository.py # 💬 Chat session DB
│   │
│   ├── 📂 services/                 # Business Logic Layer
│   │   │
│   │   │ # === RAG Pipeline Services ===
│   │   ├── 📄 chat_service.py       # 💬 ⭐ Main RAG orchestration
│   │   ├── 📄 embedding_service.py  # 🔢 Text → Vector (sentence-transformers)
│   │   ├── 📄 vector_service.py     # 🎯 Qdrant operations
│   │   ├── 📄 rerank_service.py     # 🔄 Cross-encoder reranking
│   │   ├── 📄 llm_service.py        # 🤖 Gemini API
│   │   ├── 📄 prompt_service.py     # 📝 Prompt templates
│   │   ├── 📄 cache_service.py      # 💾 Semantic caching
│   │   │
│   │   │ # === Data Processing Services ===
│   │   ├── 📄 processing_service.py # 📄 File → Text → Chunks → Vectors
│   │   ├── 📄 chunking_service.py   # ✂️ Text splitting
│   │   ├── 📄 dataset_service.py    # 📚 Dataset business logic
│   │   └── 📄 chatbot_service.py    # 🤖 Chatbot business logic
│   │
│   ├── 📂 jobs/                     # Background Jobs
│   │   └── 📄 ingest.py             # 📥 File ingestion job
│   │
│   └── 📂 db/                       # Database utilities
│
├── 📂 uploads/                      # Local file storage
│
└── 📂 k8s/                          # Kubernetes manifests
    ├── 📄 deployment.yaml
    ├── 📄 service.yaml
    └── 📄 configmap.yaml
```

### 🔄 Luồng xử lý RAG Chat

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RAG CHAT FLOW                                        │
│              POST /api/v1/chat/ask                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1️⃣ User Question                                                          │
│     ┌──────────────┐                                                       │
│     │ "Quy định   │                                                        │
│     │  nghỉ phép  │                                                        │
│     │  là gì?"    │                                                        │
│     └──────┬───────┘                                                       │
│            │                                                                │
│            ▼                                                                │
│  2️⃣ SEMANTIC CACHE CHECK                                                   │
│     ┌────────────────────────┐                                             │
│     │   cache_service.py     │                                             │
│     │  ┌──────────────────┐  │                                             │
│     │  │ Similar question │──Yes──▶ Return cached answer ⚡                │
│     │  │ in Redis cache?  │  │                                             │
│     │  └────────┬─────────┘  │                                             │
│     │           │ No         │                                             │
│     └───────────┼────────────┘                                             │
│                 ▼                                                           │
│  3️⃣ EMBEDDING (Query → Vector)                                             │
│     ┌────────────────────────┐                                             │
│     │  embedding_service.py  │                                             │
│     │  ┌──────────────────┐  │                                             │
│     │  │ sentence-        │  │                                             │
│     │  │ transformers     │  │                                             │
│     │  │ (multilingual)   │  │                                             │
│     │  └────────┬─────────┘  │                                             │
│     │           │            │                                             │
│     │     [0.12, -0.45, ...] │  ← 768-dim vector                           │
│     └───────────┼────────────┘                                             │
│                 ▼                                                           │
│  4️⃣ VECTOR SEARCH (Find similar chunks)                                    │
│     ┌────────────────────────┐                                             │
│     │   vector_service.py    │                                             │
│     │  ┌──────────────────┐  │                                             │
│     │  │     Qdrant       │  │                                             │
│     │  │  Vector Search   │  │                                             │
│     │  │   (top_k=20)     │  │                                             │
│     │  └────────┬─────────┘  │                                             │
│     │           │            │                                             │
│     │   [chunk1, chunk2, ...]│  ← 20 relevant chunks                       │
│     └───────────┼────────────┘                                             │
│                 ▼                                                           │
│  5️⃣ RERANK (Sort by relevance)                                             │
│     ┌────────────────────────┐                                             │
│     │   rerank_service.py    │                                             │
│     │  ┌──────────────────┐  │                                             │
│     │  │  Cross-Encoder   │  │                                             │
│     │  │    Reranker      │  │                                             │
│     │  │   (top_k=5)      │  │                                             │
│     │  └────────┬─────────┘  │                                             │
│     │           │            │                                             │
│     │  [best_chunk1, ...]    │  ← Top 5 most relevant                      │
│     └───────────┼────────────┘                                             │
│                 ▼                                                           │
│  6️⃣ PROMPT BUILDING                                                        │
│     ┌────────────────────────┐                                             │
│     │   prompt_service.py    │                                             │
│     │  ┌──────────────────┐  │                                             │
│     │  │ System Prompt +  │  │                                             │
│     │  │ Context Chunks + │  │                                             │
│     │  │ User Question    │  │                                             │
│     │  └────────┬─────────┘  │                                             │
│     └───────────┼────────────┘                                             │
│                 ▼                                                           │
│  7️⃣ LLM GENERATION                                                         │
│     ┌────────────────────────┐                                             │
│     │    llm_service.py      │                                             │
│     │  ┌──────────────────┐  │                                             │
│     │  │  Google Gemini   │  │                                             │
│     │  │  2.5 Flash       │  │                                             │
│     │  └────────┬─────────┘  │                                             │
│     │           │            │                                             │
│     │  "Theo quy định..."    │  ← Generated answer                         │
│     └───────────┼────────────┘                                             │
│                 ▼                                                           │
│  8️⃣ CACHE & RESPOND                                                        │
│     ┌────────────────────────┐                                             │
│     │ - Save to cache        │                                             │
│     │ - Save to session      │                                             │
│     │ - Return response      │                                             │
│     └────────────────────────┘                                             │
│                 │                                                           │
│                 ▼                                                           │
│     ┌────────────────────────────────────────┐                             │
│     │ {                                      │                             │
│     │   "answer": "Theo quy định...",        │                             │
│     │   "sources": [...],                    │                             │
│     │   "debug_metrics": {                   │                             │
│     │     "embedding_time_ms": 45,           │                             │
│     │     "retrieval_time_ms": 12,           │                             │
│     │     "rerank_time_ms": 89,              │                             │
│     │     "llm_time_ms": 1200                │                             │
│     │   }                                    │                             │
│     │ }                                      │                             │
│     └────────────────────────────────────────┘                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 🔄 Luồng xử lý File Ingestion (Background)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FILE INGESTION FLOW                                     │
│                  (Background Processing)                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1️⃣ FILE UPLOAD                                                            │
│     ┌──────────────┐    POST /api/v1/files/upload                          │
│     │  PDF/DOCX    │ ─────────────────────────▶ ┌───────────────┐          │
│     │    File      │                            │  files.py     │          │
│     └──────────────┘                            │  upload()     │          │
│                                                 └───────┬───────┘          │
│                                                         │                   │
│  2️⃣ SAVE TO DISK                                        ▼                   │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  uploads/{dataset_id}/{filename}                           │         │
│     │  + Save metadata to MongoDB (files collection)             │         │
│     └────────────────────────────────────────────────────────────┘         │
│                                                         │                   │
│  3️⃣ QUEUE BACKGROUND JOB                                ▼                   │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  Redis Queue (ARQ)                                         │         │
│     │  enqueue("process_dataset_file", dataset_id, file_id)      │         │
│     └────────────────────────────────────────────────────────────┘         │
│                                                         │                   │
│                                                         │                   │
│  ══════════════════════ WORKER PROCESS ═══════════════════════════         │
│                                                         │                   │
│  4️⃣ WORKER PICKS UP JOB                                 ▼                   │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  worker.py + jobs/ingest.py                                │         │
│     │  ProcessingService.process_dataset_file()                  │         │
│     └────────────────────────────────────────────────────────────┘         │
│                                                         │                   │
│  5️⃣ TEXT EXTRACTION                                     ▼                   │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  processing_service.py                                     │         │
│     │  ┌─────────────────────────────────────────────────────┐   │         │
│     │  │  PDF → pypdf.PdfReader                              │   │         │
│     │  │  DOCX → python-docx                                 │   │         │
│     │  │  TXT → direct read                                  │   │         │
│     │  └─────────────────────────────────────────────────────┘   │         │
│     │            │                                               │         │
│     │    Raw text content                                        │         │
│     └────────────┼───────────────────────────────────────────────┘         │
│                  ▼                                                          │
│  6️⃣ TEXT CHUNKING                                                          │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  RecursiveCharacterTextSplitter (LangChain)                │         │
│     │  ┌─────────────────────────────────────────────────────┐   │         │
│     │  │  chunk_size = 1000                                  │   │         │
│     │  │  chunk_overlap = 200                                │   │         │
│     │  │  separators = ["\n\n", "\n", ". ", " "]             │   │         │
│     │  └─────────────────────────────────────────────────────┘   │         │
│     │            │                                               │         │
│     │    [chunk_1, chunk_2, ..., chunk_N]                        │         │
│     └────────────┼───────────────────────────────────────────────┘         │
│                  ▼                                                          │
│  7️⃣ EMBEDDING                                                              │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  embedding_service.py                                      │         │
│     │  ┌─────────────────────────────────────────────────────┐   │         │
│     │  │  sentence-transformers/paraphrase-multilingual-...  │   │         │
│     │  │  Batch process all chunks → 768-dim vectors         │   │         │
│     │  └─────────────────────────────────────────────────────┘   │         │
│     │            │                                               │         │
│     │    [[0.12, -0.45, ...], [...], ...]                        │         │
│     └────────────┼───────────────────────────────────────────────┘         │
│                  ▼                                                          │
│  8️⃣ SAVE TO DATABASES                                                      │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │                                                            │         │
│     │  ┌─────────────────────┐    ┌─────────────────────┐       │         │
│     │  │      MongoDB        │    │       Qdrant        │       │         │
│     │  │  ┌───────────────┐  │    │  ┌───────────────┐  │       │         │
│     │  │  │ chunks        │  │    │  │ collection:   │  │       │         │
│     │  │  │ collection    │  │    │  │ dataset_{id}  │  │       │         │
│     │  │  │ (text, meta)  │  │    │  │ (vectors)     │  │       │         │
│     │  │  └───────────────┘  │    │  └───────────────┘  │       │         │
│     │  └─────────────────────┘    └─────────────────────┘       │         │
│     │                                                            │         │
│     └────────────────────────────────────────────────────────────┘         │
│                  │                                                          │
│  9️⃣ UPDATE STATUS                                                          │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  dataset_files.status = "INDEXED" ✅                       │         │
│     └────────────────────────────────────────────────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📱 Service 3: UI SERVICE (Port 3000)

### 📁 Cấu trúc thư mục

```
airc_internal_chatbot_ui/
├── 📄 Dockerfile                    # Build image
├── 📄 package.json                  # NPM dependencies
├── 📄 next.config.ts                # Next.js configuration
├── 📄 tsconfig.json                 # TypeScript config
├── 📄 .env.example                  # Environment template
│
├── 📂 src/
│   ├── 📄 middleware.ts             # 🛡️ Auth route protection
│   │
│   ├── 📂 app/                      # Next.js App Router (Pages)
│   │   ├── 📄 layout.tsx            # 🏠 Root layout (providers)
│   │   ├── 📄 page.tsx              # 🏠 Home (redirect)
│   │   ├── 📄 globals.css           # 🎨 Global styles
│   │   │
│   │   ├── 📂 auth/                 # Auth Pages
│   │   │   ├── 📂 login/
│   │   │   │   └── 📄 page.tsx      # 🔑 Login page
│   │   │   └── 📂 register/
│   │   │       └── 📄 page.tsx      # 📝 Register page
│   │   │
│   │   ├── 📂 dashboard/
│   │   │   └── 📄 page.tsx          # 📊 Dashboard (stats)
│   │   │
│   │   └── 📂 admin/                # Admin Pages
│   │       ├── 📂 users/            # 👥 User management
│   │       ├── 📂 roles/            # 🔒 Role management
│   │       ├── 📂 permissions/      # 🔑 Permission management
│   │       └── 📂 chatbots/         # 🤖 Chatbot management
│   │
│   ├── 📂 components/               # React Components
│   │   ├── 📂 Auth/                 # Auth components
│   │   │   ├── 📄 LoginForm.tsx
│   │   │   └── 📄 RegisterForm.tsx
│   │   │
│   │   ├── 📂 Chat/                 # Chat components
│   │   │   ├── 📄 ChatSidebar.tsx   # 📋 Session list
│   │   │   ├── 📄 ChatMessages.tsx  # 💬 Message list
│   │   │   ├── 📄 ChatInput.tsx     # ⌨️ Message input
│   │   │   └── 📄 RAGDebugPanel.tsx # 🔍 Debug metrics
│   │   │
│   │   ├── 📂 Dataset/              # Dataset components
│   │   │   └── 📄 KnowledgeBaseTab.tsx # 📚 File management
│   │   │
│   │   ├── 📂 Admin/                # Admin components
│   │   │   ├── 📄 UserTable.tsx
│   │   │   ├── 📄 RoleTable.tsx
│   │   │   ├── 📄 PermissionTable.tsx
│   │   │   └── 📄 ChatbotTable.tsx
│   │   │
│   │   ├── 📂 Layout/               # Layout components
│   │   │   └── 📄 AdminLayout.tsx
│   │   │
│   │   └── 📂 Common/               # Shared components
│   │
│   ├── 📂 services/                 # API Clients
│   │   ├── 📄 authService.ts        # 🔐 Auth API calls
│   │   ├── 📄 chatService.ts        # 💬 Chat API calls
│   │   ├── 📄 chatbotService.ts     # 🤖 Chatbot API calls
│   │   ├── 📄 datasetService.ts     # 📚 Dataset API calls
│   │   ├── 📄 fileService.ts        # 📁 File API calls
│   │   ├── 📄 rbacService.ts        # 👥 RBAC API calls
│   │   ├── 📄 statsService.ts       # 📊 Stats API calls
│   │   └── 📄 storageService.ts     # 💾 localStorage helper
│   │
│   ├── 📂 stores/                   # Zustand State Management
│   │   ├── 📄 authStore.ts          # 🔐 Auth state (user, token)
│   │   ├── 📄 chatStore.ts          # 💬 Chat state (sessions, messages)
│   │   └── 📄 datasetStore.ts       # 📚 Dataset state
│   │
│   ├── 📂 infrastructure/           # Infrastructure Layer
│   │   ├── 📂 http/
│   │   │   ├── 📄 auth.client.ts    # 🔐 Axios client for Auth API
│   │   │   └── 📄 core.client.ts    # 🧠 Axios client for Core API
│   │   └── 📂 repositories/         # Frontend repositories
│   │
│   ├── 📂 core/                     # Core domain
│   │   └── 📂 entities/             # TypeScript interfaces
│   │
│   ├── 📂 types/                    # Global TypeScript types
│   │
│   ├── 📂 hooks/                    # Custom React hooks
│   │
│   └── 📂 utils/                    # Utility functions
│
├── 📂 public/                       # Static assets
│
└── 📂 k8s/                          # Kubernetes manifests
```

### 🔄 Luồng xử lý UI - Chat Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     UI CHAT FLOW                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1️⃣ USER TYPES MESSAGE                                                     │
│     ┌────────────────────┐                                                 │
│     │    ChatInput.tsx   │                                                 │
│     │  ┌──────────────┐  │                                                 │
│     │  │ "Quy định   │  │                                                 │
│     │  │  nghỉ phép?" │  │                                                 │
│     │  └──────┬───────┘  │                                                 │
│     └─────────┼──────────┘                                                 │
│               │                                                             │
│               ▼                                                             │
│  2️⃣ ZUSTAND STATE UPDATE                                                   │
│     ┌────────────────────┐                                                 │
│     │   chatStore.ts     │                                                 │
│     │  ┌──────────────┐  │                                                 │
│     │  │ addMessage() │  │  ← Optimistic update (show immediately)        │
│     │  │ setLoading() │  │                                                 │
│     │  └──────┬───────┘  │                                                 │
│     └─────────┼──────────┘                                                 │
│               │                                                             │
│               ▼                                                             │
│  3️⃣ API CALL                                                               │
│     ┌────────────────────┐                                                 │
│     │  chatService.ts    │                                                 │
│     │  ┌──────────────┐  │                                                 │
│     │  │ askQuestion()│  │                                                 │
│     │  └──────┬───────┘  │                                                 │
│     └─────────┼──────────┘                                                 │
│               │                                                             │
│               ▼                                                             │
│  4️⃣ HTTP REQUEST                                                           │
│     ┌────────────────────┐                                                 │
│     │  core.client.ts    │                                                 │
│     │  ┌──────────────┐  │                                                 │
│     │  │ POST         │  │                                                 │
│     │  │ /api/v1/chat │  │  → Authorization: Bearer {token}               │
│     │  │ /ask         │  │                                                 │
│     │  └──────┬───────┘  │                                                 │
│     └─────────┼──────────┘                                                 │
│               │                                                             │
│               │  ═══════════════════════════════════════════════           │
│               │              CORE SERVICE PROCESSING                        │
│               │  ═══════════════════════════════════════════════           │
│               │                                                             │
│               ▼                                                             │
│  5️⃣ RESPONSE                                                               │
│     ┌────────────────────┐                                                 │
│     │  {                 │                                                 │
│     │    answer: "...",  │                                                 │
│     │    sources: [...], │                                                 │
│     │    debug: {...}    │                                                 │
│     │  }                 │                                                 │
│     └─────────┬──────────┘                                                 │
│               │                                                             │
│               ▼                                                             │
│  6️⃣ UPDATE STATE & UI                                                      │
│     ┌────────────────────┐                                                 │
│     │   chatStore.ts     │                                                 │
│     │  ┌──────────────┐  │                                                 │
│     │  │ addMessage() │  │  ← Add assistant response                       │
│     │  │ setLoading() │  │                                                 │
│     │  └──────┬───────┘  │                                                 │
│     └─────────┼──────────┘                                                 │
│               │                                                             │
│               ▼                                                             │
│  7️⃣ RENDER                                                                 │
│     ┌────────────────────┐                                                 │
│     │ ChatMessages.tsx   │                                                 │
│     │  ┌──────────────┐  │                                                 │
│     │  │ 👤 User:     │  │                                                 │
│     │  │ "Quy định?" │  │                                                 │
│     │  │              │  │                                                 │
│     │  │ 🤖 Bot:      │  │                                                 │
│     │  │ "Theo quy..." │  │                                                 │
│     │  └──────────────┘  │                                                 │
│     └────────────────────┘                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Schema

### MongoDB Collections

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MONGODB COLLECTIONS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📦 AUTH DATABASE (airc_auth_db)                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  👤 users                        🔒 roles                          │   │
│  │  ┌───────────────────┐          ┌───────────────────┐             │   │
│  │  │ _id: ObjectId     │          │ _id: ObjectId     │             │   │
│  │  │ email: string     │          │ code: string      │             │   │
│  │  │ hashed_password   │          │ name: string      │             │   │
│  │  │ full_name: string │          │ description       │             │   │
│  │  │ role: string ─────┼─────────▶│ permissions: []   │             │   │
│  │  │ role_ids: []      │          │ is_active: bool   │             │   │
│  │  │ is_active: bool   │          └───────────────────┘             │   │
│  │  │ created_at: Date  │                                            │   │
│  │  └───────────────────┘          🔑 permissions                    │   │
│  │                                 ┌───────────────────┐             │   │
│  │                                 │ _id: ObjectId     │             │   │
│  │                                 │ code: string      │             │   │
│  │                                 │ name: string      │             │   │
│  │                                 │ category: string  │             │   │
│  │                                 │ is_active: bool   │             │   │
│  │                                 └───────────────────┘             │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  📦 CORE DATABASE (airc_chatbot)                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  🤖 chatbots                    📚 datasets                        │   │
│  │  ┌───────────────────┐          ┌───────────────────┐             │   │
│  │  │ _id: ObjectId     │          │ _id: ObjectId     │             │   │
│  │  │ name: string      │          │ name: string      │             │   │
│  │  │ description       │          │ description       │             │   │
│  │  │ dataset_ids: [] ──┼─────────▶│ owner_id: string  │             │   │
│  │  │ allowed_roles: [] │          │ file_count: int   │             │   │
│  │  │ owner_id: string  │          │ total_chunks: int │             │   │
│  │  │ is_active: bool   │          │ created_at: Date  │             │   │
│  │  └───────────────────┘          └─────────┬─────────┘             │   │
│  │                                           │                        │   │
│  │  📁 files                       📄 dataset_files                  │   │
│  │  ┌───────────────────┐          ┌───────────────────┐             │   │
│  │  │ _id: ObjectId     │◀─────────│ file_id: ObjectId │             │   │
│  │  │ filename: string  │          │ dataset_id ───────┼────┘        │   │
│  │  │ path: string      │          │ status: enum      │             │   │
│  │  │ mimetype: string  │          │ chunk_count: int  │             │   │
│  │  │ size: int         │          │ created_at: Date  │             │   │
│  │  └───────────────────┘          └───────────────────┘             │   │
│  │                                                                     │   │
│  │  📝 chunks                      💬 chat_sessions                  │   │
│  │  ┌───────────────────┐          ┌───────────────────┐             │   │
│  │  │ _id: ObjectId     │          │ _id: ObjectId     │             │   │
│  │  │ dataset_id        │          │ name: string      │             │   │
│  │  │ file_id           │          │ user_id: string   │             │   │
│  │  │ text: string      │          │ messages: [       │             │   │
│  │  │ chunk_index: int  │          │   {role, content} │             │   │
│  │  │ metadata: {}      │          │ ]                 │             │   │
│  │  └───────────────────┘          │ created_at: Date  │             │   │
│  │                                 └───────────────────┘             │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Qdrant Vector Collections

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      QDRANT VECTOR DB                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Collection: dataset_{dataset_id}                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  Point 1                        Point 2                             │   │
│  │  ┌───────────────────┐          ┌───────────────────┐              │   │
│  │  │ id: chunk_id      │          │ id: chunk_id      │              │   │
│  │  │ vector: [768-dim] │          │ vector: [768-dim] │              │   │
│  │  │ payload: {        │          │ payload: {        │              │   │
│  │  │   chunk_id,       │          │   chunk_id,       │              │   │
│  │  │   dataset_id,     │          │   dataset_id,     │              │   │
│  │  │   file_id,        │          │   file_id,        │              │   │
│  │  │   text_preview    │          │   text_preview    │              │   │
│  │  │ }                 │          │ }                 │              │   │
│  │  └───────────────────┘          └───────────────────┘              │   │
│  │                                                                     │   │
│  │  Vector Search: Cosine Similarity                                   │   │
│  │  Index: HNSW (Hierarchical Navigable Small World)                  │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Environment Variables Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ENVIRONMENT VARIABLES                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🔐 AUTH SERVICE (.env)                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  MONGODB_URL=mongodb://localhost:27017                              │   │
│  │  MONGODB_DB_NAME=airc_auth_db                                       │   │
│  │  JWT_SECRET_KEY=your-secret-key        ◀─── Must match Core!       │   │
│  │  JWT_ALGORITHM=HS256                                                │   │
│  │  JWT_EXPIRE_MINUTES=1440                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  🧠 CORE SERVICE (.env)                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  MONGODB_URL=mongodb://localhost:27017                              │   │
│  │  MONGODB_DB_NAME=airc_chatbot                                       │   │
│  │  REDIS_URL=redis://localhost:6379/0                                 │   │
│  │  QDRANT_URL=http://localhost:6333                                   │   │
│  │  AUTH_SERVICE_URL=http://localhost:8001                             │   │
│  │  JWT_SECRET_KEY=your-secret-key        ◀─── Must match Auth!       │   │
│  │  GEMINI_API_KEY=your-api-key                                        │   │
│  │  GEMINI_MODEL=models/gemini-2.5-flash                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  📱 UI SERVICE (build args / .env.local)                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  NEXT_PUBLIC_AUTH_API=http://localhost:8001/api/auth                │   │
│  │  NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1                   │   │
│  │  NEXT_PUBLIC_APP_URL=http://localhost:3000                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Deployment Architecture (GKE)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GKE KUBERNETES CLUSTER                                   │
│                    Cluster: rag-gke | Region: asia-southeast1-c             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Internet                                                                   │
│     │                                                                       │
│     ▼                                                                       │
│  ┌─────────────────┐                                                       │
│  │  Cloudflare     │                                                       │
│  │  Tunnel         │                                                       │
│  │  (ragairc.      │                                                       │
│  │   neovort.shop) │                                                       │
│  └────────┬────────┘                                                       │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Namespace: airc-chatbot                                            │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │                         INGRESS                               │  │   │
│  │  │  /           → ui-service:3000                               │  │   │
│  │  │  /api/auth/* → auth-service:8001                             │  │   │
│  │  │  /api/v1/*   → core-service:8000                             │  │   │
│  │  │  /api/rbac/* → auth-service:8001                             │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │           │              │              │                           │   │
│  │           ▼              ▼              ▼                           │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │  │ UI Service  │ │Auth Service │ │Core Service │ │   Worker    │   │   │
│  │  │ (1 replica) │ │ (1 replica) │ │ (1 replica) │ │ (1 replica) │   │   │
│  │  │  Next.js    │ │  FastAPI    │ │  FastAPI    │ │  ARQ/RQ     │   │   │
│  │  │  :3000      │ │  :8001      │ │  :8000      │ │             │   │   │
│  │  └─────────────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘   │   │
│  │                         │              │              │             │   │
│  │                         └──────────────┼──────────────┘             │   │
│  │                                        │                            │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │                    STATEFULSETS                               │  │   │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │  │   │
│  │  │  │  MongoDB    │ │   Redis     │ │   Qdrant    │             │  │   │
│  │  │  │  (1 pod)    │ │  (1 pod)    │ │  (1 pod)    │             │  │   │
│  │  │  │  :27017     │ │  :6379      │ │  :6333      │             │  │   │
│  │  │  │  [PVC:10Gi] │ │  [PVC:1Gi]  │ │  [PVC:10Gi] │             │  │   │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘             │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                                                     │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │  SECRETS & CONFIGMAPS                                        │  │   │
│  │  │  - shared-secrets (JWT_SECRET, GEMINI_API_KEY)              │  │   │
│  │  │  - registry-credentials (Docker registry)                    │  │   │
│  │  │  - *-configmap (Service configs)                             │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Quick Reference - File Locations

| Chức năng       | Auth Service           | Core Service           | UI Service                     |
| --------------- | ---------------------- | ---------------------- | ------------------------------ |
| **Entry Point** | `app/main.py`          | `app/main.py`          | `src/app/layout.tsx`           |
| **Config**      | `app/core/settings.py` | `app/core/config.py`   | `next.config.ts`               |
| **Database**    | `app/core/database.py` | `app/core/database.py` | -                              |
| **API Routes**  | `app/api/v1/*.py`      | `app/api/v1/*.py`      | `src/app/**/page.tsx`          |
| **Services**    | `app/services/*.py`    | `app/services/*.py`    | `src/services/*.ts`            |
| **Models**      | `app/models/*.py`      | `app/models/*.py`      | `src/types/*.ts`               |
| **State**       | -                      | -                      | `src/stores/*.ts`              |
| **HTTP Client** | -                      | -                      | `src/infrastructure/http/*.ts` |

---

**📝 Document Version:** 1.0  
**📅 Last Updated:** February 2026  
**👥 Author:** AIRC Team

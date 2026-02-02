# 🔄 AIRC Chatbot - Sơ đồ Luồng Hệ thống (Mermaid)

> 📌 **Hướng dẫn xem:** File này chứa các sơ đồ Mermaid. Để xem đẹp nhất, hãy mở bằng:
>
> - VS Code với extension "Markdown Preview Mermaid Support"
> - GitHub/GitLab (tự động render)
> - Mermaid Live Editor: https://mermaid.live

---

## 📑 Mục lục

1. [Kiến trúc Tổng thể](#1-kiến-trúc-tổng-thể)
2. [Luồng Đăng nhập (Login)](#2-luồng-đăng-nhập-login)
3. [Luồng Xác thực Token (Core Service)](#3-luồng-xác-thực-token-core-service)
4. [Luồng Chat RAG](#4-luồng-chat-rag)
5. [Luồng Upload File](#5-luồng-upload-file)
6. [Luồng Xử lý File (Background Worker)](#6-luồng-xử-lý-file-background-worker)
7. [Luồng Tạo Chatbot](#7-luồng-tạo-chatbot)
8. [Quan hệ Database](#8-quan-hệ-database)
9. [Kiến trúc Triển khai (GKE)](#9-kiến-trúc-triển-khai-gke)

---

## 1. Kiến trúc Tổng thể

### 📝 Giải thích:

Hệ thống có 3 service chính chạy độc lập:

- **UI Service (Next.js - Port 3000)**: Giao diện web, dùng 2 Axios clients riêng biệt
- **Auth Service (FastAPI - Port 8001)**: Xử lý đăng nhập, JWT, RBAC
- **Core Service (FastAPI - Port 8000)**: Xử lý RAG, chat, datasets, files
- **Worker (RQ)**: Xử lý background jobs (file ingestion)

**Quan trọng**: Core Service KHÔNG có database riêng cho users - khi cần xác thực, nó gọi Auth Service qua HTTP.

```mermaid
flowchart TB
    subgraph BROWSER["🌐 Browser"]
        USER["👤 Người dùng"]
    end

    subgraph UI["📱 UI Service - Next.js (Port 3000)"]
        direction TB
        PAGES["Pages<br/>(App Router)"]
        COMPONENTS["Components<br/>(React)"]
        STORES["Stores<br/>(Zustand)"]

        subgraph CLIENTS["HTTP Clients (Axios)"]
            AUTH_CLIENT["authClient<br/>→ /api/auth"]
            CORE_CLIENT["coreClient<br/>→ /api/v1"]
        end
    end

    subgraph AUTH["🔐 Auth Service - FastAPI (Port 8001)"]
        direction TB
        AUTH_ROUTES["Routes:<br/>/api/auth/login<br/>/api/auth/register<br/>/api/auth/me<br/>/api/auth/verify"]
        RBAC_ROUTES["Routes:<br/>/api/rbac/roles<br/>/api/rbac/permissions<br/>/api/rbac/users"]
        AUTH_SERVICES["Services:<br/>AuthService<br/>JWTService<br/>RBACService"]
        AUTH_MIDDLEWARE["Middleware:<br/>RateLimit<br/>SecurityHeaders<br/>InputSanitize"]
    end

    subgraph CORE["🧠 Core Service - FastAPI (Port 8000)"]
        direction TB
        CORE_ROUTES["Routes:<br/>/api/v1/chat/ask<br/>/api/v1/chatbots<br/>/api/v1/datasets<br/>/api/v1/files<br/>/api/v1/sessions<br/>/api/v1/stats"]
        CORE_SERVICES["Services:<br/>ChatService<br/>DatasetService<br/>ProcessingService<br/>ChatbotService"]

        subgraph AI_SERVICES["AI Services"]
            EMBED["EmbeddingService<br/>(sentence-transformers)"]
            RERANK["RerankService<br/>(cross-encoder)"]
            LLM["LLMService<br/>(Google Gemini)"]
        end
    end

    subgraph WORKER["👷 Background Worker (RQ)"]
        RQ_WORKER["worker.py"]
        INGEST_JOB["jobs/ingest.py"]
    end

    subgraph INFRA["🗄️ Infrastructure"]
        MONGO_AUTH[("MongoDB<br/>airc_auth_db<br/>- users<br/>- roles<br/>- permissions")]
        MONGO_CORE[("MongoDB<br/>airc_chatbot<br/>- datasets<br/>- files<br/>- chunks<br/>- chatbots<br/>- sessions")]
        REDIS[("Redis<br/>- Job Queue<br/>- Semantic Cache")]
        QDRANT[("Qdrant<br/>Vector DB")]
        DISK["💿 Local Disk<br/>uploads/"]
    end

    USER --> PAGES
    PAGES --> COMPONENTS
    COMPONENTS --> STORES
    STORES --> CLIENTS

    AUTH_CLIENT -->|"POST /login<br/>POST /register<br/>GET /me"| AUTH_ROUTES
    CORE_CLIENT -->|"POST /chat/ask<br/>GET /chatbots<br/>POST /files/upload"| CORE_ROUTES

    AUTH_ROUTES --> AUTH_SERVICES
    AUTH_SERVICES --> MONGO_AUTH
    RBAC_ROUTES --> AUTH_SERVICES

    CORE_ROUTES -->|"verify token"| AUTH_ROUTES
    CORE_ROUTES --> CORE_SERVICES
    CORE_SERVICES --> AI_SERVICES
    CORE_SERVICES --> MONGO_CORE
    CORE_SERVICES --> REDIS
    CORE_SERVICES --> QDRANT
    CORE_SERVICES --> DISK

    CORE_SERVICES -->|"enqueue job"| REDIS
    REDIS -->|"dequeue"| RQ_WORKER
    RQ_WORKER --> INGEST_JOB
    INGEST_JOB --> MONGO_CORE
    INGEST_JOB --> QDRANT
    INGEST_JOB --> DISK

    style AUTH fill:#ffccbc
    style CORE fill:#c8e6c9
    style WORKER fill:#d1c4e9
```

---

## 2. Luồng Đăng nhập (Login)

### 📝 Giải thích:

1. User nhập email/password trên LoginForm
2. UI gọi `authClient.post('/login')` → Auth Service `/api/auth/login`
3. Auth Service kiểm tra email trong MongoDB `users` collection
4. Nếu đúng, tạo JWT token chứa `{user_id, email, role}`
5. UI lưu token vào localStorage và Zustand store
6. Từ đó, mọi request đều gửi token trong header `Authorization: Bearer xxx`

```mermaid
sequenceDiagram
    autonumber
    participant U as 👤 User
    participant UI as 📱 LoginForm.tsx
    participant Store as 🗃️ authStore.ts
    participant Client as 📡 authClient.ts
    participant Auth as 🔐 Auth Service
    participant JWT as 🎫 JWTService
    participant DB as 🗄️ MongoDB (airc_auth_db)

    Note over U,DB: 🔵 BƯỚC 1: User điền form đăng nhập

    U->>UI: Nhập email, password
    UI->>UI: Client-side validation
    UI->>Store: login(email, password)

    Note over U,DB: 🔵 BƯỚC 2: Zustand store gọi authService

    Store->>Store: setLoading(true)
    Store->>Client: POST /login {email, password}

    Note over U,DB: 🔵 BƯỚC 3: HTTP Request đến Auth Service

    Client->>+Auth: POST /api/auth/login<br/>Body: {email, password}

    Auth->>Auth: InputValidator.validate_email()
    Auth->>Auth: RateLimiter.is_blocked()

    Auth->>+DB: users.find_one({email: email})
    DB-->>-Auth: user document hoặc null

    alt Email không tồn tại
        Auth-->>Client: ❌ 401 "Email không tồn tại"
        Client-->>Store: throw Error
        Store->>Store: setError(message)
        Store-->>UI: error state
        UI-->>U: Hiển thị thông báo lỗi
    else Email tồn tại
        Note over U,DB: 🔵 BƯỚC 4: Verify password với pbkdf2_sha256

        Auth->>Auth: pbkdf2_sha256.verify(password, hashed)

        alt Password sai
            Auth-->>Client: ❌ 401 "Password không đúng"
            Client-->>Store: throw Error
            Store-->>UI: Hiển thị lỗi
        else Password đúng
            Note over U,DB: 🔵 BƯỚC 5: Tạo JWT Token

            Auth->>+JWT: create_access_token({<br/>  user_id,<br/>  email,<br/>  role<br/>})
            JWT-->>-Auth: "eyJhbGciOiJIUzI1NiIs..."

            Auth-->>-Client: ✅ 200 {access_token: "eyJ..."}

            Note over U,DB: 🔵 BƯỚC 6: Lưu token và cập nhật state

            Client-->>Store: {access_token}
            Store->>Store: localStorage.setItem("token", token)
            Store->>Store: setToken(token)
            Store->>Store: setAuthenticated(true)
            Store->>Store: chatStore.resetStore()

            Note over U,DB: 🔵 BƯỚC 7: Fetch user info (background)

            Store->>Client: GET /me (với Bearer token)
            Client->>Auth: GET /api/auth/me
            Auth->>Auth: decode JWT → user_id
            Auth->>DB: users.find_one({_id: user_id})
            DB-->>Auth: user document
            Auth-->>Client: {id, email, full_name, role, permissions}
            Client-->>Store: user data
            Store->>Store: setUser(user)

            Store-->>UI: isAuthenticated = true
            UI-->>U: ✅ Redirect to /dashboard
        end
    end
```

---

## 3. Luồng Xác thực Token (Core Service)

### 📝 Giải thích:

Khi UI gọi Core Service API (chat, datasets, files...), Core Service KHÔNG tự verify JWT. Thay vào đó:

1. Core Service extract token từ header `Authorization: Bearer xxx`
2. Gọi Auth Service endpoint `POST /api/auth/verify` với token
3. Auth Service decode + validate token, trả về user info
4. Core Service dùng user info để check permission và xử lý request

**Tại sao làm vậy?** Vì Core Service không có access đến `JWT_SECRET_KEY` giống Auth Service (trong thực tế có thể share secret, nhưng design hiện tại dùng service-to-service call).

```mermaid
sequenceDiagram
    autonumber
    participant UI as 📱 UI (coreClient)
    participant Core as 🧠 Core Service
    participant Dep as 🔍 dependencies.py
    participant Auth as 🔐 Auth Service
    participant Logic as ⚙️ Business Logic

    Note over UI,Logic: 🔵 Mọi request đến Core Service đều qua luồng này

    UI->>+Core: GET /api/v1/chatbots<br/>Header: Authorization: Bearer eyJ...

    Core->>+Dep: get_current_user(authorization)

    Note over UI,Logic: 🔵 Extract token từ header

    Dep->>Dep: token = authorization.split(" ")[1]

    Note over UI,Logic: 🔵 Gọi Auth Service verify endpoint

    Dep->>+Auth: POST /api/auth/verify<br/>Body: {"token": "eyJ..."}

    Auth->>Auth: JWTService.decode_token(token)

    alt Token invalid hoặc hết hạn
        Auth-->>Dep: ❌ 401 "Token invalid"
        Dep-->>Core: HTTPException 401
        Core-->>UI: ❌ 401 Unauthorized
    else Token hợp lệ
        Auth-->>-Dep: ✅ 200 {<br/>  id: "user123",<br/>  email: "a@b.com",<br/>  role: "teacher",<br/>  is_active: true<br/>}

        Note over UI,Logic: 🔵 Map response thành User model

        Dep->>Dep: User(<br/>  user_id=id,<br/>  email=email,<br/>  role=UserRole(role)<br/>)

        Dep-->>-Core: User object

        Note over UI,Logic: 🔵 Permission check (nếu cần)

        Core->>Core: require_permission(Permission.XXX)

        alt Admin role
            Core->>Core: ✅ Bypass (admin có mọi quyền)
        else Không phải admin
            Core->>Core: Check role có permission?
        end

        Core->>+Logic: Xử lý business logic
        Logic-->>-Core: Result
        Core-->>-UI: ✅ Response data
    end
```

---

## 4. Luồng Chat RAG

### 📝 Giải thích chi tiết từng bước:

1. **User gửi câu hỏi**: UI gọi `POST /api/v1/chat/ask`
2. **Token verification**: Core gọi Auth Service verify token
3. **RBAC Check**: Nếu có `chatbot_id`, kiểm tra user có quyền dùng chatbot không (dựa trên `allowed_roles`)
4. **Context Locking**: Dataset IDs được lock theo chatbot config, user không thể inject datasets khác
5. **Semantic Cache**: Kiểm tra câu hỏi tương tự đã trả lời chưa (Redis)
6. **Embedding**: Dùng `sentence-transformers` convert question → vector 768 chiều
7. **Vector Search**: Tìm top-k chunks tương tự trong Qdrant
8. **Rerank**: Dùng `cross-encoder` sắp xếp lại theo độ liên quan thực sự
9. **LLM Generation**: Xây prompt với context + history, gọi Gemini API
10. **Cache + Save**: Lưu vào cache và session history

```mermaid
sequenceDiagram
    autonumber
    participant UI as 📱 UI
    participant Core as 🧠 Core Service
    participant Auth as 🔐 Auth Service
    participant Chat as 💬 ChatService
    participant Cache as 💾 Redis Cache
    participant Embed as 🔢 EmbeddingService
    participant Vector as 🎯 Qdrant
    participant Rerank as 🔄 RerankService
    participant Chunk as 📄 ChunkRepository
    participant LLM as 🤖 Gemini
    participant Session as 📝 SessionRepository

    Note over UI,Session: 🟢 BƯỚC 1-2: Request + Token Verification

    UI->>+Core: POST /api/v1/chat/ask<br/>{question, chatbot_id, session_id}<br/>Header: Bearer token

    Core->>+Auth: POST /api/auth/verify {"token": "eyJ..."}
    Auth-->>-Core: {user_id, role}

    Core->>+Chat: ask_question(question, chatbot_id, user_context)

    Note over UI,Session: 🟢 BƯỚC 3: RBAC Check (Chatbot Access)

    Chat->>Chat: Fetch chatbot từ DB

    alt User không phải admin
        Chat->>Chat: Kiểm tra role in allowed_roles?
        alt Không có quyền
            Chat-->>Core: ❌ PermissionError
            Core-->>UI: ❌ 403 "Không có quyền truy cập Chatbot"
        end
    end

    Note over UI,Session: 🟢 BƯỚC 4: Context Locking (Security)

    Chat->>Chat: dataset_ids = chatbot.dataset_ids<br/>(Override client params!)

    Note over UI,Session: 🟢 BƯỚC 5: Session History

    Chat->>+Session: add_message(session_id, "user", question)
    Session-->>-Chat: OK
    Chat->>+Session: get_messages(session_id)
    Session-->>-Chat: history[]

    Note over UI,Session: 🟢 BƯỚC 6: Semantic Cache Check

    Chat->>+Embed: embed(question)
    Embed-->>-Chat: q_vector [768]

    Chat->>+Cache: get(question, q_vector, chatbot_id)

    alt Cache HIT ⚡
        Cache-->>Chat: cached_answer
        Chat->>Session: add_message(session_id, "assistant", cached)
        Chat-->>Core: {answer: cached, cache_hit: true}
        Core-->>UI: ✅ Response (fast!)
    else Cache MISS
        Cache-->>-Chat: null

        Note over UI,Session: 🟢 BƯỚC 7: Vector Search

        Chat->>+Vector: search(q_vector, dataset_ids, top_k=20)
        Note right of Vector: Cosine Similarity<br/>trên collection dataset_{id}
        Vector-->>-Chat: [chunk_id1, chunk_id2, ...] + scores

        Note over UI,Session: 🟢 BƯỚC 8: Rerank

        Chat->>+Rerank: rerank(question, chunks, top_k=5)
        Note right of Rerank: Cross-Encoder<br/>ms-marco-MiniLM
        Rerank-->>-Chat: [best_chunks] sorted by relevance

        Note over UI,Session: 🟢 BƯỚC 9: Get Full Chunk Text

        Chat->>+Chunk: get_by_ids(chunk_ids)
        Chunk-->>-Chat: [{text, metadata}, ...]

        Note over UI,Session: 🟢 BƯỚC 10: Build Prompt + LLM

        Chat->>Chat: build_prompt(<br/>  system_prompt,<br/>  context_chunks,<br/>  history,<br/>  question<br/>)

        Chat->>+LLM: generate(prompt)
        Note right of LLM: Google Gemini<br/>models/gemini-2.5-flash
        LLM-->>-Chat: generated_answer

        Note over UI,Session: 🟢 BƯỚC 11: Save & Cache

        Chat->>Cache: set(question, q_vector, answer, chatbot_id)
        Chat->>Session: add_message(session_id, "assistant", answer)

        Chat-->>-Core: {<br/>  answer,<br/>  sources,<br/>  debug_metrics<br/>}
        Core-->>-UI: ✅ ChatResponse
    end
```

---

## 5. Luồng Upload File

### 📝 Giải thích:

Upload file là **synchronous** - file được lưu ngay và trả về response. Processing là **asynchronous** - chạy background.

1. UI gọi `POST /api/v1/files/upload` với file binary (multipart/form-data)
2. Core verify token qua Auth Service
3. Check permission: chỉ admin/teacher được upload
4. Lưu file vào disk: `uploads/{user_id}/{filename}`
5. Tạo record trong MongoDB `files` collection
6. Trả về file info ngay lập tức (status: READY)

```mermaid
sequenceDiagram
    autonumber
    participant UI as 📱 UI
    participant Core as 🧠 Core Service
    participant Auth as 🔐 Auth Service
    participant FileAPI as 📁 files.py
    participant Disk as 💿 Local Disk
    participant DB as 🗄️ MongoDB

    Note over UI,DB: 🟠 File Upload (Synchronous)

    UI->>UI: User chọn file (PDF/DOCX/TXT)
    UI->>UI: Validate file < 200MB

    UI->>+Core: POST /api/v1/files/upload<br/>Content-Type: multipart/form-data<br/>Header: Bearer token

    Core->>+Auth: POST /api/auth/verify {"token": "eyJ..."}
    Auth-->>-Core: {user_id, role}

    Core->>+FileAPI: upload_file(file, current_user)

    Note over UI,DB: 🟠 Permission Check

    FileAPI->>FileAPI: role in ["admin", "teacher"]?

    alt Không có quyền
        FileAPI-->>Core: ❌ 403 "Only admin/teacher can upload"
        Core-->>UI: ❌ 403 Forbidden
    else Có quyền
        Note over UI,DB: 🟠 Lưu file vào disk

        FileAPI->>FileAPI: file_content = await file.read()
        FileAPI->>FileAPI: file_path = uploads/{user_id}/{filename}
        FileAPI->>+Disk: aiofiles.open(file_path, 'wb')
        Disk-->>-FileAPI: OK

        Note over UI,DB: 🟠 Tạo record trong MongoDB

        FileAPI->>+DB: files.insert_one({<br/>  name,<br/>  size,<br/>  mime_type,<br/>  path,<br/>  status: "Ready"<br/>})
        DB-->>-FileAPI: file_id

        FileAPI-->>-Core: FileUploadResponse
        Core-->>-UI: ✅ 201 {id, name, size, status: "Ready"}
    end
```

---

## 6. Luồng Xử lý File (Background Worker)

### 📝 Giải thích:

Sau khi upload, user thêm file vào dataset. Lúc này mới trigger background processing:

1. UI gọi `POST /api/v1/datasets/{id}/files` để thêm file vào dataset
2. Core tạo record `dataset_files` với status `PENDING`
3. Core đẩy job vào Redis queue `ingest`
4. Worker (RQ) pick job và chạy `process_dataset_file_job()`
5. Processing: Extract text → Chunking → Embedding → Index vào Qdrant
6. Update status thành `DONE`

**Lưu ý quan trọng**: Worker sử dụng **RQ (Redis Queue)**, KHÔNG phải ARQ.

```mermaid
sequenceDiagram
    autonumber
    participant UI as 📱 UI
    participant Core as 🧠 Core Service
    participant DB as 🗄️ MongoDB
    participant Redis as 📬 Redis Queue
    participant Worker as 👷 RQ Worker
    participant Job as 📥 ingest.py
    participant Process as ⚙️ ProcessingService
    participant Disk as 💿 Local Disk
    participant Embed as 🔢 EmbeddingService
    participant Qdrant as 🎯 Qdrant

    Note over UI,Qdrant: 🟠 PHASE 1: Thêm file vào dataset

    UI->>+Core: POST /api/v1/datasets/{dataset_id}/files<br/>{file_ids: ["file123"]}

    Core->>+DB: dataset_files.insert_one({<br/>  dataset_id,<br/>  file_id,<br/>  status: "Pending"<br/>})
    DB-->>-Core: dataset_file_id

    Note over UI,Qdrant: 🟠 PHASE 2: Queue background job

    Core->>+Redis: queue.enqueue(<br/>  "process_dataset_file_job",<br/>  dataset_id,<br/>  dataset_file_id<br/>)
    Redis-->>-Core: job_id

    Core-->>-UI: ✅ 200 {status: "Pending"}

    Note over UI,Qdrant: 🟠 PHASE 3: Worker xử lý (Background)

    Redis->>+Worker: Dequeue job
    Worker->>+Job: process_dataset_file_job()

    Job->>Job: Connect MongoDB
    Job->>+Process: process_dataset_file(dataset_id, df_id)

    Note over UI,Qdrant: 🔵 Step 1: Update status CHUNKING

    Process->>DB: dataset_files.update(status: "Chunking")

    Note over UI,Qdrant: 🔵 Step 2: Lấy thông tin file

    Process->>DB: dataset_files.find_one()
    Process->>DB: files.find_one({_id: file_id})

    Note over UI,Qdrant: 🔵 Step 3: Đọc file từ disk

    Process->>+Disk: aiofiles.open(path, 'rb')
    Disk-->>-Process: binary content

    Note over UI,Qdrant: 🔵 Step 4: Extract text

    Process->>Process: PDF → pypdf.PdfReader<br/>DOCX → python-docx<br/>TXT → decode utf-8

    Note over UI,Qdrant: 🔵 Step 5: Chunking

    Process->>Process: RecursiveCharacterTextSplitter<br/>chunk_size=1024<br/>chunk_overlap=100
    Process->>Process: chunks_text = [chunk1, chunk2, ...]

    Note over UI,Qdrant: 🔵 Step 6: Update status EMBEDDING

    Process->>DB: dataset_files.update(status: "Embedding")

    Note over UI,Qdrant: 🔵 Step 7: Generate embeddings

    Process->>+Embed: embed_texts(chunks_text)
    Note right of Embed: sentence-transformers<br/>paraphrase-multilingual
    Embed-->>-Process: embeddings [[768], [768], ...]

    Note over UI,Qdrant: 🔵 Step 8: Lưu chunks vào MongoDB

    Process->>+DB: chunks.insert_many([<br/>  {dataset_id, file_id, text, vector},<br/>  ...<br/>])
    DB-->>-Process: chunk_ids

    Note over UI,Qdrant: 🔵 Step 9: Index vectors vào Qdrant

    Process->>+Qdrant: upsert(collection=dataset_{id},<br/>  points=[{id, vector, payload}])
    Qdrant-->>-Process: OK

    Note over UI,Qdrant: 🔵 Step 10: Update status DONE

    Process->>DB: dataset_files.update(<br/>  status: "Done",<br/>  chunk_count: N,<br/>  is_enabled: true<br/>)

    Process-->>-Job: OK
    Job-->>-Worker: Job completed
    Worker-->>-Redis: ACK
```

---

## 7. Luồng Tạo Chatbot

### 📝 Giải thích:

Chatbot là cầu nối giữa users và datasets:

- **Admin** tạo chatbot, chọn datasets để dùng
- **allowed_roles**: Roles nào được dùng chatbot (admin luôn có quyền)
- Khi chat, chatbot config quyết định datasets nào được search

```mermaid
sequenceDiagram
    autonumber
    participant UI as 📱 UI
    participant Core as 🧠 Core Service
    participant Auth as 🔐 Auth Service
    participant Chatbot as 🤖 ChatbotService
    participant DB as 🗄️ MongoDB

    Note over UI,DB: 🟢 Tạo Chatbot (Admin only)

    UI->>+Core: POST /api/v1/chatbots<br/>{name, description, dataset_ids, allowed_roles}<br/>Header: Bearer token

    Core->>+Auth: POST /api/auth/verify {"token": "eyJ..."}
    Auth-->>-Core: {user_id, role: "admin"}

    Core->>+Chatbot: create_chatbot(creator_id, creator_role, data)

    Note over UI,DB: 🟢 Permission Check

    Chatbot->>Chatbot: creator_role == "admin"?

    alt Không phải admin
        Chatbot-->>Core: ❌ PermissionError
        Core-->>UI: ❌ 403 "Admin only"
    else Là admin
        Note over UI,DB: 🟢 Validate datasets exist

        Chatbot->>+DB: datasets.find({_id: {$in: dataset_ids}})
        DB-->>-Chatbot: datasets[]

        Chatbot->>Chatbot: Kiểm tra số lượng datasets khớp

        Note over UI,DB: 🟢 Create chatbot record

        Chatbot->>+DB: chatbots.insert_one({<br/>  name,<br/>  description,<br/>  owner_id,<br/>  dataset_ids,<br/>  allowed_roles: ["student", "teacher"],<br/>  is_active: true,<br/>  config: {top_k, reranker, ...}<br/>})
        DB-->>-Chatbot: chatbot_id

        Chatbot-->>-Core: chatbot document
        Core-->>-UI: ✅ 201 ChatbotResponse
    end
```

### Luồng Student truy cập Chatbot

```mermaid
flowchart TD
    A[👤 Student mở trang Chat] --> B[UI gọi GET /api/v1/chatbots]
    B --> C[Core verify token]
    C --> D{Token hợp lệ?}
    D -->|No| E[❌ 401 Unauthorized]
    D -->|Yes| F[ChatbotService.get_available_chatbots]

    F --> G{User role?}
    G -->|admin| H[Trả về TẤT CẢ chatbots]
    G -->|teacher/student| I[Filter: role in allowed_roles]

    I --> J[Chatbot có allowed_roles<br/>chứa student?]
    J -->|Yes| K[✅ Hiển thị chatbot]
    J -->|No| L[❌ Không hiển thị]

    H --> M[UI render danh sách chatbots]
    K --> M

    M --> N[Student chọn chatbot]
    N --> O[UI gọi POST /chat/ask<br/>với chatbot_id]
    O --> P[ChatService kiểm tra RBAC]

    P --> Q{student in allowed_roles?}
    Q -->|Yes| R[✅ Xử lý RAG + trả lời]
    Q -->|No| S[❌ 403 Không có quyền]

    style E fill:#ffcdd2
    style L fill:#ffcdd2
    style S fill:#ffcdd2
    style K fill:#c8e6c9
    style R fill:#c8e6c9
```

---

## 8. Quan hệ Database

### 📝 Giải thích:

**2 databases MongoDB riêng biệt:**

- `airc_auth_db`: Quản lý bởi Auth Service (users, roles, permissions)
- `airc_chatbot`: Quản lý bởi Core Service (datasets, files, chunks, chatbots, sessions)

**Qdrant**: Mỗi dataset có 1 collection riêng `dataset_{id}` chứa vectors của chunks

```mermaid
erDiagram
    %% ========== AUTH DATABASE (airc_auth_db) ==========

    USERS ||--o{ USER_ROLES : "has"
    ROLES ||--o{ USER_ROLES : "assigned to"
    ROLES ||--o{ ROLE_PERMISSIONS : "has"
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : "granted to"

    USERS {
        ObjectId _id PK
        string email UK
        string hashed_password
        string full_name
        string role "default role code"
        array role_ids "ObjectId[]"
        boolean is_active
        datetime created_at
    }

    ROLES {
        ObjectId _id PK
        string code UK "admin|teacher|student"
        string name
        string description
        boolean is_active
        datetime created_at
    }

    PERMISSIONS {
        ObjectId _id PK
        string code UK "resource:action:scope"
        string name
        string resource
        string action
        string scope
        boolean is_system
        datetime created_at
    }

    USER_ROLES {
        ObjectId user_id FK
        ObjectId role_id FK
    }

    ROLE_PERMISSIONS {
        ObjectId role_id FK
        ObjectId permission_id FK
    }

    %% ========== CORE DATABASE (airc_chatbot) ==========

    DATASETS ||--o{ DATASET_FILES : "contains"
    FILES ||--o{ DATASET_FILES : "linked via"
    DATASET_FILES ||--o{ CHUNKS : "produces"
    CHATBOTS }o--o{ DATASETS : "uses"
    CHAT_SESSIONS ||--o{ MESSAGES : "contains"

    DATASETS {
        ObjectId _id PK
        string name
        string owner_id "user_id from Auth"
        string visibility "private|shared"
        int file_count
        int total_chunks
        datetime created_at
    }

    FILES {
        ObjectId _id PK
        string name
        string path "uploads/user_id/file.pdf"
        string mime_type
        int size
        string status "Ready|Error"
        datetime uploaded_at
    }

    DATASET_FILES {
        ObjectId _id PK
        ObjectId dataset_id FK
        ObjectId file_id FK
        string status "Pending|Chunking|Embedding|Done|Error"
        int chunk_count
        boolean is_enabled
        datetime created_at
    }

    CHUNKS {
        ObjectId _id PK
        ObjectId dataset_id FK
        ObjectId dataset_file_id FK
        ObjectId file_id FK
        string text
        array vector "float[768]"
        int chunk_index
        datetime created_at
    }

    CHATBOTS {
        ObjectId _id PK
        string name
        string description
        string owner_id "user_id from Auth"
        array dataset_ids "ObjectId[]"
        array allowed_roles "string[]"
        boolean is_active
        object config "top_k, reranker, etc"
        datetime created_at
    }

    CHAT_SESSIONS {
        ObjectId _id PK
        string name
        string user_id "from Auth"
        string chatbot_id FK
        datetime created_at
        datetime updated_at
    }

    MESSAGES {
        ObjectId _id PK
        ObjectId session_id FK
        string role "user|assistant"
        string content
        datetime created_at
    }
```

### Qdrant Collections

```mermaid
flowchart LR
    subgraph Qdrant["🎯 Qdrant Vector DB"]
        subgraph C1["Collection: dataset_abc123"]
            P1["Point 1<br/>id: chunk_id<br/>vector: [768 floats]<br/>payload: {dataset_id, file_id}"]
            P2["Point 2<br/>..."]
        end

        subgraph C2["Collection: dataset_xyz789"]
            P3["Point 1<br/>..."]
            P4["Point 2<br/>..."]
        end
    end

    Search["Vector Search"] -->|"Cosine Similarity<br/>HNSW Index"| C1
    Search -->|"Multi-collection<br/>search"| C2
```

---

## 9. Kiến trúc Triển khai (GKE)

### 📝 Giải thích:

- **Cloudflare Tunnel**: Kết nối domain public với cluster (không cần expose IP)
- **Ingress**: Nginx ingress định tuyến theo path
- **Deployments**: Stateless apps (có thể scale)
- **StatefulSets**: Databases với Persistent Volume Claims

```mermaid
flowchart TB
    subgraph Internet["🌐 Internet"]
        User["👤 Users"]
        Domain["ragairc.neovort.shop"]
    end

    subgraph CF["☁️ Cloudflare"]
        Tunnel["Cloudflare Tunnel<br/>(cloudflared pod)"]
    end

    subgraph GKE["☸️ GKE Cluster: rag-gke<br/>Region: asia-southeast1-c"]
        subgraph NS["Namespace: airc-chatbot"]

            subgraph Ingress["🚪 Nginx Ingress Controller"]
                ING["nginx-ingress<br/>CORS enabled"]
            end

            subgraph Apps["🚀 Deployments (Stateless)"]
                UI["📱 ui-service<br/>replicas: 1<br/>port: 3000<br/>image: airc-ui"]
                AUTH["🔐 auth-service<br/>replicas: 1<br/>port: 8001<br/>image: airc-auth"]
                CORE["🧠 core-service<br/>replicas: 1<br/>port: 8000<br/>image: airc-core"]
                WORKER["👷 worker<br/>replicas: 1<br/>image: airc-core<br/>cmd: python worker.py"]
            end

            subgraph Data["💾 StatefulSets (Stateful)"]
                MONGO[("🗄️ MongoDB<br/>port: 27017<br/>PVC: 10Gi")]
                REDIS[("⚡ Redis<br/>port: 6379<br/>PVC: 1Gi")]
                QDRANT[("🎯 Qdrant<br/>port: 6333<br/>PVC: 10Gi")]
            end

            subgraph Config["⚙️ ConfigMaps & Secrets"]
                SECRET["🔒 shared-secrets<br/>- JWT_SECRET_KEY<br/>- GEMINI_API_KEY"]
                CM_AUTH["📝 auth-configmap"]
                CM_CORE["📝 core-configmap"]
                REG["🔑 registry-credentials"]
            end
        end
    end

    User --> Domain
    Domain --> Tunnel
    Tunnel --> ING

    ING -->|"/"| UI
    ING -->|"/api/auth/*<br/>/api/rbac/*"| AUTH
    ING -->|"/api/v1/*"| CORE

    AUTH --> MONGO
    CORE -->|"POST /api/auth/verify"| AUTH
    CORE --> MONGO
    CORE --> REDIS
    CORE --> QDRANT

    WORKER --> REDIS
    WORKER --> MONGO
    WORKER --> QDRANT

    AUTH -.->|"env"| SECRET
    AUTH -.->|"env"| CM_AUTH
    CORE -.->|"env"| SECRET
    CORE -.->|"env"| CM_CORE

    UI -.->|"pull image"| REG
    AUTH -.->|"pull image"| REG
    CORE -.->|"pull image"| REG

    style UI fill:#fff9c4
    style AUTH fill:#ffccbc
    style CORE fill:#c8e6c9
    style WORKER fill:#d1c4e9
```

### Ingress Routing Rules

```mermaid
flowchart LR
    subgraph Request["📨 Incoming Request"]
        R1["GET /"]
        R2["POST /api/auth/login"]
        R3["GET /api/auth/me"]
        R4["POST /api/auth/verify"]
        R5["GET /api/rbac/roles"]
        R6["POST /api/v1/chat/ask"]
        R7["GET /api/v1/chatbots"]
        R8["POST /api/v1/files/upload"]
    end

    subgraph Ingress["🚪 Ingress Rules"]
        RULE1["path: /"]
        RULE2["path: /api/auth"]
        RULE3["path: /api/rbac"]
        RULE4["path: /api/v1"]
    end

    subgraph Services["🎯 Backend Services"]
        UI["ui-service:3000"]
        AUTH["auth-service:8001"]
        CORE["core-service:8000"]
    end

    R1 --> RULE1 --> UI
    R2 --> RULE2 --> AUTH
    R3 --> RULE2 --> AUTH
    R4 --> RULE2 --> AUTH
    R5 --> RULE3 --> AUTH
    R6 --> RULE4 --> CORE
    R7 --> RULE4 --> CORE
    R8 --> RULE4 --> CORE
```

---

## 📊 Tổng hợp API Endpoints

### Auth Service (Port 8001)

| Method | Endpoint                | Mô tả                       | Auth     |
| ------ | ----------------------- | --------------------------- | -------- |
| POST   | `/api/auth/register`    | Đăng ký user mới            | ❌       |
| POST   | `/api/auth/login`       | Đăng nhập                   | ❌       |
| GET    | `/api/auth/me`          | Lấy thông tin user hiện tại | ✅       |
| POST   | `/api/auth/verify`      | Verify JWT token (internal) | ❌       |
| GET    | `/api/rbac/roles`       | Danh sách roles             | ✅ Admin |
| POST   | `/api/rbac/roles`       | Tạo role mới                | ✅ Admin |
| GET    | `/api/rbac/permissions` | Danh sách permissions       | ✅ Admin |
| GET    | `/api/rbac/users`       | Danh sách users             | ✅ Admin |

### Core Service (Port 8000)

| Method | Endpoint                      | Mô tả                   | Auth             |
| ------ | ----------------------------- | ----------------------- | ---------------- |
| POST   | `/api/v1/chat/ask`            | Gửi câu hỏi RAG         | ✅               |
| GET    | `/api/v1/chatbots`            | Danh sách chatbots      | ✅               |
| POST   | `/api/v1/chatbots`            | Tạo chatbot             | ✅ Admin         |
| GET    | `/api/v1/datasets`            | Danh sách datasets      | ✅               |
| POST   | `/api/v1/datasets`            | Tạo dataset             | ✅ Admin/Teacher |
| POST   | `/api/v1/datasets/{id}/files` | Thêm files vào dataset  | ✅               |
| POST   | `/api/v1/files/upload`        | Upload file             | ✅ Admin/Teacher |
| GET    | `/api/v1/files/{id}/view`     | Xem/Download file       | ✅               |
| GET    | `/api/v1/sessions`            | Danh sách chat sessions | ✅               |
| GET    | `/api/v1/stats/dashboard`     | Thống kê dashboard      | ✅               |

---

**📝 Document Version:** 2.0  
**📅 Last Updated:** February 2025  
**👥 Author:** AIRC Team

> 💡 **Tip:** Sử dụng [Mermaid Live Editor](https://mermaid.live) để chỉnh sửa và xem preview các diagram.

# AIRC Chatbot - System Flow Architecture

Tài liệu này cung cấp cái nhìn tổng quan về kiến trúc và luồng hoạt động của hệ thống AIRC Internal Chatbot. Đây là cẩm nang xây dựng hệ thống dành cho các thành viên mới, giúp các bạn nhanh chóng nắm bắt được cách các thành phần trong hệ thống RAG (Retrieval-Augmented Generation) kết nối và tương tác với nhau.

## Tổng quan hệ thống

Hệ thống AIRC Internal Chatbot tuân theo kiến trúc Microservices để đảm bảo tính phân tách trách nhiệm, dễ dàng bảo trì và mở rộng. 

Hệ thống bao gồm 3 service chính:
- **UI Service** (Frontend): Giao diện người dùng web xây dựng với Next.js.
- **Auth Service** (Backend Xác thực): Quản lý đăng nhập, cấp phát phân quyền (RBAC) với FastAPI.
- **Core Service** (Backend RAG): Xử lý toàn bộ logic nghiệp vụ chính (ngữ cảnh, Retrieval, LLM generation) với FastAPI.

Ngoài ra hệ thống còn đi kèm các thành phần hạ tầng (Infrastructure) như Database (MongoDB, Redis, Qdrant) và các worker xử lý tiến trình background.

```text
+-----------------------------------------------------------------------------+
|                           AIRC CHATBOT SYSTEM                               |
+-----------------------------------------------------------------------------+
|                                                                             |
|   +-------------+     +-------------+     +-----------------------------+   |
|   |     UI      |     |    AUTH     |     |            CORE             |   |
|   |  (Next.js)  |---->|  (FastAPI)  |     |          (FastAPI)          |   |
|   |  Port 3000  |     |  Port 8001  |     |          Port 8000          |   |
|   +-------------+     +-------------+     +-----------------------------+   |
|         |                    |                           |                  |
|         |                    v                           v                  |
|         |            +-------------+     +-----------------------------+    |
|         |            |   MongoDB   |     |       Infrastructure        |    |
|         |            |  (Auth DB)  |     |  +-----+ +------+ +------+  |    |
|         |            +-------------+     |  |Mongo| |Qdrant| |Redis |  |    |
|         |                                |  | DB  | | VDB  | |Queue |  |    |
|         |                                |  +-----+ +------+ +------+  |    |
|         |                                +-----------------------------+    |
|         |                                                |                  |
|         |                                                v                  |
|         |                                       +-----------------+         |
|         |                                       |     Worker      |         |
|         |                                       |  (Background)   |         |
|         +---------------------------------------+-----------------+         |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## 1. Service 1: AUTH SERVICE (Port 8001)

Auth Service đóng vai trò là cửa ngõ bảo mật của toàn bộ nền tảng. Chức năng chính của dịch vụ này bao gồm: cấp phát các JWT token khi người dùng đăng nhập, lưu trữ thông tin người dùng và duy trì ma trận phân quyền dựa trên Role (RBAC). Mọi yêu cầu truy cập từ UI đến các API cần bảo mật đều phải thông qua dịch vụ này.

### Cấu trúc thư mục

Dưới đây là sơ đồ cấu trúc mã nguồn của Auth Service. Các thư mục được tổ chức theo kiến trúc lớp (Layered Architecture):

```text
airc_internal_chatbot_auth/
|-- Dockerfile                    # File đóng gói môi trường chạy Docker
|-- requirements.txt              # Danh sách các thư viện Python cài đặt
|-- .env.example                  # Định dạng biến môi trường cấu hình
|
|-- app/
|   |-- __init__.py
|   |-- main.py                   # Entry point của FastAPI, nơi khởi tạo app
|   |
|   |-- api/                      # Lớp giao tiếp (API Layer), định nghĩa các endpoint
|   |   |-- dependencies.py       # Chứa các hàm Dependency Injection, ví dụ lấy user hiện tại
|   |   |-- v1/
|   |       |-- auth.py           # Endpoint xác thực (login, đăng ký, thông tin account)
|   |       |-- rbac.py           # Endpoint quản lý phân quyền (Role, Permission)
|   |
|   |-- core/                     # Lớp Cấu hình, định nghĩa hằng số hệ thống
|   |   |-- settings.py           # Thiết lập các biến môi trường
|   |   |-- database.py           # Quản lý kết nối tới MongoDB
|   |   |-- rate_limiter.py       # Middleware giới hạn số lượng request
|   |   |-- security_middleware.py# Middleware đảm bảo header an toàn, chống XSS
|   |   |-- validators.py         # Kiểm tra, xác thực đầu vào
|   |
|   |-- models/                   # Lớp Mapping Data, các Object mô tả dữ liệu
|   |   |-- user.py               # Thông tin và schema API User
|   |   |-- rbac.py               # Cấu trúc Role và Permissions
|   |   |-- database.py           # Ánh xạ Models vào database
|   |
|   |-- repositories/             # Lớp Trừu tượng hóa truy vấn Data base
|   |   |-- base_repository.py    # Chứa logic tái sử dụng như CRUD
|   |   |-- user_repository.py    # Thao tác liên quan User database
|   |   |-- rbac_repository.py    # Thao tác liên quan Quyền (Role/Permission)
|   |
|   |-- services/                 # Lớp Nghiệp vụ (Business logic) thực thi tác vụ
|       |-- auth_service.py       # Logic Đăng nhập, mã hóa cấp quyền
|       |-- jwt_service.py        # Ký tạo và giải mã JWT token
|       |-- rbac_service.py       # Thuật toán kiểm tra giới hạn phân quyền
|
|-- k8s/                          # Các tệp Deployment cho môi trường Kubernetes
    |-- deployment.yaml
    |-- service.yaml
    |-- configmap.yaml
```

### Luồng xử lý Authentication (Đăng nhập)

Khi người dùng cung cấp tài khoản, hệ thống sẽ kiểm tra bảo mật (hash password) và cấp cho họ một chuỗi chuỗi Token định danh. Token này giống như "căn cước" để đi qua các dịch vụ.

```text
+-----------------------------------------------------------------------------+
|                        AUTH FLOW - LOGIN                                    |
+-----------------------------------------------------------------------------+
|                                                                             |
|  1. User Input                                                              |
|     +----------+    POST /api/auth/login                                    |
|     | Browser  | ------------------------> +---------------+                |
|     | (email,  |                           | api/v1/auth.py|                |
|     | password)|                           |   login()     |                |
|     +----------+                           +-------+-------+                |
|                                                    |                        |
|  2. Business Logic                                 v                        |
|                                            +---------------+                |
|                                            | AuthService   |                |
|                                            |   login()     |                |
|                                            +-------+-------+                |
|                                                    |                        |
|  3. Database Query                                 v                        |
|                                            +---------------+                |
|                                            |UserRepository |                |
|                                            |get_by_email() |                |
|                                            +-------+-------+                |
|                                                    |                        |
|  4. Password Verify                                v                        |
|                                            +---------------+                |
|                                            | pbkdf2_sha256 |                |
|                                            |   verify()    |                |
|                                            +-------+-------+                |
|                                                    |                        |
|  5. Token Generation                               v                        |
|                                            +---------------+                |
|                                            |  JWTService   |                |
|                                            |create_token() |                |
|                                            +-------+-------+                |
|                                                    |                        |
|  6. Response                                       v                        |
|     +----------+    {access_token: "eyJ..."}                                |
|     | Browser  | <------------------------ Token Response                   |
|     |          |    (Lưu vào localStorage)                                  |
|     +----------+                                                            |
|                                                                             |
+-----------------------------------------------------------------------------+
```

### Luồng xử lý RBAC (Kiểm tra Phân quyền)

Khi dịch vụ nhận được API với yêu cầu truy cập thông tin kín, nó sử dụng chuỗi JWT để xác thực và check quyền dựa vào CSDL Role/Permission. Nếu Role có Permission hành động, request được cho phép thực hiện. 

```text
+-----------------------------------------------------------------------------+
|                        RBAC FLOW - PERMISSION CHECK                         |
+-----------------------------------------------------------------------------+
|                                                                             |
|  Request với JWT Token                                                      |
|     +----------+    Authorization: Bearer eyJ...                            |
|     |  Client  | -------------------------> +----------------+              |
|     +----------+                            | dependencies.py|              |
|                                             |get_current_user|              |
|                                             +-------+--------+              |
|                                                     |                       |
|                                                     v                       |
|                                             +----------------+              |
|                                             |  JWTService    |              |
|                                             | decode_token() |              |
|                                             | -> user_id     |              |
|                                             | -> role        |              |
|                                             +-------+--------+              |
|                                                     |                       |
|                                                     v                       |
|                                             +----------------+              |
|                                             |  RBACService   |              |
|                                             |check_permission|              |
|                                             +-------+--------+              |
|                                                     |                       |
|           +-----------------------------------------+-------------------+   |
|           |                                         |                   |   |
|           v                                         v                   |   |
|   +---------------+                        +---------------+            |   |
|   | Admin Role?   |---Yes--> [GRANTED]     | Check in DB   |            |   |
|   | (bypass all)  |                        |role_permission|            |   |
|   +---------------+                        +-------+-------+            |   |
|                                                    |                    |   |
|                                        Has permission? --Yes--> [OK]    |   |
|                                                    |                    |   |
|                                                   No                    |   |
|                                                    v                    |   |
|                                              [403 Forbidden]            |   |
|                                                                         |   |
+-----------------------------------------------------------------------------+
```

---

## 2. Service 2: CORE SERVICE (Port 8000)

Core Service đảm nhận cốt lõi của hoạt động Retrieval-Augmented Generation (RAG). Nó quản lý các tệp, trích xuất dữ liệu, chia văn bản thành các khối nhỏ (chunks), mã hóa nó vào thuật toán Vector tìm kiếm, cho đến cuối thu thập câu trả lời từ AI theo câu hỏi được đưa ra bởi User.

### Cấu trúc thư mục

```text
airc_internal_chatbot_core/
|-- Dockerfile                    # File đóng gói cho ứng dụng RAG Service
|-- requirements.txt              # Thư viện như Qdrant, sentence-transformer
|-- worker.py                     # Nơi thực thi tiến trình làm việc ẩn (Queue Worker)
|-- .env.example                  # Định dạng cấu hình môi trường
|
|-- app/
|   |-- __init__.py
|   |-- main.py                   # Root FastAPI cung cấp API cho Core Service
|   |
|   |-- api/                      # Giao diện kết nối REST
|   |   |-- dependencies.py       # Cầu kiểm tra Token gửi sang Auth API 
|   |   |-- v1/
|   |       |-- chat.py           # API Xử lý đoạn Chat (Gen response)
|   |       |-- chatbots.py       # Quản trị thông tin bot Agent
|   |       |-- datasets.py       # Tập hợp tài nguyên thông tin Data sets
|   |       |-- files.py          # Quản lý tải và upload lên server
|   |       |-- sessions.py       # Tiến trình trò chuyện (History)
|   |       |-- stats.py          # Truy xuất phục vụ cho biểu đồ Admin
|   |
|   |-- core/                     
|   |   |-- config.py             # Map cấu hình của Ứng dụng
|   |   |-- database.py           # Connection kết nối CSDL Core DB
|   |   |-- queues.py             # Triển khai Redis queue gửi/nhận WorkJobs
|   |
|   |-- models/                   # Lớp đối tượng lưu trữ Schema (Pydantic models)
|   |   |-- auth.py               # Map data User JWT Payload
|   |   |-- schemas.py            # Mô tả input-output JSON từ Client
|   |   |-- chatbot_schemas.py    # Schema thuộc về tác vụ chatbot
|   |   |-- dataset.py            # Thông tin data files
|   |   |-- database.py           # Model object lưu MongoDB
|   |   |-- enums.py              # Thư mục định dạng giá trị hằng (Constants)
|   |
|   |-- repositories/             # Interface lớp trung gian lưu DB
|   |   |-- base_repository.py    # Kế thừa CRUD chung 
|   |   |-- chatbot_repository.py # CRUD thông tin Chatbot Model
|   |   |-- dataset_repository.py # DB Collections liên quan tập Dataset
|   |   |-- dataset_file_repository.py # Link kết nối Data-File
|   |   |-- file_repository.py    # Metadata từng file
|   |   |-- chunk_repository.py   # DB các mảnh Text chunks được sinh
|   |   |-- session_repository.py # Nơi ghi vết lại session Chat Message
|   |
|   |-- services/                 # Cụm logic ứng dụng chính (Core Business)
|   |   |
|   |   | # === RAG Pipeline Services ===  (Các bước của chuỗi RAG)
|   |   |-- chat_service.py       # Hàm trọng tâm kết nối Retrieval/LLM/Prompt
|   |   |-- embedding_service.py  # Sử dụng model Text to Vector 
|   |   |-- vector_service.py     # Tra cứu trong Vector database (Qdrant)
|   |   |-- rerank_service.py     # Điểm hóa lại Cross-encoder
|   |   |-- llm_service.py        # Gọi External Proxy LLM như Gemini APIs
|   |   |-- prompt_service.py     # Template Context Prompt
|   |   |-- cache_service.py      # Bộ nhớ ngăn Chat dư thừa (Redis Semantic cache)
|   |   |
|   |   | # === Data Processing Services ===
|   |   |-- processing_service.py # Convert Raw-File sang vector chunks
|   |   |-- chunking_service.py   # Chẻ nhỏ số chữ
|   |   |-- dataset_service.py    # Quản lý tài nguyên tổng quan 
|   |   |-- chatbot_service.py    # Điều chính hành vi Assistant
|   |
|   |-- jobs/                     # Hoạt động ngầm ngoài thread (Worker Task)
|   |   |-- ingest.py             # Hàm index xử lý Background cho Document Data 
|   |
|   |-- db/                       # Các util bổ trợ DB init
|
|-- uploads/                      # Đường dẫn lưu rễ file gốc trên đĩa 
|
|-- k8s/                          # Deployment Kubernetes Config
    |-- deployment.yaml
    |-- service.yaml
    |-- configmap.yaml
```

### Luồng xử lý RAG Chat (Luồng Hỏi-Đáp)

Luồng hoạt động dưới đây mô tả chính xác quá trình từ lời chất vấn của người dùng đến lúc máy tạo thành văn bản phản hồi thông minh bằng RAG. Nó liên kết Vector, Document context và LLM theo từng công đoạn xử lý chắt lọc cẩn thận.

```text
+-----------------------------------------------------------------------------+
|                        RAG CHAT FLOW                                        |
|              POST /api/v1/chat/ask                                          |
+-----------------------------------------------------------------------------+
|                                                                             |
|  1. User Question                                                           |
|     +--------------+                                                        |
|     | "Quy định    |                                                        |
|     |  nghỉ phép   |                                                        |
|     |  là gì?"     |                                                        |
|     +------+-------+                                                        |
|            |                                                                |
|            v                                                                |
|  2. SEMANTIC CACHE CHECK                                                    |
|     +------------------------+                                              |
|     |   cache_service.py     |                                              |
|     |  +------------------+  |                                              |
|     |  | Similar question |---Yes--> Return cached answer (No LLM load)     |
|     |  | in Redis cache?  |  |                                              |
|     |  +--------+---------+  |                                              |
|     |           | No         |                                              |
|     +-----------+------------+                                              |
|                 v                                                           |
|  3. EMBEDDING (Query -> Vector)                                             |
|     +------------------------+                                              |
|     |  embedding_service.py  |                                              |
|     |  +------------------+  |                                              |
|     |  | sentence-        |  |                                              |
|     |  | transformers     |  |                                              |
|     |  | (multilingual)   |  |                                              |
|     |  +--------+---------+  |                                              |
|     |           |            |                                              |
|     |     [0.12, -0.45, ...] |  <- 768-dim vector (Tạo giá trị tọa độ text) |
|     +-----------+------------+                                              |
|                 v                                                           |
|  4. VECTOR SEARCH (Find similar chunks)                                     |
|     +------------------------+                                              |
|     |   vector_service.py    |                                              |
|     |  +------------------+  |                                              |
|     |  |     Qdrant       |  |                                              |
|     |  |  Vector Search   |  |                                              |
|     |  |   (top_k=20)     |  |                                              |
|     |  +--------+---------+  |                                              |
|     |           |            |                                              |
|     |   [chunk1, chunk2, ...]|  <- 20 relevant chunks (Trích 20 đoạn liên   |
|     +-----------+------------+      quan theo ngữ nghĩa tọa độ Vector)      |
|                 v                                                           |
|  5. RERANK (Sort by relevance)                                              |
|     +------------------------+                                              |
|     |   rerank_service.py    |                                              |
|     |  +------------------+  |                                              |
|     |  |  Cross-Encoder   |  |                                              |
|     |  |    Reranker      |  |                                              |
|     |  |   (top_k=5)      |  |                                              |
|     |  +--------+---------+  |                                              |
|     |           |            |                                              |
|     |  [best_chunk1, ...]    |  <- Top 5 most relevant (Lấy 5 đoạn tốt nhất)|
|     +-----------+------------+                                              |
|                 v                                                           |
|  6. PROMPT BUILDING                                                         |
|     +------------------------+                                              |
|     |   prompt_service.py    |                                              |
|     |  +------------------+  |                                              |
|     |  | System Prompt +  |  |                                              |
|     |  | Context Chunks + |  |                                              |
|     |  | User Question    |  |                                              |
|     |  +--------+---------+  |                                              |
|     +-----------+------------+                                              |
|                 v                                                           |
|  7. LLM GENERATION                                                          |
|     +------------------------+                                              |
|     |    llm_service.py      |                                              |
|     |  +------------------+  |                                              |
|     |  |  Google Gemini   |  |                                              |
|     |  |  2.5 Flash       |  |                                              |
|     |  +--------+---------+  |                                              |
|     |           |            |                                              |
|     |  "Theo quy định..."    |  <- Generated answer (Bot hồi đáp văn bản)   |
|     +-----------+------------+                                              |
|                 v                                                           |
|  8. CACHE & RESPOND                                                         |
|     +------------------------+                                              |
|     | - Save cache to Redis  |                                              |
|     | - Save history session |                                              |
|     | - Return JSON Res      |                                              |
|     +------------------------+                                              |
|                 |                                                           |
|                 v                                                           |
|     +----------------------------------------+                              |
|     | {                                      |                              |
|     |   "answer": "Theo quy định...",        |                              |
|     |   "sources": [...],                    |                              |
|     |   "debug_metrics": {                   |                              |
|     |     "embedding_time_ms": 45,           |                              |
|     |     "retrieval_time_ms": 12,           |                              |
|     |     "rerank_time_ms": 89,              |                              |
|     |     "llm_time_ms": 1200                |                              |
|     |   }                                    |                              |
|     | }                                      |                              |
|     +----------------------------------------+                              |
|                                                                             |
+-----------------------------------------------------------------------------+
```

### Luồng xử lý File Ingestion (Background)

File Ingestion là cơ chế phi đồng bộ (Asynchronous Worker). Khi tải liệu nặng nề (ví dụ PDF 100 trang) được tải lên, hệ thống tiếp nhận nhanh, thả xuống queue để Redis worker thu gom text, nhúng nó vào Vector ngầm. Giao diện sau đấy sẽ tự đồng bộ báo Indexed.

```text
+-----------------------------------------------------------------------------+
|                     FILE INGESTION FLOW                                     |
|                  (Background Processing)                                    |
+-----------------------------------------------------------------------------+
|                                                                             |
|  1. FILE UPLOAD                                                             |
|     +--------------+    POST /api/v1/files/upload                           |
|     |  PDF/DOCX    | -------------------------> +---------------+           |
|     |    File      |                            |  files.py     |           |
|     +--------------+                            |  upload()     |           |
|                                                 +-------+-------+           |
|                                                         |                   |
|  2. SAVE TO DISK                                        v                   |
|     +------------------------------------------------------------+          |
|     |  uploads/{dataset_id}/{filename}                           |          |
|     |  + Lưu Metadata record database (Status: Uploading)        |          |
|     +------------------------------------------------------------+          |
|                                                         |                   |
|  3. QUEUE BACKGROUND JOB                                v                   |
|     +------------------------------------------------------------+          |
|     |  Redis Queue (Background Pipeline)                         |          |
|     |  enqueue("process_dataset_file", file_id)                  |          |
|     +------------------------------------------------------------+          |
|                                                         |                   |
|                                                         |                   |
|  ====================== WORKER PROCESS ===========================          |
|                                                         |                   |
|  4. WORKER PICKS UP JOB                                 v                   |
|     +------------------------------------------------------------+          |
|     |  worker.py + jobs/ingest.py                                |          |
|     |  ProcessingService.process_dataset_file()                  |          |
|     +------------------------------------------------------------+          |
|                                                         |                   |
|  5. TEXT EXTRACTION                                     v                   |
|     +------------------------------------------------------------+          |
|     |  processing_service.py                                     |          |
|     |  +-----------------------------------------------------+   |          |
|     |  |  PDF -> pypdf.PdfReader (Trích OCR)                 |   |          |
|     |  |  DOCX -> python-docx    (Trích XML word)            |   |          |
|     |  |  TXT -> direct read                                 |   |          |
|     |  +-----------------------------------------------------+   |          |
|     |            |                                               |          |
|     |    Raw text content                                        |          |
|     +------------+-----------------------------------------------+          |
|                  v                                                          |
|  6. TEXT CHUNKING                                                           |
|     +------------------------------------------------------------+          |
|     |  RecursiveCharacterTextSplitter (LangChain)                |          |
|     |  +-----------------------------------------------------+   |          |
|     |  |  chunk_size = 1000                                  |   |          |
|     |  |  chunk_overlap = 200 (Giúp ko gãy ngữ cảnh nối câu) |   |          |
|     |  |  separators = ["\n\n", "\n", ". ", " "]             |   |          |
|     |  +-----------------------------------------------------+   |          |
|     |            |                                               |          |
|     |    [chunk_1, chunk_2, ..., chunk_N]                        |          |
|     +------------+-----------------------------------------------+          |
|                  v                                                          |
|  7. EMBEDDING                                                               |
|     +------------------------------------------------------------+          |
|     |  embedding_service.py                                      |          |
|     |  +-----------------------------------------------------+   |          |
|     |  |  Mô hình HuggingFace paraphrase-multilingual...     |   |          |
|     |  |  Dịch Array -> Tensor Vector (768 chiều không gian) |   |          |
|     |  +-----------------------------------------------------+   |          |
|     |            |                                               |          |
|     |    [[0.12, -0.45, ...], [...], ...]                        |          |
|     +------------+-----------------------------------------------+          |
|                  v                                                          |
|  8. SAVE TO DATABASES                                                       |
|     +------------------------------------------------------------+          |
|     |                                                            |          |
|     |  +---------------------+    +---------------------+        |          |
|     |  |      MongoDB        |    |       Qdrant        |        |          |
|     |  |  +---------------+  |    |  +---------------+  |        |          |
|     |  |  | chunks        |  |    |  | collection:   |  |        |          |
|     |  |  | collection    |  |    |  | dataset_{id}  |  |        |          |
|     |  |  | (text string) |  |    |  | (vector DB)   |  |        |          |
|     |  |  +---------------+  |    |  +---------------+  |        |          |
|     |  +---------------------+    +---------------------+        |          |
|     |                                                            |          |
|     +------------------------------------------------------------+          |
|                  |                                                          |
|  9. UPDATE STATUS                                                           |
|     +------------------------------------------------------------+          |
|     |  dataset_files.status = "INDEXED" [COMPLETE]               |          |
|     +------------------------------------------------------------+          |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## 3. Service 3: UI SERVICE (Port 3000)

Dịch vụ này được xây dựng trên Next.js và TailwindCSS. Nó giao tiếp với 2 service BackEnd thông qua Axios Clients. State App được điều khiển theo dạng Client Stores thay vì Local React Components nhờ dùng Zustand.

### Cấu trúc thư mục

```text
airc_internal_chatbot_ui/
|-- Dockerfile                    # File đóng gói môi trường Container Node.js
|-- package.json                  # Nơi lưu Version thư viện React+Next js
|-- next.config.ts                # Cấu hình biên dịch của Next js Framework
|-- tsconfig.json                 # Cấu hình Typescript typing
|-- .env.example                  # File tham khảo env 
|
|-- src/
|   |-- middleware.ts             # Server hook chặn truy cập Url trái phép 
|   |
|   |-- app/                      # Nơi định nghĩa các Trang / Tùy tuyến (App Router)
|   |   |-- layout.tsx            # Bố cục Header/Footer, Context Wrapper bọc web
|   |   |-- page.tsx              # URL Gốc Redirect vào Dashboard nếu đã Đăng Nhập
|   |   |-- globals.css           # Inject file cài CSS Base, Tailwind Rules
|   |   |
|   |   |-- auth/                 # Trang Dành Cho Visitor Account Flow
|   |   |   |-- login/page.tsx    # Giao diện Trang Đăng nhập hệ thống
|   |   |   |-- register/page.tsx # Giao diện Trang Đăng Ký người dùng
|   |   |
|   |   |-- dashboard/            # Bảng trung tâm thống kê, Biểu đồ report sử dụng
|   |   |   |-- page.tsx          
|   |   |
|   |   |-- admin/                # Khu vực quản lý đặc quyền của ADMIN Mode
|   |       |-- users/            # Trang danh mục bảng Người Dùng, Edit Active
|   |       |-- roles/            # Bảng Phân Quyền Vai Trò
|   |       |-- permissions/      # Danh mục Cây phân nhánh chi tiết Action
|   |       |-- chatbots/         # Màn hình setup Bot Agent và Dataset 
|   |
|   |-- components/               # Module mảnh HTML View Code 
|   |   |-- Auth/                 # Layout Login box
|   |   |-- Chat/                 # Layout đoạn chat, Cột Box nhập chữ v.v.
|   |   |-- Dataset/              # Quản lý Table Upload file Document
|   |   |-- Admin/                # Reusabe các Table data CMS
|   |   |-- Layout/               # Sidebar dọc menu hoặc Header Profile nav component
|   |   |-- Common/               # Modal, Button, Alert popup xài dùng chung
|   |
|   |-- services/                 # Khu Vực Cung Cấp Hàm Client giao tiếp Mạng (REST API Fetch)
|   |   |-- authService.ts        # Đóng gói gọi POST Signup/Sign in API
|   |   |-- chatService.ts        # Đóng gói gọi Push messages API
|   |   |-- datasetService.ts     # Function tải files và xem Meta table Dataset API
|   |   |-- rbacService.ts        # Fetch Role API Management
|   |   |-- storageService.ts     # Wrapper lấy/lưu string vào trình duyệt Localstorage
|   |
|   |-- stores/                   # Quản lý Trạng Thái Toàn Cục (Global State Store bằng Zustand)
|   |   |-- authStore.ts          # Memory lưu user hiện tại, lưu access Token
|   |   |-- chatStore.ts          # Memory giữ Array Message đang trò chuyện liên tục (cột trái/phải)
|   |   |-- datasetStore.ts       # State mảng dataset Load theo trang
|   |
|   |-- infrastructure/           # Hạ tầng Kết Nối Môi Trường HTTP
|   |   |-- http/
|   |       |-- auth.client.ts    # Setup Axios Interceptor dành riêng Auth Backend (Port 8001)
|   |       |-- core.client.ts    # Setup Axios Interceptor dành riêng Core Backend (Port 8000)
|   |
|   |-- types/                    # Nơi chia sẻ các Interface/Type Model cho Data Entity
|   |
|   |-- hooks/                    # Nơi đóng gói custom React Lifecycles (useFetch, useUI...)
|   |
|   |-- utils/                    # Các helper function phụ như String formatter hay Date convert
|
|-- public/                       # Static File Folder Images Assets, SVG icon
|
|-- k8s/                          # Manifest Setup Deploy Frontend UI Deployment Node js
```

### Luồng xử lý UI - Chat Flow

Sơ đồ trình bày cách mà một chuỗi tin nhắn của người dùng đi từ lúc gõ phím đến lúc update UI cho đến khi nhận được Text Reponse tạo thành luồng liền mạch trên Trình duyệt.

```text
+-----------------------------------------------------------------------------+
|                     UI CHAT FLOW                                            |
+-----------------------------------------------------------------------------+
|                                                                             |
|  1. USER TYPES MESSAGE                                                      |
|     +--------------------+                                                  |
|     |    ChatInput.tsx   |                                                  |
|     |  +--------------+  |                                                  |
|     |  | "Quy định    |  |                                                  |
|     |  |  nghỉ phép?" |  |                                                  |
|     |  +------+-------+  |                                                  |
|     +---------+----------+                                                  |
|               |                                                             |
|               v                                                             |
|  2. ZUSTAND STATE UPDATE (Optimistic UI)                                    |
|     +--------------------+                                                  |
|     |   chatStore.ts     |                                                  |
|     |  +--------------+  |                                                  |
|     |  | addMessage() |  |  <- Cập nhật UI ngay tức khắc thành tin gửi đi   |
|     |  | setLoading() |  |  <- Tạo hiệu ứng "Typing/Loading" quay tròn      |
|     |  +------+-------+  |                                                  |
|     +---------+----------+                                                  |
|               |                                                             |
|               v                                                             |
|  3. API CALL                                                                |
|     +--------------------+                                                  |
|     |  chatService.ts    |                                                  |
|     |  +--------------+  |                                                  |
|     |  | askQuestion()|  |                                                  |
|     |  +------+-------+  |                                                  |
|     +---------+----------+                                                  |
|               |                                                             |
|               v                                                             |
|  4. HTTP REQUEST                                                            |
|     +--------------------+                                                  |
|     |  core.client.ts    |                                                  |
|     |  +--------------+  |                                                  |
|     |  | POST         |  |                                                  |
|     |  | /api/v1/chat |  |  -> Gửi Header: Authorization: Bearer {token}    |
|     |  | /ask         |  |                                                  |
|     |  +------+-------+  |                                                  |
|     +---------+----------+                                                  |
|               |                                                             |
|               |  ===============================================            |
|               |              CORE SERVICE PROCESSING                        |
|               |  ===============================================            |
|               |                                                             |
|               v                                                             |
|  5. RESPONSE                                                                |
|     +--------------------+                                                  |
|     |  {                 |                                                  |
|     |    answer: "...",  |                                                  |
|     |    sources: [...], |                                                  |
|     |    debug: {...}    |                                                  |
|     |  }                 |                                                  |
|     +---------+----------+                                                  |
|               |                                                             |
|               v                                                             |
|  6. UPDATE STATE & UI                                                       |
|     +--------------------+                                                  |
|     |   chatStore.ts     |                                                  |
|     |  +--------------+  |                                                  |
|     |  | addMessage() |  |  <- Ghi tin nhắn Text hoàn chỉnh vào list Chat   |
|     |  | setLoading() |  |  <- Tắt Load quay tròn                           |
|     |  +------+-------+  |                                                  |
|     +---------+----------+                                                  |
|               |                                                             |
|               v                                                             |
|  7. RENDER                                                                  |
|     +--------------------+                                                  |
|     | ChatMessages.tsx   |                                                  |
|     |  +--------------+  |                                                  |
|     |  | User:        |  |                                                  |
|     |  | "Quy định?"  |  |                                                  |
|     |  |              |  |                                                  |
|     |  | Bot:         |  |                                                  |
|     |  | "Theo quy..."|  |                                                  |
|     |  +--------------+  |                                                  |
|     +--------------------+                                                  |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## 4. Thiết kế Database Schema

Dữ liệu hệ thống lưu vào 2 database logic trong MongoDB và 1 Instance Vector Map (Qdrant).

### Cấu trúc MongoDB Collections

```text
+-----------------------------------------------------------------------------+
|                      MONGODB COLLECTIONS                                    |
+-----------------------------------------------------------------------------+
|                                                                             |
|  [ AUTH DATABASE ]  (Tên: airc_auth_db)                                     |
|  +---------------------------------------------------------------------+    |
|  |                                                                     |    |
|  |  Table: users                    Table: roles                       |    |
|  |  +-------------------+          +-------------------+               |    |
|  |  | _id: ObjectId     |          | _id: ObjectId     |               |    |
|  |  | email: string     |          | code: string      |               |    |
|  |  | hashed_password   |          | name: string      |               |    |
|  |  | full_name: string |          | description       |               |    |
|  |  | role: string -----+--------->| permissions: []   |               |    |
|  |  | role_ids: []      |          | is_active: bool   |               |    |
|  |  | is_active: bool   |          +-------------------+               |    |
|  |  | created_at: Date  |                                              |    |
|  |  +-------------------+          Table: permissions                  |    |
|  |                                 +-------------------+               |    |
|  |                                 | _id: ObjectId     |               |    |
|  |                                 | code: string      |               |    |
|  |                                 | name: string      |               |    |
|  |                                 | category: string  |               |    |
|  |                                 | is_active: bool   |               |    |
|  |                                 +-------------------+               |    |
|  |                                                                     |    |
|  +---------------------------------------------------------------------+    |
|                                                                             |
|  [ CORE DATABASE ] (Tên: airc_chatbot)                                      |
|  +---------------------------------------------------------------------+    |
|  |                                                                     |    |
|  |  Table: chatbots                 Table: datasets                    |    |
|  |  +-------------------+          +-------------------+               |    |
|  |  | _id: ObjectId     |          | _id: ObjectId     |               |    |
|  |  | name: string      |          | name: string      |               |    |
|  |  | description       |          | description       |               |    |
|  |  | dataset_ids: [] --+--------->| owner_id: string  |               |    |
|  |  | allowed_roles: [] |          | file_count: int   |               |    |
|  |  | owner_id: string  |          | total_chunks: int |               |    |
|  |  | is_active: bool   |          | created_at: Date  |               |    |
|  |  +-------------------+          +---------+---------+               |    |
|  |                                           |                         |    |
|  |  Table: files                    Table: dataset_files               |    |
|  |  +-------------------+          +-------------------+               |    |
|  |  | _id: ObjectId     |<---------| file_id: ObjectId |               |    |
|  |  | filename: string  |          | dataset_id -------+----+          |    |
|  |  | path: string      |          | status: enum      |               |    |
|  |  | mimetype: string  |          | chunk_count: int  |               |    |
|  |  | size: int         |          | created_at: Date  |               |    |
|  |  +-------------------+          +-------------------+               |    |
|  |                                                                     |    |
|  |  Table: chunks                   Table: chat_sessions               |    |
|  |  +-------------------+          +-------------------+               |    |
|  |  | _id: ObjectId     |          | _id: ObjectId     |               |    |
|  |  | dataset_id        |          | name: string      |               |    |
|  |  | file_id           |          | user_id: string   |               |    |
|  |  | text: string      |          | messages: [       |               |    |
|  |  | chunk_index: int  |          |   {role, content} |               |    |
|  |  | metadata: {}      |          | ]                 |               |    |
|  |  +-------------------+          | created_at: Date  |               |    |
|  |                                 +-------------------+               |    |
|  |                                                                     |    |
|  +---------------------------------------------------------------------+    |
|                                                                             |
+-----------------------------------------------------------------------------+
```

### Cấu trúc Qdrant Vector Collections

```text
+-----------------------------------------------------------------------------+
|                      QDRANT VECTOR DB                                       |
+-----------------------------------------------------------------------------+
|                                                                             |
|  Tên Tập Hợp: dataset_{dataset_id}                                          |
|  +---------------------------------------------------------------------+    |
|  |                                                                     |    |
|  |  Vector Item 1                  Vector Item 2                       |    |
|  |  +-------------------+          +-------------------+               |    |
|  |  | id: chunk_id      |          | id: chunk_id      |               |    |
|  |  | vector: [768-dim] |          | vector: [768-dim] |               |    |
|  |  | payload: {        |          | payload: {        |               |    |
|  |  |   chunk_id,       |          |   chunk_id,       |               |    |
|  |  |   dataset_id,     |          |   dataset_id,     |               |    |
|  |  |   file_id,        |          |   file_id,        |               |    |
|  |  |   text_preview    |          |   text_preview    |               |    |
|  |  | }                 |          | }                 |               |    |
|  |  +-------------------+          +-------------------+               |    |
|  |                                                                     |    |
|  |  Khớp khoảng cách Vector: Tính theo Cosine Similarity Euclidean     |    |
|  |  Thuật toán lập chỉ mục Indexing: Mã nguồn theo cấu trúc thuật      |    |
|  |     toán HNSW (Hierarchical Navigable Small World).                 |    |
|  |                                                                     |    |
|  +---------------------------------------------------------------------+    |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## 5. Tóm tắt Biến môi trường (Environment Variables)

Mọi service định dạng cấu trúc bảo mật và IP kết nối qua tập biến hệ điều hành. Tuyệt đối không commit các file mang extension .env lên Git. Tham khảo định nghĩa trong `.env.example` của mỗi Service nhé.

```text
+-----------------------------------------------------------------------------+
|                    ENVIRONMENT VARIABLES                                    |
+-----------------------------------------------------------------------------+
|                                                                             |
|  [ AUTH SERVICE ] (file cấu hình .env tại folder Auth)                      |
|  +---------------------------------------------------------------------+    |
|  |  MONGODB_URL=mongodb://localhost:27017                              |    |
|  |  MONGODB_DB_NAME=airc_auth_db                                       |    |
|  |  JWT_SECRET_KEY=your-secret-key        <--- Phải đồng quy với Core! |    |
|  |  JWT_ALGORITHM=HS256                                                |    |
|  |  JWT_EXPIRE_MINUTES=1440                                            |    |
|  +---------------------------------------------------------------------+    |
|                                                                             |
|  [ CORE SERVICE (.env) file cấu hình .env tại folder Core              ]    |
|  +---------------------------------------------------------------------+    |
|  |  MONGODB_URL=mongodb://localhost:27017                              |    |
|  |  MONGODB_DB_NAME=airc_chatbot                                       |    |
|  |  REDIS_URL=redis://localhost:6379/0                                 |    |
|  |  QDRANT_URL=http://localhost:6333                                   |    |
|  |  AUTH_SERVICE_URL=http://localhost:8001                             |    |
|  |  JWT_SECRET_KEY=your-secret-key        <--- Phải đồng quy với Auth! |    |
|  |  GEMINI_API_KEY=your-api-key                                        |    |
|  |  GEMINI_MODEL=models/gemini-2.5-flash                               |    |
|  +---------------------------------------------------------------------+    |
|                                                                             |
|  [ UI SERVICE (build args / .env.local)  file biến số NextJS           ]    |
|  +---------------------------------------------------------------------+    |
|  |  NEXT_PUBLIC_AUTH_API=http://localhost:8001/api/auth                |    |
|  |  NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1                   |    |
|  |  NEXT_PUBLIC_APP_URL=http://localhost:3000                          |    |
|  +---------------------------------------------------------------------+    |
+-----------------------------------------------------------------------------+
```

# 🧠 Core Service - Tài liệu Chi tiết API

> **Service**: airc_internal_chatbot_core  
> **Port**: 8000  
> **Framework**: FastAPI  
> **Database**: MongoDB (airc_chatbot), Qdrant, Redis

---

## 📑 Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Chat API](#2-chat-api)
3. [Chatbot API](#3-chatbot-api)
4. [Dataset API](#4-dataset-api)
5. [File API](#5-file-api)
6. [Session API](#6-session-api)
7. [Stats API](#7-stats-api)
8. [Xác thực Token](#8-xác-thực-token)
9. [Background Processing](#9-background-processing)

---

## 1. Tổng quan

Core Service là **trung tâm xử lý nghiệp vụ** của hệ thống AIRC Chatbot, bao gồm:

- 🤖 **RAG Chat**: Trả lời câu hỏi dựa trên tài liệu
- 📊 **Datasets**: Quản lý bộ dữ liệu tài liệu
- 📁 **Files**: Upload và quản lý files
- 💬 **Sessions**: Lưu lịch sử chat
- 🤖 **Chatbots**: Cấu hình bot cho từng use case

### Base URL

```
http://localhost:8000/api/v1
```

### Collections MongoDB (airc_chatbot)

| Collection      | Mô tả                             |
| --------------- | --------------------------------- |
| `datasets`      | Thông tin bộ dữ liệu              |
| `files`         | Metadata files đã upload          |
| `dataset_files` | Mapping dataset ↔ file với status |
| `chunks`        | Text chunks sau khi processing    |
| `chatbots`      | Cấu hình chatbot                  |
| `chat_sessions` | Session chat của user             |
| `messages`      | Tin nhắn trong session            |

### External Services

| Service           | Mục đích                   |
| ----------------- | -------------------------- |
| **Auth Service**  | Xác thực JWT token         |
| **Qdrant**        | Vector database cho RAG    |
| **Redis**         | Job queue + Semantic cache |
| **Google Gemini** | LLM sinh câu trả lời       |

---

## 2. Chat API

### `POST /api/v1/chat/ask`

**Chức năng chính** của hệ thống - Gửi câu hỏi và nhận câu trả lời từ RAG pipeline.

**Quyền yêu cầu**: `chat:use` (tất cả users)

#### Request Body

```json
{
  "question": "Quy trình nộp bài tập như thế nào?",
  "chatbot_id": "65a1b2c3d4e5f6789012001",
  "session_id": "65a1b2c3d4e5f6789099001",
  "dataset_ids": ["65a1b2c3d4e5f6789033001"],
  "history": [
    { "role": "user", "content": "Xin chào" },
    { "role": "assistant", "content": "Chào bạn! Tôi có thể giúp gì?" }
  ]
}
```

| Field         | Type      | Required | Mô tả                                           |
| ------------- | --------- | -------- | ----------------------------------------------- |
| `question`    | string    | ✅       | Câu hỏi của user                                |
| `chatbot_id`  | string    | ⭕       | ID chatbot (quyết định datasets + config)       |
| `session_id`  | string    | ⭕       | ID session để lưu history                       |
| `dataset_ids` | string[]  | ⭕       | Override datasets (bị ignore nếu có chatbot_id) |
| `history`     | Message[] | ⭕       | Lịch sử chat (tự load nếu có session_id)        |

#### Response thành công (200)

```json
{
  "status": "success",
  "question": "Quy trình nộp bài tập như thế nào?",
  "answer": "Theo tài liệu hướng dẫn, quy trình nộp bài tập gồm 3 bước:\n1. Đăng nhập vào hệ thống...\n2. Chọn môn học...\n3. Upload file bài tập...",
  "sources": [
    {
      "dataset_id": "65a1b2c3d4e5f6789033001",
      "dataset_name": "Hướng dẫn sinh viên",
      "file_name": "quy_trinh_nop_bai.pdf",
      "chunk_text": "Quy trình nộp bài tập online bao gồm các bước sau...",
      "score": 0.89
    }
  ],
  "errors": [],
  "debug": {
    "total_time_ms": 2340,
    "embedding_time_ms": 45,
    "retrieval_time_ms": 120,
    "rerank_time_ms": 85,
    "llm_time_ms": 2090,
    "cache_hit": false,
    "chunks_found": 15,
    "chunks_after_rerank": 5,
    "avg_similarity_score": 0.76,
    "top_similarity_score": 0.89,
    "datasets_searched": 1,
    "model_used": "gemini-2.5-flash",
    "reranker_used": "ms-marco-MiniLM-L-6-v2",
    "no_context": false
  }
}
```

#### Response lỗi quyền (403)

```json
{
  "detail": "Bạn không có quyền truy cập Chatbot 'Chatbot Nội bộ'."
}
```

#### Luồng xử lý chi tiết

```
┌─────────────────────────────────────────────────────────────┐
│                    POST /api/v1/chat/ask                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. TOKEN VERIFICATION                                        │
│    - Extract token từ Authorization header                   │
│    - POST /api/auth/verify → Auth Service                   │
│    - Nhận user_id, email, role                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. PERMISSION CHECK                                          │
│    - require_permission(Permission.CHAT_USE)                │
│    - Admin bypass mọi permission check                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. CHATBOT RBAC CHECK (nếu có chatbot_id)                   │
│    - Fetch chatbot từ DB                                    │
│    - Kiểm tra user.role in chatbot.allowed_roles            │
│    - Admin bypass check                                      │
│    - ❌ 403 nếu không có quyền                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. CONTEXT LOCKING 🔒                                        │
│    - Override dataset_ids = chatbot.dataset_ids             │
│    - User KHÔNG thể inject datasets khác                    │
│    - Bảo vệ chống data injection attack                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. SESSION HANDLING                                          │
│    - Lưu message user vào session (nếu có session_id)       │
│    - Load history từ DB (nếu không truyền history)          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. SEMANTIC CACHE CHECK                                      │
│    - Embed question → vector 768 chiều                      │
│    - Cache key = question + chatbot_id                      │
│    - ⚡ Return cached answer nếu HIT                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. VECTOR SEARCH (Retrieval)                                 │
│    - Với mỗi dataset_id:                                    │
│      + Search Qdrant collection "dataset_{id}"              │
│      + Cosine similarity với question embedding             │
│      + Lấy top_k chunks (default: 5)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. RERANKING                                                 │
│    - Sử dụng Cross-Encoder model                            │
│    - Sắp xếp lại chunks theo độ liên quan thực sự           │
│    - Loại bỏ chunks có score thấp dưới threshold            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. NO CONTEXT HANDLING                                       │
│    Nếu không tìm thấy chunks:                               │
│    - "reject": Trả thông báo từ chối                        │
│    - "custom_message": Trả message tùy chỉnh                │
│    - "fallback_llm": Vẫn gọi LLM (general knowledge)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 10. PROMPT BUILDING                                          │
│    - System prompt (từ chatbot config hoặc default)         │
│    - Context chunks                                          │
│    - Chat history                                            │
│    - User question                                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 11. LLM GENERATION                                           │
│    - Gọi Google Gemini API                                  │
│    - Model: gemini-2.5-flash (hoặc từ config)               │
│    - Nhận generated answer                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 12. POST-PROCESSING                                          │
│    - Cache answer vào Redis (với chatbot_id)                │
│    - Lưu assistant message vào session                      │
│    - Return ChatResponse với debug metrics                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Chatbot API

### `GET /api/v1/chatbots`

Lấy danh sách chatbots user có quyền truy cập.

**Quyền**: Authenticated

#### Response (200)

```json
[
  {
    "id": "65a1b2c3d4e5f6789012001",
    "name": "Chatbot Hướng dẫn",
    "description": "Hỗ trợ sinh viên về quy trình",
    "owner_id": "65a1b2c3d4e5f6789000001",
    "dataset_ids": ["65a1b2c3d4e5f6789033001"],
    "allowed_roles": ["student", "teacher"],
    "is_active": true,
    "config": {
      "top_k": 5,
      "reranker": "ms-marco-MiniLM-L-6-v2",
      "similarity_threshold": 0.5,
      "model": "gemini-2.5-flash",
      "no_context_behavior": "reject"
    }
  }
]
```

**Logic filter**:

- `Admin`: Xem tất cả chatbots
- `Teacher/Student`: Xem chatbots có role trong `allowed_roles`

---

### `POST /api/v1/chatbots`

Tạo chatbot mới.

**Quyền yêu cầu**: `Admin`

#### Request Body

```json
{
  "name": "Chatbot Môn học",
  "description": "Hỗ trợ sinh viên môn Lập trình",
  "dataset_ids": ["65a1b2c3d4e5f6789033001", "65a1b2c3d4e5f6789033002"],
  "allowed_roles": ["student"],
  "config": {
    "top_k": 5,
    "reranker": "ms-marco-MiniLM-L-6-v2",
    "similarity_threshold": 0.5,
    "model": "gemini-2.5-flash",
    "system_prompt": "Bạn là trợ lý AI hỗ trợ sinh viên...",
    "no_context_behavior": "reject",
    "no_context_message": "Xin lỗi, tôi không tìm thấy thông tin..."
  }
}
```

| Field                        | Type     | Mô tả                                    |
| ---------------------------- | -------- | ---------------------------------------- |
| `name`                       | string   | Tên chatbot                              |
| `description`                | string   | Mô tả                                    |
| `dataset_ids`                | string[] | Datasets được phép search                |
| `allowed_roles`              | string[] | Roles được dùng chatbot                  |
| `config.top_k`               | int      | Số chunks tìm kiếm                       |
| `config.reranker`            | string   | Model reranker                           |
| `config.model`               | string   | LLM model                                |
| `config.system_prompt`       | string   | System prompt tùy chỉnh                  |
| `config.no_context_behavior` | string   | `reject`/`custom_message`/`fallback_llm` |

---

### `GET /api/v1/chatbots/{chatbot_id}`

Lấy chi tiết chatbot.

**Quyền**: Role trong `allowed_roles` hoặc Admin

---

### `PATCH /api/v1/chatbots/{chatbot_id}`

Cập nhật chatbot.

**Quyền**: Owner hoặc Admin

---

### `DELETE /api/v1/chatbots/{chatbot_id}`

Xóa chatbot.

**Quyền**: Owner hoặc Admin

---

### `POST /api/v1/chatbots/{chatbot_id}/datasets`

Gán datasets cho chatbot.

**Quyền**: Owner hoặc Admin

#### Request Body

```json
{
  "dataset_ids": ["65a1b2c3d4e5f6789033003"]
}
```

---

### `GET /api/v1/chatbots/meta/roles-with-chatbot`

Lấy danh sách roles đã được assign chatbot (để disable trong UI).

**Quyền**: Admin

**Mục đích**: Mỗi role (trừ admin) chỉ nên dùng 1 chatbot.

---

## 4. Dataset API

### `GET /api/v1/datasets`

Lấy danh sách datasets.

**Quyền**: Authenticated

**Logic filter theo role**:

- `Admin`: Tất cả datasets
- `Teacher`: Datasets của mình (owner_id = user_id)
- `Student`: Datasets với visibility = "shared"

#### Response (200)

```json
[
  {
    "id": "65a1b2c3d4e5f6789033001",
    "name": "Tài liệu hướng dẫn",
    "owner_id": "65a1b2c3d4e5f6789000002",
    "visibility": "shared",
    "file_count": 5,
    "total_chunks": 234,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### `POST /api/v1/datasets`

Tạo dataset mới.

**Quyền**: Admin hoặc Teacher

#### Request Body

```json
{
  "name": "Tài liệu môn học",
  "visibility": "private",
  "chatbot_ids": ["65a1b2c3d4e5f6789012001"]
}
```

| Field        | Giá trị   | Mô tả         |
| ------------ | --------- | ------------- |
| `visibility` | `private` | Chỉ owner xem |
| `visibility` | `shared`  | Mọi người xem |

---

### `GET /api/v1/datasets/{dataset_id}`

Lấy chi tiết dataset.

---

### `PATCH /api/v1/datasets/{dataset_id}`

Cập nhật dataset.

**Quyền**: Owner hoặc Admin

---

### `DELETE /api/v1/datasets/{dataset_id}`

Xóa dataset (bao gồm tất cả files, chunks trong đó).

**Quyền**: Owner hoặc Admin

---

### `POST /api/v1/datasets/{dataset_id}/files`

**Thêm files vào dataset** và trigger background processing.

**Quyền**: Admin hoặc Teacher (phải là owner nếu teacher)

#### Request Body

```json
{
  "file_ids": ["65a1b2c3d4e5f6789044001", "65a1b2c3d4e5f6789044002"]
}
```

#### Response (200)

```json
{
  "status": "success",
  "added": [
    {
      "id": "65a1b2c3d4e5f6789055001",
      "file_id": "65a1b2c3d4e5f6789044001",
      "status": "Pending"
    }
  ],
  "skipped": []
}
```

**⚠️ Quan trọng**: Sau khi thêm, background worker sẽ tự động:

1. Đọc file từ disk
2. Trích xuất text
3. Chunking (1024 chars, overlap 100)
4. Embedding (768 dimensions)
5. Index vào Qdrant

---

### `GET /api/v1/datasets/{dataset_id}/files`

Lấy danh sách files trong dataset với status.

#### Response (200)

```json
[
  {
    "id": "65a1b2c3d4e5f6789055001",
    "file_id": "65a1b2c3d4e5f6789044001",
    "file_name": "huong_dan.pdf",
    "status": "Done",
    "chunk_count": 45,
    "is_enabled": true,
    "created_at": "2024-01-15T10:30:00Z"
  },
  {
    "id": "65a1b2c3d4e5f6789055002",
    "file_id": "65a1b2c3d4e5f6789044002",
    "file_name": "quy_trinh.docx",
    "status": "Embedding",
    "chunk_count": 0,
    "is_enabled": false,
    "created_at": "2024-01-15T10:35:00Z"
  }
]
```

**Các status**:
| Status | Mô tả |
|--------|-------|
| `Pending` | Đang chờ xử lý |
| `Chunking` | Đang trích xuất và chia text |
| `Embedding` | Đang tạo embeddings |
| `Done` | Hoàn thành, sẵn sàng search |
| `Error` | Lỗi trong quá trình xử lý |

---

### `PATCH /api/v1/datasets/{dataset_id}/files/{dataset_file_id}`

Bật/tắt file trong dataset (để include/exclude khỏi search).

#### Request Body

```json
{
  "is_enabled": false
}
```

---

### `DELETE /api/v1/datasets/{dataset_id}/files/{dataset_file_id}`

Xóa file khỏi dataset (xóa cả chunks).

**Quyền**: Owner hoặc Admin

---

## 5. File API

### `POST /api/v1/files/upload`

Upload file lên server.

**Quyền**: Admin hoặc Teacher

#### Request

```
Content-Type: multipart/form-data
file: <binary>
```

**Supported formats**:

- PDF (`.pdf`)
- Word (`.docx`)
- Text (`.txt`)
- Max size: **200MB**

#### Response (201)

```json
{
  "id": "65a1b2c3d4e5f6789044001",
  "name": "huong_dan.pdf",
  "size": 1234567,
  "mime_type": "application/pdf",
  "status": "Ready",
  "uploaded_at": "2024-01-15T10:30:00Z"
}
```

**Lưu ý**:

- File được lưu vào `uploads/{user_id}/{filename}`
- File chưa được processing - cần thêm vào dataset để trigger processing

---

### `GET /api/v1/files`

Lấy danh sách tất cả files đã upload.

---

### `GET /api/v1/files/{file_id}`

Lấy thông tin file.

---

### `GET /api/v1/files/{file_id}/view`

**Xem hoặc download file**.

#### Response

- PDF, images, text: Hiển thị inline trong browser
- Các loại khác: Download attachment

---

## 6. Session API

### `GET /api/v1/sessions`

Lấy danh sách chat sessions của user.

#### Query Parameters

| Param        | Mô tả               |
| ------------ | ------------------- |
| `chatbot_id` | Filter theo chatbot |

#### Response (200)

```json
[
  {
    "id": "65a1b2c3d4e5f6789099001",
    "name": "Hỏi về quy trình nộp bài",
    "chatbot_id": "65a1b2c3d4e5f6789012001",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T11:45:00Z",
    "message_count": 8
  }
]
```

---

### `POST /api/v1/sessions`

Tạo session mới.

#### Request Body

```json
{
  "name": "Session học tập",
  "chatbot_id": "65a1b2c3d4e5f6789012001"
}
```

---

### `GET /api/v1/sessions/{session_id}`

Lấy chi tiết session với tất cả messages.

#### Response (200)

```json
{
  "id": "65a1b2c3d4e5f6789099001",
  "name": "Hỏi về quy trình nộp bài",
  "chatbot_id": "65a1b2c3d4e5f6789012001",
  "messages": [
    {
      "role": "user",
      "content": "Làm sao để nộp bài?",
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Để nộp bài, bạn cần...",
      "created_at": "2024-01-15T10:30:05Z"
    }
  ]
}
```

---

### `DELETE /api/v1/sessions/{session_id}`

Xóa session (và tất cả messages).

---

## 7. Stats API

### `GET /api/v1/stats/dashboard`

Lấy thống kê tổng quan cho dashboard.

**Quyền**: Admin

#### Response (200)

```json
{
  "total_users": 150,
  "total_chatbots": 5,
  "total_datasets": 12,
  "total_files": 89,
  "total_chunks": 4567,
  "total_sessions": 1234,
  "total_messages": 8901,
  "recent_activity": [
    {
      "type": "chat",
      "user": "student@airc.edu.vn",
      "timestamp": "2024-01-15T11:45:00Z"
    }
  ]
}
```

---

## 8. Xác thực Token

### Cơ chế xác thực

Core Service **không tự verify JWT**. Thay vào đó, gọi Auth Service:

```python
# Trong dependencies.py

async def get_current_user(
    authorization: str = Header(None)
) -> User:
    # 1. Extract token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")

    token = authorization.split(" ")[1]

    # 2. Gọi Auth Service verify
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AUTH_SERVICE_URL}/api/auth/verify",
            json={"token": token}
        )

    if response.status_code != 200:
        raise HTTPException(401, "Invalid token")

    # 3. Map response sang User model
    data = response.json()
    return User(
        user_id=data["id"],
        email=data["email"],
        role=UserRole(data["role"])
    )
```

### Permission Check

```python
def require_permission(permission: Permission):
    async def checker(user: User = Depends(get_current_user)):
        # Admin bypass
        if user.role == UserRole.ADMIN:
            return user

        # Check permission
        if not user_has_permission(user, permission):
            raise HTTPException(403, "Permission denied")

        return user
    return checker
```

---

## 9. Background Processing

### RQ Worker

File processing chạy **background** bằng RQ (Redis Queue):

```python
# worker.py
from rq import Worker, Queue
from redis import Redis

redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)
queue = Queue('ingest', connection=redis_conn)

if __name__ == '__main__':
    worker = Worker([queue], connection=redis_conn)
    worker.work()
```

### Job: process_dataset_file_job

```python
# jobs/ingest.py

def process_dataset_file_job(dataset_id: str, dataset_file_id: str):
    """
    Xử lý file trong dataset:
    1. Update status → "Chunking"
    2. Đọc file từ disk
    3. Extract text (PDF/DOCX/TXT)
    4. Chunking (1024 chars, overlap 100)
    5. Update status → "Embedding"
    6. Generate embeddings (768 dims)
    7. Lưu chunks vào MongoDB
    8. Index vectors vào Qdrant
    9. Update status → "Done"
    """
    asyncio.run(_async_process(dataset_id, dataset_file_id))
```

### Processing Config

| Setting             | Value                                   |
| ------------------- | --------------------------------------- |
| Chunk size          | 1024 characters                         |
| Chunk overlap       | 100 characters                          |
| Embedding model     | `paraphrase-multilingual-MiniLM-L12-v2` |
| Embedding dimension | 768                                     |
| Qdrant collection   | `dataset_{dataset_id}`                  |

---

## 📊 Tổng hợp Endpoints

### Chat

| Method | Endpoint           | Mô tả       | Auth        |
| ------ | ------------------ | ----------- | ----------- |
| POST   | `/api/v1/chat/ask` | Gửi câu hỏi | ✅ chat:use |

### Chatbot

| Method | Endpoint                         | Mô tả        | Auth        |
| ------ | -------------------------------- | ------------ | ----------- |
| GET    | `/api/v1/chatbots`               | Danh sách    | ✅          |
| POST   | `/api/v1/chatbots`               | Tạo mới      | Admin       |
| GET    | `/api/v1/chatbots/{id}`          | Chi tiết     | ✅ RBAC     |
| PATCH  | `/api/v1/chatbots/{id}`          | Cập nhật     | Owner/Admin |
| DELETE | `/api/v1/chatbots/{id}`          | Xóa          | Owner/Admin |
| POST   | `/api/v1/chatbots/{id}/datasets` | Gán datasets | Owner/Admin |

### Dataset

| Method | Endpoint                            | Mô tả       | Auth          |
| ------ | ----------------------------------- | ----------- | ------------- |
| GET    | `/api/v1/datasets`                  | Danh sách   | ✅            |
| POST   | `/api/v1/datasets`                  | Tạo mới     | Admin/Teacher |
| GET    | `/api/v1/datasets/{id}`             | Chi tiết    | ✅            |
| PATCH  | `/api/v1/datasets/{id}`             | Cập nhật    | Owner/Admin   |
| DELETE | `/api/v1/datasets/{id}`             | Xóa         | Owner/Admin   |
| POST   | `/api/v1/datasets/{id}/files`       | Thêm files  | Owner/Admin   |
| GET    | `/api/v1/datasets/{id}/files`       | List files  | ✅            |
| PATCH  | `/api/v1/datasets/{id}/files/{fid}` | Toggle file | ✅            |
| DELETE | `/api/v1/datasets/{id}/files/{fid}` | Xóa file    | Owner/Admin   |

### File

| Method | Endpoint                  | Mô tả        | Auth          |
| ------ | ------------------------- | ------------ | ------------- |
| POST   | `/api/v1/files/upload`    | Upload       | Admin/Teacher |
| GET    | `/api/v1/files`           | Danh sách    | ✅            |
| GET    | `/api/v1/files/{id}`      | Chi tiết     | ✅            |
| GET    | `/api/v1/files/{id}/view` | Xem/Download | ✅            |

### Session

| Method | Endpoint                | Mô tả     | Auth |
| ------ | ----------------------- | --------- | ---- |
| GET    | `/api/v1/sessions`      | Danh sách | ✅   |
| POST   | `/api/v1/sessions`      | Tạo mới   | ✅   |
| GET    | `/api/v1/sessions/{id}` | Chi tiết  | ✅   |
| DELETE | `/api/v1/sessions/{id}` | Xóa       | ✅   |

### Stats

| Method | Endpoint                  | Mô tả    | Auth  |
| ------ | ------------------------- | -------- | ----- |
| GET    | `/api/v1/stats/dashboard` | Thống kê | Admin |

---

**📝 Document Version:** 1.0  
**📅 Last Updated:** February 2025  
**👥 Author:** AIRC Team

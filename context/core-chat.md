# CODEBASE_CONTEXT - Core Chat Domain

Last updated: 2026-05-28

This file contains extracted context related to ChatService, RAG pipeline, LLM, and vector search.

## 1. Project Overview (Core Chat)

### 1.1 Purpose and business domain
- Internal enterprise chatbot platform using RAG (Retrieval-Augmented Generation) for organizational knowledge lookup.
- Three core concerns are separated:
  - RAG ingestion/retrieval/generation workflows.

### 1.2 Architecture style
- Monorepo with service boundaries.
- Microservice runtime:
  - `airc_internal_chatbot_core` (RAG API + background worker).
- Layering pattern in backend services:
  - API routers -> dependency injection -> service layer -> repository layer -> MongoDB/Qdrant/Redis.

### 1.3 Technology stack (Core)

| Area | Stack | Versions / notes |
|---|---|---|
| Core service | Python + FastAPI + Motor + Redis/RQ + Qdrant + Gemini | Docker base `python:3.10-slim`; `fastapi>=0.115`, `sentence-transformers>=2.6` |

## 2. Directory Structure (Core Chat extract)

```text
airc_internal_chatbot_core/
|- app/
|  |- main.py                    # FastAPI app, model warmup, router mounting
|  |- api/
|  |  |- dependencies.py         # token verification bridge to Auth, DI wiring
|  |  |- v1/                     # chat, sessions, chatbots endpoints
|  |- models/                    # auth/schema/chatbot/enums
|  |- repositories/              # chunks/sessions/chatbots data access
|  |- services/                  # RAG pipeline logic
```

## 3. Entry Points and Runtime (Core Chat)

### 3.1 Backend entrypoints
- Core API entrypoint: `airc_internal_chatbot_core/app/main.py`
  - mounts `/api/v1/{chat,datasets,files,sessions,chatbots,stats}`
  - preloads embedding/rerank models and configures LLM service.

## 4. Core Modules / Components (Core Chat)

### 4.1 ChatService (RAG orchestrator)
- Path: `airc_internal_chatbot_core/app/services/chat_service.py`
- Responsibility:
  - complete RAG request lifecycle: embed -> cache -> retrieval -> rerank -> prompt -> generate -> session persistence.
  - enforces chatbot access gating theo user/department và dataset context locking.
- Key signatures:

```python
class ChatService:
    async def ask_question(
        self,
        question: str,
        dataset_ids: List[str],
        history: Optional[List[Dict]] = None,
        session_id: Optional[str] = None,
        chatbot_id: Optional[str] = None,
        user_context: Optional[Dict] = None,
    ) -> Dict[str, Any]
```

- Depends on:
  - repositories (`dataset`, `dataset_file`, `chunk`, optional `session`, `chatbot`)
  - services (`embedding_service`, `vector_service`, `rerank_service`, `prompt_service`, `llm_service`, `semantic_cache_service`).
- Imported by:
  - DI in `app/api/dependencies.py`, used by `app/api/v1/chat.py`.

### 4.2 ChatbotService
- Path: `airc_internal_chatbot_core/app/services/chatbot_service.py`
- Responsibility:
  - chatbot CRUD, RBAC visibility filtering, dataset assignment, admin-only create gate.
- Key signatures:

```python
class ChatbotService:
    async def create_chatbot(self, creator_id: str, creator_role: str, data: ChatbotCreate) -> dict
    async def get_available_chatbots(self, user_id: str, user_role: str) -> List[dict]
    async def update_chatbot(self, chatbot_id: str, user_id: str, user_role: str, data: ChatbotUpdate) -> Optional[dict]
```

- Depends on:
  - `ChatbotRepository`, `DatasetRepository`.
- Imported by:
  - DI and `app/api/v1/chatbots.py`.

### 4.3 SessionRepository
- Path: `airc_internal_chatbot_core/app/repositories/session_repository.py`
- Responsibility:
  - persistent session/message storage and ownership-bound retrieval.
- Key signatures:

```python
class SessionRepository(BaseRepository):
    async def create_session(self, user_id: str, name: str) -> dict
    async def get_user_sessions(self, user_id: str, limit: int = 50, skip: int = 0) -> List[dict]
    async def add_message(self, session_id: str, role: str, content: str) -> dict
    async def get_messages(self, session_id: str, limit: int = 100) -> List[dict]
```

- Depends on:
  - Mongo collections `sessions`, `messages`.
- Imported by:
  - `app/api/v1/sessions.py`, `ChatService` (through DI).

## 5. Complete Function Signatures (Core Chat)

### 5.1 ChatService (complete signatures)

```python
class ChatService:
    def __init__(
        self,
        dataset_repo: DatasetRepository,
        dataset_file_repo: DatasetFileRepository,
        chunk_repo: ChunkRepository,
        session_repo: Any = None,
        chatbot_repo: Any = None
    )

    async def ask_question(
        self,
        question: str,
        dataset_ids: List[str],
        history: Optional[List[Dict]] = None,
        session_id: Optional[str] = None,
        chatbot_id: Optional[str] = None,
        user_context: Optional[Dict] = None
    ) -> Dict[str, Any]

    async def _search_dataset(
        self,
        dataset_id: str,
        question: str,
        q_vec: Optional[np.ndarray],
        top_k: int = DEFAULT_TOP_K
    ) -> Dict[str, Any]

    def _try_embed_question(self, question: str) -> Optional[np.ndarray]

    async def _list_all_datasets_context(self, grouped_results: List[Dict])

    def _apply_reranking(
        self,
        question: str,
        grouped_results: List[Dict],
        reranker_model: Optional[str] = None
    )

    async def _generate_answer(
        self,
        prompt: str,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> str

    def _format_response(
        self,
        question: str,
        answer: str,
        sources: List[Dict],
        errors: List[Dict],
        cached: bool,
        no_context: bool = False,
        debug_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]
```

| Signature | One-line description |
|---|---|
| `__init__(...)` | Inject repositories phục vụ retrieval, dataset filtering và session/chatbot logic. |
| `ask_question(...)` | Orchestrate end-to-end RAG request và trả về response chuẩn cho API. |
| `_search_dataset(...)` | Tìm chunks liên quan trong một dataset (vector + regex + merge/deduplicate). |
| `_try_embed_question(...)` | Embed câu hỏi và trả `None` nếu embed thất bại. |
| `_list_all_datasets_context(...)` | Legacy helper để nạp context tất cả datasets khi không chỉ định dataset cụ thể. |
| `_apply_reranking(...)` | Áp dụng reranker theo cấu hình chatbot lên grouped retrieval results. |
| `_generate_answer(...)` | Gọi LLM service để sinh câu trả lời từ prompt đã build. |
| `_format_response(...)` | Chuẩn hóa payload trả về gồm answer, sources, errors và debug metrics. |

### 5.2 VectorService (complete signatures)

```python
class VectorService:
    def __init__(self)

    @property
    def client(self)

    def _get_collection_name(self, dataset_id: str) -> str

    def _ensure_collection(self, collection_name: str, vector_size: int)

    def add_vectors(
        self,
        dataset_id: str,
        vectors: np.ndarray,
        payloads: List[Dict[str, Any]]
    ) -> List[str]

    def search(
        self,
        dataset_id: str,
        query_vector: np.ndarray,
        top_k: int = 5,
        allowed_file_ids: Optional[List[str]] = None
    ) -> Tuple[List[float], List[Dict[str, Any]]]

    def delete_index(self, dataset_id: str)
```

| Signature | One-line description |
|---|---|
| `__init__()` | Khởi tạo lazy state cho Qdrant client. |
| `client` | Property trả về Qdrant client đã được lazy-initialize. |
| `_get_collection_name(...)` | Chuẩn hóa tên collection theo convention `dataset_<dataset_id>`. |
| `_ensure_collection(...)` | Tạo collection nếu chưa tồn tại với vector dimension tương ứng. |
| `add_vectors(...)` | Upsert batch vectors và trả về danh sách point IDs đã ghi. |
| `search(...)` | Similarity search theo query vector, hỗ trợ filter dataset_file_id. |
| `delete_index(...)` | Xóa toàn bộ collection của dataset trong Qdrant. |

### 5.3 SessionRepository (complete signatures)

```python
class SessionRepository(BaseRepository):
    def __init__(self, db)

    async def create_session(self, user_id: str, name: str) -> dict

    async def get_user_sessions(self, user_id: str, limit: int = 50, skip: int = 0) -> List[dict]

    async def get_session(self, session_id: str) -> Optional[dict]

    async def update_session(self, session_id: str, update_data: dict) -> Optional[dict]

    async def delete_session(self, session_id: str) -> bool

    async def add_message(self, session_id: str, role: str, content: str) -> dict

    async def get_messages(self, session_id: str, limit: int = 100) -> List[dict]
```

| Signature | One-line description |
|---|---|
| `__init__(...)` | Khởi tạo repository sessions và giữ handle riêng cho collection `messages`. |
| `create_session(...)` | Tạo phiên chat mới cho user. |
| `get_user_sessions(...)` | Lấy danh sách sessions theo user, có phân trang. |
| `get_session(...)` | Lấy thông tin chi tiết một session. |
| `update_session(...)` | Cập nhật metadata session và refresh `updated_at`. |
| `delete_session(...)` | Xóa session và toàn bộ messages liên quan. |
| `add_message(...)` | Lưu tin nhắn mới vào history của session. |
| `get_messages(...)` | Lấy lịch sử tin nhắn theo thứ tự thời gian tăng dần. |

## 6. Data Models and Schemas (Core Chat)

### 6.1 Core-side entities

| Entity | Source | Fields (type) |
|---|---|---|
| Dataset (`datasets`) | `dataset_repository.py` | `name:str`, `owner_id:str`, `visibility:str`, `shared_with:list[str]`, `created_at:datetime` |
| DatasetFile (`dataset_files`) | `dataset_file_repository.py` | `dataset_id:str`, `file_id:str`, `status:str`, `chunk_count:int`, `is_enabled:bool`, `created_at:datetime`, `processed_at?:datetime` |
| Chunk (`chunks`) | `chunk_repository.py` | `dataset_id:str`, `dataset_file_id:str`, `file_id:str`, `chunk_index:int`, `text:str`, `vector_id?:int` |
| Chatbot (`chatbots`) | `chatbot_repository.py` + `chatbot_schemas.py` | `name:str`, `description?:str`, `icon?:str`, `config:dict`, `dataset_ids:list[str]`, `allowed_user_ids:list[str]`, `allowed_departments:list[str]`, `visibility:str`, `owner_id:str`, `is_active:bool`, `created_at`, `updated_at?` |
| Session (`sessions`) | `session_repository.py` | `user_id:str`, `name:str`, `created_at`, `updated_at` |
| Message (`messages`) | `session_repository.py` | `session_id:str`, `role:str`, `content:str`, `created_at` |

### 6.2 Vector store payload model
- Qdrant collection naming: `dataset_<dataset_id>`.
- Payload used in vector points:
  - `chunk_id`, `dataset_file_id`, `dataset_id`.

### 6.3 Key DTO schemas

| DTO | Source | Key fields |
|---|---|---|
| `ChatRequest` | `core/app/models/schemas.py` | `question`, `dataset_ids[]`, `session_id?`, `chatbot_id?`, `history?` |
| `ChatResponse` | same | `status`, `question`, `answer`, `sources[]`, `errors[]`, `debug?` |
| `ChatbotConfigModel` | `core/app/models/chatbot_schemas.py` | retrieval/reranker/LLM/prompt/no-context behavior config |

## 7. API / Interface Contracts (Core Chat)

### 7.1 Core API (`/api/v1`) - Chat

| Method | Path | Input | Output | Side effects |
|---|---|---|---|---|
| POST | `/chat/ask` | `ChatRequest` | `ChatResponse` | may persist session messages, reads vector DB, calls Gemini, updates semantic cache |

### 7.2 Core API (`/api/v1`) - Sessions

| Method | Path | Input | Output | Side effects |
|---|---|---|---|---|
| POST | `/sessions/` | `ChatSessionCreate` | `ChatSessionResponse` | creates session |
| GET | `/sessions/` | `limit,skip` | `ChatSessionResponse[]` | none |
| GET | `/sessions/{session_id}` | path param | `ChatSessionResponse` | none |
| PATCH | `/sessions/{session_id}` | `ChatSessionUpdate` | `ChatSessionResponse` | updates session |
| DELETE | `/sessions/{session_id}` | path param | message payload | deletes session + all session messages |
| GET | `/sessions/{session_id}/messages` | `limit` | `ChatMessageResponse[]` | none |
| POST | `/sessions/{session_id}/messages` | `ChatMessageCreate` | `ChatMessageResponse` | appends message |

### 7.3 Core API (`/api/v1`) - Chatbots

| Method | Path | Input | Output | Side effects |
|---|---|---|---|---|
| POST | `/chatbots` | `ChatbotCreate` | `ChatbotResponse` | creates chatbot (admin only) |
| GET | `/chatbots` | none | `ChatbotResponse[]` | user/department-filtered visibility |
| GET | `/chatbots/{chatbot_id}` | path param | `ChatbotResponse` | permission checks |
| PATCH | `/chatbots/{chatbot_id}` | `ChatbotUpdate` | `ChatbotResponse` | updates chatbot |
| DELETE | `/chatbots/{chatbot_id}` | path param | `SuccessResponse` | deletes chatbot |
| POST | `/chatbots/{chatbot_id}/datasets` | `ChatbotAssignDatasetsRequest` | `ChatbotResponse` | replaces chatbot dataset links |

## 8. Business Logic and Rules (Core Chat)

### 8.1 Chatbot access and context isolation
- Chatbot create is `admin` only.
- For non-admin users, chatbot usage requires either explicit `allowed_user_ids` match or `allowed_departments` match.
- If both `allowed_user_ids` and `allowed_departments` are empty, chatbot is private (admin-only).
- Critical security behavior in chat pipeline:
  - If `chatbot_id` exists and has `dataset_ids`, user-supplied `dataset_ids` are overridden (context locking).
  - Additional dataset accessibility filtering for non-admin users: only owner/shared datasets remain.

### 8.2 RAG request algorithm (`ChatService.ask_question`)
1. Validate input and optionally persist user message to session.
2. Embed question.
3. Attempt semantic cache hit (cache key optionally namespaced by chatbot).
4. Resolve chatbot config (`top_k`, reranker, model, prompt, no-context behavior).
5. Retrieve chunks per dataset:
   - vector search in Qdrant (filtered to enabled files),
   - regex fallback search in chunks collection.
6. Optional rerank.
7. If no context:
   - `reject` -> return refusal.
   - `custom_message` -> return configured message.
   - `fallback_llm` -> continue with LLM.
8. Build prompt and call Gemini.
9. Cache successful answer and persist assistant message.
10. Return answer + sources + debug metrics.

## 9. Configuration and Environment (Core Chat)

### 9.1 Required env vars (Core)

| Variable | Required | Default / note |
|---|---|---|
| `MONGODB_URL` | yes | no default in settings |
| `JWT_SECRET_KEY` | yes | must match auth design assumption |
| `GEMINI_API_KEY` | yes | required for generation |
| `MONGODB_DB_NAME` | no | `airc_chatbot` |
| `QDRANT_URL` | no | `http://qdrant:6333` |
| `AUTH_SERVICE_URL` | no | `http://localhost:8001` |
| `GEMINI_MODEL` | no | `models/gemini-2.5-flash` |
| `DEBUG` | no | `False` |

### 9.2 Feature/config behavior knobs
- Chatbot config controls retrieval/rerank/LLM/prompt/no-context behavior per chatbot.
- `no_context_behavior`: `reject | fallback_llm | custom_message`.

## 10. Dependency Graph (Core Chat)

### 10.1 Core chat path

```mermaid
graph LR
  UI --> ChatAPI[/api/v1/chat/ask]
  ChatAPI --> CoreDeps[get_current_user]
  CoreDeps --> AuthVerify[POST /api/auth/verify]
  ChatAPI --> ChatService
  ChatService --> Embed
  ChatService --> Cache
  ChatService --> Vector[Qdrant search]
  ChatService --> ChunkRepo
  ChatService --> Rerank
  ChatService --> Prompt
  ChatService --> LLM[Gemini]
  ChatService --> SessionRepo
  ChunkRepo --> Mongo[(MongoDB)]
  SessionRepo --> Mongo
```

## 11. Core API Error Contract (Core Chat)

### 11.1 Chat API (`/api/v1/chat`)

| Method | Path | Error statuses and trigger conditions |
|---|---|---|
| POST | `/api/v1/chat/ask` | `401`: thiếu/sai `Authorization` hoặc token verify qua Auth service thất bại.<br>`403`: `ChatService` raise `PermissionError` (không đủ quyền dùng chatbot).<br>`422`: payload `ChatRequest` không hợp lệ.<br>`500`: lỗi không kiểm soát trong flow hỏi đáp (được wrap thành `Failed to process question`). |

### 11.2 Sessions API (`/api/v1/sessions`)

| Method | Path | Error statuses and trigger conditions |
|---|---|---|
| POST | `/api/v1/sessions/` | `401`: thiếu/sai token.<br>`422`: body `ChatSessionCreate` không hợp lệ.<br>`500`: lỗi không kiểm soát khi tạo session. |
| GET | `/api/v1/sessions/` | `401`: thiếu/sai token.<br>`422`: query params (`limit`, `skip`) sai kiểu/không hợp lệ.<br>`500`: lỗi không kiểm soát khi list sessions. |
| GET | `/api/v1/sessions/{session_id}` | `401`: thiếu/sai token.<br>`404`: session không tồn tại.<br>`403`: session không thuộc user hiện tại.<br>`500`: lỗi không kiểm soát khi truy vấn. |
| PATCH | `/api/v1/sessions/{session_id}` | `401`: thiếu/sai token.<br>`404`: session không tồn tại (trước hoặc sau update).<br>`403`: không có quyền update session này.<br>`422`: body `ChatSessionUpdate` không hợp lệ.<br>`500`: lỗi không kiểm soát khi update. |
| DELETE | `/api/v1/sessions/{session_id}` | `401`: thiếu/sai token.<br>`404`: session không tồn tại.<br>`403`: không có quyền xóa session này.<br>`500`: delete thất bại hoặc lỗi runtime. |
| GET | `/api/v1/sessions/{session_id}/messages` | `401`: thiếu/sai token.<br>`404`: session không tồn tại.<br>`403`: không có quyền xem messages của session này.<br>`422`: query `limit` không hợp lệ.<br>`500`: lỗi không kiểm soát khi lấy messages. |
| POST | `/api/v1/sessions/{session_id}/messages` | `401`: thiếu/sai token.<br>`404`: session không tồn tại.<br>`403`: không có quyền thêm message vào session này.<br>`422`: body `ChatMessageCreate` không hợp lệ.<br>`500`: lỗi không kiểm soát khi insert message. |

### 11.3 Chatbots API (`/api/v1/chatbots`)

| Method | Path | Error statuses and trigger conditions |
|---|---|---|
| POST | `/api/v1/chatbots` | `401`: thiếu/sai token.<br>`403`: `PermissionError` từ service (vd không phải admin).<br>`400`: dữ liệu chatbot không hợp lệ (`ValueError`).<br>`422`: body `ChatbotCreate` không hợp lệ.<br>`500`: lỗi không kiểm soát khi tạo chatbot. |
| GET | `/api/v1/chatbots` | `401`: thiếu/sai token.<br>`500`: lỗi khi list chatbots theo role filter. |
| GET | `/api/v1/chatbots/{chatbot_id}` | `401`: thiếu/sai token.<br>`403`: không đủ quyền truy cập chatbot (`PermissionError`).<br>`404`: chatbot không tồn tại.<br>`500`: lỗi không kiểm soát khi lấy detail chatbot. |
| PATCH | `/api/v1/chatbots/{chatbot_id}` | `401`: thiếu/sai token.<br>`403`: không đủ quyền cập nhật.<br>`400`: payload/business rule invalid (`ValueError`).<br>`404`: chatbot không tồn tại.<br>`422`: body `ChatbotUpdate` không hợp lệ.<br>`500`: lỗi không kiểm soát khi update. |
| DELETE | `/api/v1/chatbots/{chatbot_id}` | `401`: thiếu/sai token.<br>`403`: không đủ quyền xóa.<br>`404`: chatbot không tồn tại (`success=False`).<br>`500`: lỗi không kiểm soát khi delete. |
| POST | `/api/v1/chatbots/{chatbot_id}/datasets` | `401`: thiếu/sai token.<br>`403`: không đủ quyền gán datasets.<br>`400`: input dataset IDs không hợp lệ (`ValueError`).<br>`422`: body `ChatbotAssignDatasetsRequest` không hợp lệ.<br>`500`: lỗi không kiểm soát khi assign datasets. |

## 12. Conventions (Core Chat-related)

### 12.1 Conventions used
- Service/repository naming is explicit (`*Service`, `*Repository`).
- FastAPI dependency wiring is centralized in `api/dependencies.py`.
- Mongo `_id` is serialized to `id` via base repository helpers.
- API versioning:
  - Core: `/api/v1/*`

### 12.2 Repeated design patterns
- Singleton-like global services for embedding/rerank/LLM/cache.
- Repository pattern for database IO.

## 13. Pitfalls (Core Chat-related)

### 13.1 Important technical debt / anti-patterns
- Core permission dependency is intentionally soft in places (`require_permission` logs warning and may allow) and has TODO for strict enforcement.

## 14. Quick Answer Index (Core Chat)

If you need to answer quickly:
- Token verification bridge from Core to Auth (payload now includes `department` for access checks): `airc_internal_chatbot_core/app/api/dependencies.py`.
- RAG internals: `airc_internal_chatbot_core/app/services/chat_service.py`.
- Frontend chat state orchestration: `src/stores/chatStore.ts`, `src/services/chatService.ts`.

# CODEBASE_CONTEXT - Core Ingest Domain

Last updated: 2026-05-28

This file contains extracted context related to ProcessingService, Worker, RQ jobs, and Qdrant ingest.

## 1. Project Overview (Core Ingest)

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

## 2. Directory Structure (Core Ingest extract)

```text
airc_internal_chatbot_core/
|- app/
|  |- api/
|  |  |- v1/                     # datasets, files endpoints
|  |- repositories/              # datasets/files/chunks data access
|  |- services/                  # dataset/chatbot processing logic
|  |- jobs/ingest.py             # RQ job entrypoint
|- worker.py                     # RQ worker process entrypoint
|- migrate/                      # core seeds
|- k8s/                          # Core + worker deployment manifests
```

## 3. Entry Points and Runtime (Core Ingest)

### 3.1 Backend entrypoints
- Core API entrypoint: `airc_internal_chatbot_core/app/main.py`
  - mounts `/api/v1/{chat,datasets,files,sessions,chatbots,stats}`
  - preloads embedding/rerank models and configures LLM service.
- Worker entrypoint: `airc_internal_chatbot_core/worker.py`
  - starts RQ worker on queue `ingest`.
- Job function: `airc_internal_chatbot_core/app/jobs/ingest.py`
  - resolves repos/services and runs `ProcessingService.process_dataset_file(...)`.

## 4. Core Modules / Components (Core Ingest)

### 4.1 DatasetService
- Path: `airc_internal_chatbot_core/app/services/dataset_service.py`
- Responsibility:
  - dataset lifecycle, dataset-file joins, sharing, cleanup (including vector index delete), chunk listing.
- Key signatures:

```python
class DatasetService:
    async def create_dataset(self, name: str, owner_id: str, visibility: str = "private", chatbot_ids: Optional[List[str]] = None) -> dict
    async def share_dataset(self, dataset_id: str, user_ids: List[str]) -> bool
    async def add_files_to_dataset(self, dataset_id: str, file_ids: List[str]) -> Dict[str, List]
    async def delete_dataset(self, dataset_id: str) -> bool
    async def toggle_dataset_file(self, dataset_file_id: str, is_enabled: bool) -> bool
```

- Depends on:
  - `DatasetRepository`, `DatasetFileRepository`, `FileRepository`, `ChunkRepository`, `vector_service`.
- Imported by:
  - DI in `app/api/dependencies.py`, routers in `app/api/v1/datasets.py`.

### 4.2 ProcessingService (ingest worker logic)
- Path: `airc_internal_chatbot_core/app/services/processing_service.py`
- Responsibility:
  - background file processing: read file -> extract text -> chunk -> embed -> save chunks -> upsert vectors -> status transitions.
- Key signatures:

```python
class ProcessingService:
    async def process_dataset_file(self, dataset_id: str, dataset_file_id: str)
```

- Depends on:
  - dataset file/file/chunk repositories, `chunking_service`, `embedding_service`, `vector_service`, `pypdf`, `python-docx`.
- Imported by:
  - `app/jobs/ingest.py`, DI for dataset router background operations.

## 5. Complete Function Signatures (Core Ingest)

### 5.1 ProcessingService (complete signatures)

```python
class ProcessingService:
    def __init__(
        self,
        dataset_file_repo: DatasetFileRepository,
        file_repo: FileRepository,
        chunk_repo: ChunkRepository
    )

    async def process_dataset_file(self, dataset_id: str, dataset_file_id: str)

    def _extract_text(self, content: bytes, filename: str) -> str

    def _extract_pdf(self, content: bytes) -> str

    def _extract_docx(self, content: bytes) -> str
```

| Signature | One-line description |
|---|---|
| `__init__(...)` | Inject repos cần thiết cho ingest lifecycle. |
| `process_dataset_file(...)` | Thực thi toàn bộ luồng xử lý một dataset_file và cập nhật trạng thái. |
| `_extract_text(...)` | Chọn extractor theo extension (`pdf/docx/txt`). |
| `_extract_pdf(...)` | Trích text toàn bộ pages từ dữ liệu PDF bytes. |
| `_extract_docx(...)` | Trích text từ các paragraph trong DOCX bytes. |

### 5.2 DatasetRepository (complete signatures)

```python
class DatasetRepository(BaseRepository):
    def __init__(self, db)

    async def create_dataset(
        self,
        name: str,
        owner_id: str,
        visibility: str = "private"
    ) -> dict

    async def get_by_id(self, dataset_id: str) -> Optional[dict]

    async def get_all(self) -> List[dict]

    async def get_by_owner(self, owner_id: str) -> List[dict]

    async def get_shared_with_user(self, user_id: str) -> List[dict]

    async def share_dataset(self, dataset_id: str, user_ids: List[str]) -> bool

    async def delete_dataset(self, dataset_id: str) -> bool

    async def update_dataset(self, dataset_id: str, data: dict) -> Optional[dict]
```

| Signature | One-line description |
|---|---|
| `__init__(...)` | Khởi tạo repository với collection `datasets`. |
| `create_dataset(...)` | Insert dataset mới với metadata cơ bản và `shared_with` rỗng. |
| `get_by_id(...)` | Truy vấn dataset theo ID và serialize `_id` sang `id`. |
| `get_all()` | Lấy toàn bộ datasets. |
| `get_by_owner(...)` | Lấy datasets theo `owner_id`. |
| `get_shared_with_user(...)` | Lấy datasets mà user nằm trong mảng `shared_with`. |
| `share_dataset(...)` | Replace danh sách `shared_with` của dataset. |
| `delete_dataset(...)` | Xóa dataset theo ID. |
| `update_dataset(...)` | Update dataset và trả về bản ghi mới sau khi cập nhật. |

### 5.3 FileRepository (complete signatures)

```python
class FileRepository(BaseRepository):
    def __init__(self, db)

    async def create_file(
        self,
        name: str,
        size: int,
        mime_type: str,
        path: str,
        status: FileStatus = FileStatus.PENDING
    ) -> dict

    async def get_by_id(self, file_id: str) -> Optional[dict]

    async def get_by_ids(self, file_ids: List[str]) -> List[dict]

    async def update_status(
        self,
        file_id: str,
        status: FileStatus,
        error: Optional[str] = None
    ) -> bool

    async def get_ready_files(self) -> List[dict]

    async def get_all(self) -> List[dict]
```

| Signature | One-line description |
|---|---|
| `__init__(...)` | Khởi tạo repository với collection `files`. |
| `create_file(...)` | Insert metadata cho file vừa upload. |
| `get_by_id(...)` | Truy vấn một file theo ID. |
| `get_by_ids(...)` | Truy vấn nhiều file theo danh sách IDs. |
| `update_status(...)` | Cập nhật trạng thái xử lý file, kèm thời điểm xử lý và lỗi (nếu có). |
| `get_ready_files()` | Lấy danh sách files có trạng thái `READY`. |
| `get_all()` | Lấy toàn bộ files theo thứ tự `uploaded_at` giảm dần. |

Lưu ý: `get_all(self) -> List[dict]` hiện được định nghĩa 2 lần giống hệt nhau trong file; Python sẽ dùng định nghĩa sau cùng.

## 6. Data Models and Schemas (Core Ingest)

### 6.1 Core-side entities

| Entity | Source | Fields (type) |
|---|---|---|
| Dataset (`datasets`) | `dataset_repository.py` | `name:str`, `owner_id:str`, `visibility:str`, `shared_with:list[str]`, `created_at:datetime` |
| File (`files`) | `file_repository.py` | `name:str`, `size:int`, `mime_type:str`, `path:str`, `status:str`, `uploaded_at:datetime`, `processed_at?:datetime`, `error?:str` |
| DatasetFile (`dataset_files`) | `dataset_file_repository.py` | `dataset_id:str`, `file_id:str`, `status:str`, `chunk_count:int`, `is_enabled:bool`, `created_at:datetime`, `processed_at?:datetime` |
| Chunk (`chunks`) | `chunk_repository.py` | `dataset_id:str`, `dataset_file_id:str`, `file_id:str`, `chunk_index:int`, `text:str`, `vector_id?:int` |

### 6.2 Vector store payload model
- Qdrant collection naming: `dataset_<dataset_id>`.
- Payload used in vector points:
  - `chunk_id`, `dataset_file_id`, `dataset_id`.

### 6.3 Key DTO schemas

| DTO | Source | Key fields |
|---|---|---|
| `ShareDatasetRequest` | same | `user_ids?`, `student_ids?` (legacy), `all_students` (legacy mode) |

## 7. API / Interface Contracts (Core Ingest)

### 7.1 Core API (`/api/v1`) - Datasets

| Method | Path | Input | Output | Side effects |
|---|---|---|---|---|
| GET | `/datasets/ping` | none | health payload | none |
| POST | `/datasets` | `DatasetCreate` | `DatasetResponse` | inserts dataset; optional chatbot assignment |
| GET | `/datasets` | none | `DatasetResponse[]` | role-filtered listing |
| GET | `/datasets/{dataset_id}` | path param | `DatasetResponse` | none |
| PATCH | `/datasets/{dataset_id}` | dataset payload | `DatasetResponse` | updates dataset metadata |
| DELETE | `/datasets/{dataset_id}` | path param | `SuccessResponse` | deletes dataset + dataset_files + chunks + Qdrant collection |
| POST | `/datasets/{dataset_id}/files` | `AddFilesToDatasetRequest` | `{status,added,skipped}` | inserts dataset_file records + enqueues ingest jobs |
| GET | `/datasets/{dataset_id}/files` | path param | `DatasetFileResponse[]` | none |
| PATCH | `/datasets/{dataset_id}/files/{dataset_file_id}` | toggle payload | `SuccessResponse` | updates `is_enabled` |
| DELETE | `/datasets/{dataset_id}/files/{dataset_file_id}` | path params | `SuccessResponse` | deletes dataset-file relation + related chunks |
| GET | `/datasets/{dataset_id}/files/{dataset_file_id}/chunks` | path params | `ChunkResponse[]` | none |
| PUT | `/datasets/{dataset_id}/files/{dataset_file_id}/toggle` | toggle payload | `SuccessResponse` | updates `is_enabled` |
| POST | `/datasets/{dataset_id}/share` | `ShareDatasetRequest` | `SuccessResponse` | replaces `shared_with` list |

### 7.2 Core API (`/api/v1`) - Files

| Method | Path | Input | Output | Side effects |
|---|---|---|---|---|
| POST | `/files/upload` | multipart file | `FileUploadResponse` | writes file to disk + inserts file metadata |
| GET | `/files/` | none | `FileResponse[]` | none |
| GET | `/files/{file_id}` | path param | `FileResponse` | none |
| GET | `/files/{file_id}/view` | path param | stream/attachment | reads file from disk |

## 8. Business Logic and Rules (Core Ingest)

### 8.1 Dataset and sharing rules
- Only `admin`/`employee` can create/upload/manage datasets/files.
- `employee` ownership checks enforced on many dataset mutating endpoints.
- `share_dataset` replaces `shared_with` with normalized deduplicated list.

### 8.2 Ingest algorithm (`ProcessingService.process_dataset_file`)
1. Load dataset_file + file metadata.
2. Status transitions: `chunking` -> `embedding` -> `done` or `error`.
3. Read local file path and extract text (`pdf/docx/txt`).
4. Chunk text using Vietnamese-oriented chunker.
5. Embed chunks.
6. Insert chunks in MongoDB.
7. Upsert vectors to Qdrant collection `dataset_<dataset_id>`.
8. Store chunk count and set `is_enabled=true`.

## 9. Configuration and Environment (Core Ingest)

### 9.1 Required env vars (Core)

| Variable | Required | Default / note |
|---|---|---|
| `MONGODB_URL` | yes | no default in settings |
| `MONGODB_DB_NAME` | no | `airc_chatbot` |
| `REDIS_URL` | no | `redis://localhost:6379/0` |
| `QDRANT_URL` | no | `http://qdrant:6333` |
| `MAX_UPLOAD_SIZE` | no | `209715200` |
| `DEBUG` | no | `False` |

## 10. Dependency Graph (Core Ingest)

### 10.1 Ingest path

```mermaid
graph LR
  UI --> AddFilesAPI[/api/v1/datasets/{id}/files]
  AddFilesAPI --> Queue[Redis RQ ingest queue]
  Queue --> Worker[worker.py]
  Worker --> IngestJob[app/jobs/ingest.py]
  IngestJob --> ProcessingService
  ProcessingService --> FileSystem[(uploads/)]
  ProcessingService --> ChunkRepo
  ProcessingService --> VectorSvc
  ChunkRepo --> Mongo[(MongoDB)]
  VectorSvc --> Qdrant[(Qdrant)]
```

## 11. Core API Error Contract (Core Ingest)

### 11.1 Datasets API (`/api/v1/datasets`)

| Method | Path | Error statuses and trigger conditions |
|---|---|---|
| GET | `/api/v1/datasets/ping` | Không có error contract explicit trong controller (chủ yếu trả `200`). |
| POST | `/api/v1/datasets` | `401`: thiếu/sai token.<br>`403`: role không thuộc `admin/employee`.<br>`400`: `ValueError` từ service (input/business validation).<br>`422`: body `DatasetCreate` không hợp lệ.<br>`500`: lỗi không kiểm soát khi tạo dataset. |
| GET | `/api/v1/datasets` | `401`: thiếu/sai token.<br>`500`: lỗi khi list datasets. |
| GET | `/api/v1/datasets/{dataset_id}` | `404`: không tìm thấy dataset.<br>`500`: lỗi không kiểm soát từ service/database. |
| PATCH | `/api/v1/datasets/{dataset_id}` | `401`: thiếu/sai token.<br>`404`: dataset không tồn tại.<br>`403`: không phải admin hoặc owner.<br>`422`: body update không hợp lệ.<br>`500`: cập nhật thất bại hoặc lỗi không kiểm soát. |
| DELETE | `/api/v1/datasets/{dataset_id}` | `401`: thiếu/sai token.<br>`404`: dataset không tồn tại (pre-check hoặc delete trả false).<br>`403`: không phải admin/owner.<br>`500`: lỗi không kiểm soát khi xóa. |
| POST | `/api/v1/datasets/{dataset_id}/files` | `401`: thiếu/sai token.<br>`403`: role không cho phép hoặc employee không phải owner.<br>`404`: dataset không tồn tại (owner check của employee).<br>`400`: `ValueError` từ service (file IDs/data invalid).<br>`422`: body `AddFilesToDatasetRequest` không hợp lệ.<br>`500`: lỗi enqueue/DB/service. |
| GET | `/api/v1/datasets/{dataset_id}/files` | `500`: lỗi không kiểm soát khi lấy danh sách file theo dataset. |
| PATCH | `/api/v1/datasets/{dataset_id}/files/{dataset_file_id}` | `400`: toggle thất bại (`success=False`).<br>`422`: body `ToggleDatasetFileRequest` không hợp lệ.<br>`500`: lỗi không kiểm soát khi cập nhật. |
| DELETE | `/api/v1/datasets/{dataset_id}/files/{dataset_file_id}` | `401`: thiếu/sai token.<br>`404`: dataset không tồn tại khi employee check owner.<br>`403`: employee không phải owner dataset.<br>`400`: remove thất bại (`success=False`).<br>`500`: lỗi không kiểm soát khi remove file. |
| GET | `/api/v1/datasets/{dataset_id}/files/{dataset_file_id}/chunks` | `500`: mọi lỗi trong quá trình lấy chunks đều bị catch và trả `500`. |
| PUT | `/api/v1/datasets/{dataset_id}/files/{dataset_file_id}/toggle` | `400`: toggle thất bại (`success=False`).<br>`422`: body `ToggleDatasetFileRequest` không hợp lệ.<br>`500`: lỗi runtime không kiểm soát. |
| POST | `/api/v1/datasets/{dataset_id}/share` | `401`: thiếu/sai token.<br>`403`: role không thuộc `admin/employee` hoặc employee không phải owner.<br>`404`: dataset không tồn tại.<br>`400`: thiếu `user_ids`/`student_ids` hợp lệ hoặc share operation fail.<br>`422`: body `ShareDatasetRequest` không hợp lệ.<br>`500`: lỗi không kiểm soát khi share. |

### 11.2 Files API (`/api/v1/files`)

| Method | Path | Error statuses and trigger conditions |
|---|---|---|
| POST | `/api/v1/files/upload` | `401`: thiếu/sai token.<br>`403`: role không thuộc `admin/employee`.<br>`400`: thiếu filename hoặc file quá giới hạn size.<br>`422`: multipart/form-data không hợp lệ (vd thiếu field `file`).<br>`500`: lỗi ghi file hoặc lưu metadata. |
| GET | `/api/v1/files/` | `401`: thiếu/sai token.<br>`500`: lỗi khi query danh sách files. |
| GET | `/api/v1/files/{file_id}` | `404`: file không tồn tại.<br>`500`: lỗi không kiểm soát khi query/serialize file. |
| GET | `/api/v1/files/{file_id}/view` | `404`: file metadata không tồn tại, thiếu path trong DB, hoặc file không tồn tại trên disk.<br>`500`: lỗi streaming/IO không kiểm soát. |

## 12. Conventions (Core Ingest-related)

### 12.1 Conventions used
- Service/repository naming is explicit (`*Service`, `*Repository`).
- FastAPI dependency wiring is centralized in `api/dependencies.py`.
- Mongo `_id` is serialized to `id` via base repository helpers.
- API versioning:
  - Core: `/api/v1/*`

### 12.2 Repeated design patterns
- Repository pattern for database IO.

## 13. Pitfalls (Core Ingest-related)

### 13.1 Important technical debt / anti-patterns
- Core permission dependency is intentionally soft in places (`require_permission` logs warning and may allow) and has TODO for strict enforcement.
- `airc_internal_chatbot_core/app/repositories/file_repository.py` defines `get_all` twice (duplicate method definition).

## 14. Quick Answer Index (Core Ingest)

If you need to answer quickly:
- Ingest/worker: `airc_internal_chatbot_core/app/jobs/ingest.py`, `worker.py`, `services/processing_service.py`.
- Dataset sharing rules: `airc_internal_chatbot_core/app/api/v1/datasets.py` + `dataset_service.py`.

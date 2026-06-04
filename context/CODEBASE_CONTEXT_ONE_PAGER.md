# AIRC Codebase One-Pager

Mục tiêu tài liệu này: giúp agent mới vào dự án nắm nhanh critical path và các pitfall có thể gây regression, không cần đọc toàn bộ source.

## 1) Dùng khi nào
- Dùng ngay đầu phiên để bootstrap context nhanh.
- Dùng khi task nhỏ-vừa: fix bug, thêm endpoint, sửa UI flow, chỉnh RBAC, sửa ingest/chat pipeline.
- Không thay thế tài liệu đầy đủ. Khi sửa lớn đa module, đọc thêm [CODEBASE_CONTEXT.md].

## 2) 30-Second Architecture
- Monorepo gồm 3 service chính:
  - Auth API: [airc_internal_chatbot_auth](airc_internal_chatbot_auth)
  - Core API + Worker: [airc_internal_chatbot_core](airc_internal_chatbot_core)
  - UI Next.js: [airc_internal_chatbot_ui](airc_internal_chatbot_ui)
- Runtime local qua [docker-compose.local.yml](docker-compose.local.yml): MongoDB + Redis + Qdrant + Auth + Core + Worker + UI.

## 3) Critical Path (phải hiểu trước khi sửa)

### A. Auth/RBAC path
1. UI gửi bearer token lên Auth/Core.
2. Core không tin token local, gọi Auth verify endpoint.
3. RBAC quyền đọc từ DB role/permission mappings.

File trọng tâm:
- [airc_internal_chatbot_auth/app/api/v1/auth.py](airc_internal_chatbot_auth/app/api/v1/auth.py)
- [airc_internal_chatbot_auth/app/api/v1/rbac.py](airc_internal_chatbot_auth/app/api/v1/rbac.py)
- [airc_internal_chatbot_auth/app/services/auth_service.py](airc_internal_chatbot_auth/app/services/auth_service.py)
- [airc_internal_chatbot_auth/app/services/rbac_service.py](airc_internal_chatbot_auth/app/services/rbac_service.py)
- [airc_internal_chatbot_core/app/api/dependencies.py](airc_internal_chatbot_core/app/api/dependencies.py)

### B. Chat RAG request path
1. UI gọi chat ask endpoint.
2. Core verify user qua Auth service.
3. ChatService chạy pipeline: embed -> cache -> retrieve -> rerank -> prompt -> Gemini -> save session/message.
4. Nếu có chatbot_id thì khóa context theo dataset_ids chatbot (ngăn dataset injection).

File trọng tâm:
- [airc_internal_chatbot_core/app/api/v1/chat.py](airc_internal_chatbot_core/app/api/v1/chat.py)
- [airc_internal_chatbot_core/app/services/chat_service.py](airc_internal_chatbot_core/app/services/chat_service.py)
- [airc_internal_chatbot_core/app/services/prompt_service.py](airc_internal_chatbot_core/app/services/prompt_service.py)
- [airc_internal_chatbot_core/app/services/llm_service.py](airc_internal_chatbot_core/app/services/llm_service.py)
- [airc_internal_chatbot_core/app/services/vector_service.py](airc_internal_chatbot_core/app/services/vector_service.py)

### C. Ingest path (upload -> worker)
1. UI upload file lên Core.
2. Dataset API add file vào dataset và enqueue ingest job Redis/RQ.
3. Worker đọc job, extract/chunk/embed, lưu chunk Mongo, upsert vector Qdrant.

File trọng tâm:
- [airc_internal_chatbot_core/app/api/v1/files.py](airc_internal_chatbot_core/app/api/v1/files.py)
- [airc_internal_chatbot_core/app/api/v1/datasets.py](airc_internal_chatbot_core/app/api/v1/datasets.py)
- [airc_internal_chatbot_core/app/jobs/ingest.py](airc_internal_chatbot_core/app/jobs/ingest.py)
- [airc_internal_chatbot_core/worker.py](airc_internal_chatbot_core/worker.py)
- [airc_internal_chatbot_core/app/services/processing_service.py](airc_internal_chatbot_core/app/services/processing_service.py)

### D. UI state path
1. Auth state ở Zustand, token lưu cookie + localStorage.
2. Axios interceptor attach token và xử lý 401 redirect login.
3. Chat state giữ session/messages/dataset/chatbot context.

File trọng tâm:
- [airc_internal_chatbot_ui/src/stores/authStore.ts](airc_internal_chatbot_ui/src/stores/authStore.ts)
- [airc_internal_chatbot_ui/src/stores/chatStore.ts](airc_internal_chatbot_ui/src/stores/chatStore.ts)
- [airc_internal_chatbot_ui/src/infrastructure/http/interceptors.ts](airc_internal_chatbot_ui/src/infrastructure/http/interceptors.ts)
- [airc_internal_chatbot_ui/src/components/Auth/AuthGuard.tsx](airc_internal_chatbot_ui/src/components/Auth/AuthGuard.tsx)

## 4) Pitfalls (đọc trước khi sửa)

### P0: Permission check Core chưa strict hoàn toàn
- Ở Core dependency, một số nhánh đang soft-check (log warning thay vì deny cứng).
- Rủi ro: tưởng đã chặn quyền nhưng thực tế vẫn cho qua.
- File: [airc_internal_chatbot_core/app/api/dependencies.py](airc_internal_chatbot_core/app/api/dependencies.py)

### P0: Context locking chatbot là lớp bảo vệ quan trọng
- Không bỏ logic override dataset_ids theo chatbot nếu chưa thay bằng cơ chế bảo vệ tương đương.
- File: [airc_internal_chatbot_core/app/services/chat_service.py](airc_internal_chatbot_core/app/services/chat_service.py)

### P1: Share dataset là replace semantics, không merge
- API share hiện set lại toàn bộ shared_with theo payload mới.
- File: [airc_internal_chatbot_core/app/repositories/dataset_repository.py](airc_internal_chatbot_core/app/repositories/dataset_repository.py)

### P1: UI build bỏ qua TS errors
- next config đang ignore build errors, dễ che lỗi kiểu dữ liệu.
- File: [airc_internal_chatbot_ui/next.config.ts](airc_internal_chatbot_ui/next.config.ts)

### P1: Stats endpoint có số liệu heuristic/default
- Không xem đây là metric production-grade.
- File: [airc_internal_chatbot_core/app/api/v1/stats.py](airc_internal_chatbot_core/app/api/v1/stats.py)

### P1: K8s infra đang có debt cấu hình
- Kustomization tham chiếu secrets file chưa có.
- Cloudflared deployment chứa token hardcoded.
- Managed certificate domain chưa đồng bộ ingress host.
- Files:
  - [k8s-infrastructure/kustomization.yaml](k8s-infrastructure/kustomization.yaml)
  - [k8s-infrastructure/cloudflared/deployment.yaml](k8s-infrastructure/cloudflared/deployment.yaml)
  - [k8s-infrastructure/ingress/ingress.yaml](k8s-infrastructure/ingress/ingress.yaml)
  - [k8s-infrastructure/ingress/managed-certificate.yaml](k8s-infrastructure/ingress/managed-certificate.yaml)

## 5) Quick file map theo nhu cầu
- Sửa login/register/verify: [airc_internal_chatbot_auth/app/api/v1/auth.py](airc_internal_chatbot_auth/app/api/v1/auth.py)
- Sửa RBAC matrix, assign role/perm: [airc_internal_chatbot_auth/app/api/v1/rbac.py](airc_internal_chatbot_auth/app/api/v1/rbac.py)
- Sửa chat pipeline, cache, rerank: [airc_internal_chatbot_core/app/services/chat_service.py](airc_internal_chatbot_core/app/services/chat_service.py)
- Sửa upload/ingest: [airc_internal_chatbot_core/app/services/processing_service.py](airc_internal_chatbot_core/app/services/processing_service.py)
- Sửa share dataset: [airc_internal_chatbot_core/app/api/v1/datasets.py](airc_internal_chatbot_core/app/api/v1/datasets.py)
- Sửa UI role-user page: [airc_internal_chatbot_ui/src/app/admin/users/[id]/roles/page.tsx](airc_internal_chatbot_ui/src/app/admin/users/[id]/roles/page.tsx)
- Sửa Share modal UI: [airc_internal_chatbot_ui/src/components/Datasets/ShareDatasetModal.tsx](airc_internal_chatbot_ui/src/components/Datasets/ShareDatasetModal.tsx)

## 6) Prompt khởi tạo agent mẫu (copy dùng ngay)

Bạn đang làm việc trên AIRC Internal Chatbot monorepo gồm Auth, Core, UI.
Mục tiêu phiên này: <ghi mục tiêu cụ thể>.

Bắt buộc giữ các invariants sau:
1. Core phải verify token qua Auth service.
2. Không phá context locking theo chatbot dataset_ids nếu chưa có cơ chế thay thế an toàn.
3. Khi đổi API contract, cập nhật đồng bộ backend router + UI service/store + docs liên quan.
4. Không dùng destructive git commands.

Trước khi sửa code:
1. Xác định file critical path cần chạm.
2. Nêu các pitfall liên quan thay đổi.
3. Chỉ chỉnh tối thiểu cần thiết, tránh refactor lan rộng.

Sau khi sửa:
1. Kiểm tra lỗi type/lint/test trong phạm vi thay đổi.
2. Tóm tắt thay đổi theo file và rủi ro còn lại.

## 7) Khi nào mở tài liệu đầy đủ
- Khi thay đổi liên service lớn.
- Khi cần đầy đủ schema/API matrix.
- Khi xử lý deploy/infra phức tạp.

Tham chiếu: [CODEBASE_CONTEXT.md]

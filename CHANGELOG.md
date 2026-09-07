# Changelog

Chỉ ghi thay đổi và bug. Trạng thái: `Đã làm` · `Đã sửa` · `Chưa sửa`

---

## Chưa commit

### Thay đổi

| Mục | Trạng thái |
|-----|------------|
| Live Voice Mode: STT (Web Speech) + TTS (Edge-TTS), modal live trên dashboard và student chat | Đã làm |
| API `POST /api/v1/voice/tts` (voice allowlist, stream MP3, không log nội dung user) | Đã làm |
| Hiện nguồn (citation) dưới câu trả lời; click mở file gốc; lưu sources khi reload session | Đã làm |
| Streaming SSE `POST /api/v1/chat/ask/stream`; UI render token dần | Đã làm |
| Feedback 👍👎 (`POST /api/v1/chat/feedback`); dashboard lấy accuracy/latency thật | Đã làm |
| Share dataset chọn từng sinh viên; `all_students` dùng `shared_with: ["*"]` | Đã làm |
| Forgot/reset password (token SHA-256, SMTP optional, UI `/auth/forgot-password`) | Đã làm |
| Gán role user thật: `GET /users/{id}`, `PUT /rbac/users/{id}/roles` + UI admin | Đã làm |
| CORS Core/Auth: origin allowlist, không còn `*` + credentials | Đã làm |
| K8s: Cloudflared token qua Secret; kustomize secretGenerator; cert = `ragairc.neovort.shop` | Đã làm |
| Tắt `ignoreBuildErrors` trên Next.js | Đã làm |
| Gộp transcript chat (ChatTranscript + useChatBranches) | Đã làm |
| `search_mode` / `similarity_threshold` chạy thật (RRF hybrid) | Đã làm |
| Gợi ý câu hỏi, xuất Markdown, drawer kiểm chứng nguồn, góp ý khi 👎 | Đã làm |
| Jenkins Core thêm stage Test | Đã làm |
| API không preload embedding/rerank (PRELOAD_MODELS); worker mới preload | Đã làm |

### Bug

| Mục | Trạng thái |
|-----|------------|
| Tắt mic rồi bot nói xong vẫn tự bật nghe lại | Đã sửa |
| Pause lúc đang tải câu TTS tiếp theo vẫn phát tiếp | Đã sửa |
| VAD 1s chỉ gửi text final, mất từ interim cuối câu | Đã sửa |
| Đóng modal lúc `audioCtx.resume()` leak mic / AudioContext | Đã sửa |
| Dashboard mở Live khi chưa chọn chatbot; gửi fail thì live im lặng | Đã sửa |
| Hướng dẫn mic hardcode `localhost:3000` | Đã sửa |
| Lỗi STT `network` / `audio-capture` restart vòng, không báo UI | Đã sửa |
| Live modal re-render ~60fps vì `setMicAudioLevel` mỗi frame | Đã sửa |
| Enter từ overlay lọt xuống ô chat phía sau; không đóng bằng Escape | Đã sửa |
| Core `require_permission` chỉ log warning, không chặn 403 | Đã sửa |
| Dashboard `accuracy_rate=89%` và `avg_response_time=1.2s` hardcode | Đã sửa |
| Share “all students” không ghi student nào; UI chọn SV cụ thể chưa làm | Đã sửa |
| Forgot-password là endpoint giả; trang gán role user dùng mock | Đã sửa |
| TTS không prefetch câu sau → ngắt quãng giữa các câu | Chưa sửa |
| Chưa ghi trên UI là STT đi Google, TTS đi Microsoft | Chưa sửa |
| `ChatInput.onOpenLiveVoice` không được dùng (dead code) | Chưa sửa |
| CORS `allow_origins=["*"]` + credentials; token Cloudflared hardcode; cert lệch ingress | Đã sửa |
| `_search_dataset` query file N+1 | Đã sửa |
| Reformulation/compression mặc định bật (thêm 1–2 lần LLM) | Đã sửa |
| Dashboard stats không auth | Đã sửa |
| UI tiếng Việt không dấu (ChatInput, DatasetTable, form admin) | Đã sửa |
| `search_mode` / threshold chỉ nằm trên form, retrieval luôn vector+regex | Đã sửa |

---

## `feature/rag-processing-improvements`

### Thay đổi

| Mục | Trạng thái |
|-----|------------|
| Parse tài liệu bằng Docling (PDF/DOCX/HTML, OCR) | Đã làm |
| Chunking layout-aware, parent-child, gộp chunk ngắn, overlap thông minh | Đã làm |
| Document profiling, section parsing, enrich context bằng tóm tắt / header bảng | Đã làm |
| Nén lịch sử hội thoại (incremental buffer) và reformulation câu hỏi | Đã làm |
| Upload nhiều file song song | Đã làm |
| Admin UI tiếng Việt; hỗ trợ chọn LLM local / OpenAI-compatible | Đã làm |
| Chat render Markdown, LaTeX, sơ đồ Mermaid | Đã làm |

### Bug

| Mục | Trạng thái |
|-----|------------|
| Chữ Việt không dấu trên admin (users, roles, permissions, datasets) | Đã sửa |

---

## Trước đó

### Thay đổi

| Mục | Trạng thái |
|-----|------------|
| Auth/RBAC, chia sẻ dataset, lọc user theo role | Đã làm |
| UI bỏ mock role, nối API thật | Đã làm |
| Seed, docker-compose, cấu hình môi trường local/dev | Đã làm |

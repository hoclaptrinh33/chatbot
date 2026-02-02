# AIRC Internal Chatbot (Project Master)

Dự án AIRC Internal Chatbot là hệ thống tích hợp RAG (Retrieval-Augmented Generation) để hỗ trợ tra cứu thông tin nội bộ, được chia thành 3 microservices chính.

**🌐 Production Deployment:** https://ragairc.neovort.shop

---

## 📚 Quick Links

- **[Complete Deploy Guide](DEPLOY_GUIDE_SIMPLE.md)** - Hướng dẫn deploy lên GKE chi tiết
- **[Quick Reference](QUICK_REFERENCE.md)** - Lệnh nhanh và troubleshooting
- **[Original Deploy Guide](DEPLOY_TO_GKE.md)** - Tài liệu deploy đầy đủ (legacy)

---

## 🚀 Production Status (GKE)

**Cluster:** rag-gke (2 nodes x e2-standard-4)  
**Domain:** ragairc.neovort.shop  
**Status:** ✅ All services running

| Service | Pods | CPU Usage | RAM Usage | Status     |
| ------- | ---- | --------- | --------- | ---------- |
| Core    | 1/1  | 13m       | 2235Mi    | ✅ Running |
| Auth    | 1/1  | 12m       | 222Mi     | ✅ Running |
| Worker  | 1/1  | 1m        | 559Mi     | ✅ Running |
| UI      | 1/1  | 2m        | 38Mi      | ✅ Running |
| MongoDB | 1/1  | 7m        | 68Mi      | ✅ Running |
| Redis   | 1/1  | 7m        | 3Mi       | ✅ Running |
| Qdrant  | 1/1  | 1m        | 14Mi      | ✅ Running |

**Total:** 43m CPU / 3.1GB RAM (Cluster: 8 vCPU / 32GB)

---

## 1. Kiến trúc Tổng quan (System Architecture)

Dự án được triển khai theo mô hình Microservices, được đóng gói và kết nối bằng Docker Compose.

```
airc_internal_chatbot_v1/         # ROOT DIRECTORY
├── docker-compose.yml            # Orchestration Config (Start All)
├── README.md                     # Master Documentation
│
├── airc_internal_chatbot_auth/   # [Service 8001] Authentication & RBAC
│   ├── app/                      # Source Code
│   ├── .env.example              # Config Sample
│   └── Dockerfile                # Build Instruction
│
├── airc_internal_chatbot_core/   # [Service 8000] RAG, LLM & File Processing
│   ├── app/                      # Source Code
│   ├── .env.example              # Config Sample
│   └── Dockerfile                # Build Instruction
│
└── airc_internal_chatbot_ui/     # [Service 3000] Frontend Interface
    ├── src/                      # Source Code
    ├── .env.example              # Config Sample
    └── Dockerfile                # Build Instruction
```

---

## 2. Hướng dẫn Triển khai (Deployment Guide)

### Cách 1: Chạy Monorepo (Khuyên dùng)

Nếu bạn có toàn bộ source code trong thư mục cha `airc_internal_chatbot_v1` như cấu trúc trên.

1.  **Cấu hình Environment:**
    - Vào từng thư mục con (`auth`, `core`, `ui`), copy file `.env.example` thành `.env` (hoặc `.env.local` cho UI).
    - Cập nhật các secret keys nếu cần.

2.  **Khởi động hệ thống:**
    Tại thư mục Root, chạy lệnh:

    ```bash
    docker-compose up -d --build
    ```

3.  **Truy cập:**
    - Frontend: `http://localhost:3000`
    - Auth API: `http://localhost:8001/docs`
    - Core API: `http://localhost:8000/docs`

### Cách 2: Chạy từ Source Code Rời rạc (Distributed Repos)

Nếu người dùng tải 3 services từ 3 git repository khác nhau về máy. Để chạy được bằng `docker-compose`, họ cần làm như sau:

**Bước 1: Chuẩn bị Thư mục**
Tạo một thư mục cha (ví dụ `AIRC_System`) và đặt 3 projects con nằm cùng cấp với nhau:

```
AIRC_System/
├── airc_internal_chatbot_auth/   <-- Git Clone Auth
├── airc_internal_chatbot_core/   <-- Git Clone Core
├── airc_internal_chatbot_ui/     <-- Git Clone UI
└── docker-compose.yml            <-- Cần file này!
```

**Bước 2: Tải file Orchestration**
Người dùng **BẮT BUỘC** phải có file `docker-compose.yml` đặt ở thư mục cha. File này định nghĩa việc build và kết nối mạng giữa 3 services.

**Bước 3: Chạy lệnh**
Tại thư mục `AIRC_System`, chạy lệnh tương tự:

```bash
docker-compose up -d --build
```

---

### Cách 3: Chạy thủ công từng Dockerfile (Dành cho chuyên gia)

**Câu hỏi:** _Nếu tôi chỉ tải 3 source code và chạy `docker build/run` từng cái thì có chạy được không?_
**Trả lời:** Không chạy ngay được. Bạn sẽ **THIẾU 3 thành phần cốt lõi** mà Docker Compose tự động xử lý giúp bạn:

1.  **Docker Network (Mạng nội bộ):**
    - Các container mặc định bị cô lập, không thể gọi nhau bằng tên (ví dụ: Core không thể gọi `http://auth_service` được).
    - **Giải pháp:** Phải tự tạo mạng: `docker network create airc-network`.

2.  **Infrastructure (Cơ sở hạ tầng):**
    - Docker Compose tự bật MongoDB, Redis, Qdrant. Nếu chạy thủ công, bạn phải tự cài và chạy các services này trước.
    - **Giải pháp:** Phải tự chạy MongoDB, Redis, Qdrant và join vào network trên.

3.  **Environment Variables (Kết nối):**
    - Bạn phải sửa file `.env` để trỏ đúng IP hoặc Hostname của các container trên (không dùng `localhost` được vì localhost trong container là chính nó).

#### Hướng dẫn chạy thủ công (Manual Workflow):

Nếu bắt buộc phải chạy rời, hãy làm theo thứ tự:

1.  **Tạo mạng:**

    ```bash
    docker network create airc-net
    ```

2.  **Chạy Database (Bắt buộc):**

    ```bash
    docker run -d --name mongo --net airc-net mongo:latest
    docker run -d --name redis --net airc-net redis:alpine
    docker run -d --name qdrant --net airc-net qdrant/qdrant
    ```

3.  **Chạy Apps (Kèm env):**

    ```bash
    # Auth Service
    docker run -d --name auth_service --net airc-net --env MONGODB_URL="mongodb://mongo:27017" airc-auth-service

    # Core Service
    docker run -d --name core_service --net airc-net --env AUTH_SERVICE_URL="http://auth_service:8001" airc-core-service

    # UI Service
    docker run -d -p 3000:3000 --name ui_service --net airc-net airc-ui-service
    ```

---

## 3. Tech Stack

| Service  | Technology       | Port | DB / Components                                              |
| :------- | :--------------- | :--- | :----------------------------------------------------------- |
| **Auth** | Python (FastAPI) | 8001 | MongoDB (Users, Roles)                                       |
| **Core** | Python (FastAPI) | 8000 | MongoDB (Chat), Qdrant (Vector), Redis (Queue), Gemini (LLM) |
| **UI**   | Next.js (React)  | 3000 | Zustand, Ant Design, Axios                                   |

## 4. Environment Variables (Tóm tắt)

Để kết nối 3 services, cần đảm bảo config URL trỏ đúng vào nhau:

- **Core Service (`.env`):**

  ```properties
  AUTH_SERVICE_URL=http://airc_auth_service:8001
  REDIS_URL=redis://airc_redis:6379/0
  QDRANT_URL=http://airc_qdrant:6333
  ```

  _(Lưu ý: Trong Docker, dùng tên service `airc_auth_service` thay vì localhost)_

- **UI Service (build args hoặc `.env.local`):**
  ```properties
  NEXT_PUBLIC_AUTH_API=http://localhost:8001/api/auth
  NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
  NEXT_PUBLIC_APP_URL=http://localhost:3000
  ```
  _(Lưu ý: UI chạy ở browser client nên vẫn gọi API qua localhost)_

---

## 5. API Documentation

### Auth Service (Port 8001)

| Method | Endpoint                | Description             |
| ------ | ----------------------- | ----------------------- |
| POST   | `/api/auth/register`    | Đăng ký user mới        |
| POST   | `/api/auth/login`       | Đăng nhập               |
| GET    | `/api/auth/me`          | Thông tin user hiện tại |
| GET    | `/api/rbac/roles`       | Danh sách roles         |
| GET    | `/api/rbac/permissions` | Danh sách permissions   |
| GET    | `/api/rbac/users`       | Danh sách users (Admin) |

### Core Service (Port 8000)

| Method | Endpoint                        | Description                                |
| ------ | ------------------------------- | ------------------------------------------ |
| GET    | `/api/v1/chatbots`              | Danh sách chatbots                         |
| POST   | `/api/v1/chatbots`              | Tạo chatbot mới                            |
| GET    | `/api/v1/datasets`              | Danh sách datasets                         |
| POST   | `/api/v1/datasets`              | Tạo dataset mới                            |
| POST   | `/api/v1/files/upload`          | Upload file                                |
| GET    | `/api/v1/files/{id}/view`       | Xem file (PDF/Image inline, DOCX download) |
| POST   | `/api/v1/chat`                  | Gửi tin nhắn chat                          |
| GET    | `/api/v1/sessions`              | Lịch sử chat sessions                      |
| GET    | `/api/v1/stats/dashboard`       | Dashboard statistics                       |
| GET    | `/api/v1/stats/recent-activity` | Recent activity                            |

---

## 6. Roles & Permissions (RBAC)

| Role        | Permissions                                         |
| ----------- | --------------------------------------------------- |
| **admin**   | Full access: users, roles, chatbots, datasets, chat |
| **teacher** | Manage datasets, view chatbots, chat                |
| **student** | Chat only (chatbots có `allowed_roles` phù hợp)     |

---

## 7. Quick Commands

### Local Development

```bash
# Start all services
docker-compose -f docker-compose.local.yml up -d --build

# View logs
docker-compose -f docker-compose.local.yml logs -f

# Stop all
docker-compose -f docker-compose.local.yml down
```

### Production (GKE)

```bash
# Check pods
kubectl get pods -n airc-chatbot

# View logs
kubectl logs -f deployment/core-service -n airc-chatbot

# Restart deployments
kubectl rollout restart deployment -n airc-chatbot

# Access MongoDB shell
kubectl exec -it deployment/mongodb -n airc-chatbot -- mongosh
```

---

## 📝 License

MIT License - AIRC Team 2024-2026

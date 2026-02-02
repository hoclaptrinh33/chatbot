# AIRC Core Service

Dịch vụ xử lý chính (Core Business) của hệ thống AIRC Internal Chatbot, chịu trách nhiệm xử lý logic RAG (Retrieval-Augmented Generation), quản lý Workspaces, Datasets, tích hợp LLM (Gemini) và Vector Database.

## 1. Kiến trúc & Design Pattern
Dự án chia sẻ kiến trúc tương tự Auth Service, áp dụng **Clean Architecture** để đảm bảo tính mở rộng và độc lập.

### Cấu trúc thư mục:
```
airc_internal_chatbot_core/
├── app/
│   ├── api/          # Endpoints (Chat, Files)
│   ├── core/         # LLM Config & Factories
│   ├── models/       # Data Structures
│   ├── repositories/ # Vector DB & Mongo Access
│   ├── services/     # RAG & LLM Logic
│   ├── workers/      # Background Tasks (Arq)
│   └── main.py       # Entry Point
├── .env.example      # Environment template
├── Dockerfile        # Container config
├── README.md         # Documentation
└── requirements.txt  # Python dependencies
```

### Design Patterns sử dụng:
- **Factory Pattern**: Khởi tạo các instance LLM/Embeddings khác nhau.
- **Strategy Pattern**: Xử lý các định dạng file khác nhau (PDF, Docx, TXT).
- **Observer/Event-driven**: Sử dụng Redis để xử lý asynchronous tasks (upload & process file).

## 2. Cài đặt & Chạy (Môi trường Dev)

### Yêu cầu:
- Python 3.10+
- MongoDB
- Redis (cho background jobs)

### Bước 1: Sao chép cấu hình
Copy file `.env.example` thành `.env` và điền key:
```bash
cp .env.example .env
```

### Bước 2: Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### Bước 3: Chạy ứng dụng
```bash
uvicorn app.main:app --reload --port 8000
```
Service sẽ chạy tại: `http://localhost:8000`

## 3. Chạy bằng Docker

### Bước 1: Build Image
```bash
docker build -t airc-core-service .
```

### Bước 2: Run Container
```bash
docker run -d -p 8000:8000 --env-file .env airc-core-service
```

## 4. Luồng hoạt động (System Flow)
1. **Receive Request**: Nhận API request từ Frontend (kèm JWT Token).
2. **Access Control**: Verify Token và Check Permissions (thông qua Auth Service hoặc decode logic).
3. **Process**:
    - **Chat**: Retrieve documents -> Context -> Gemini LLM -> Response.
    - **Ingest**: Upload file -> Redis Task -> Extract Text -> Vector Embedding -> Vector DB.

# AIRC Auth Service

Dịch vụ xác thực và quản lý người dùng tập trung cho hệ thống AIRC Internal Chatbot, chịu trách nhiệm xử lý đăng ký, đăng nhập, JWT token và Phân quyền (RBAC).

## 1. Kiến trúc & Design Pattern
Dự án áp dụng **Layered Architecture (Kiến trúc phân lớp)** kết hợp với **Repository Pattern** để tách biệt logic nghiệp vụ và truy xuất dữ liệu.

### Cấu trúc thư mục:
```
airc_internal_chatbot_auth/
├── app/
│   ├── api/          # Controllers & Endpoints
│   ├── core/         # Settings & Security config
│   ├── models/       # Pydantic & DB Models
│   ├── repositories/ # DAL (Data Access Layer)
│   ├── services/     # Business Logic (Auth, RBAC)
│   └── main.py       # App Entry Point
├── migrate/          # Auto-seeding scripts
├── .env.example      # Environment template
├── Dockerfile        # Container config
├── README.md         # Documentation
└── requirements.txt  # Python dependencies
```

### Design Patterns sử dụng:
- **Repository Pattern**: Ẩn giấu chi tiết triển khai database, giúp code dễ test và bảo trì.
- **Dependency Injection**: Sử dụng FastAPI Depends để tiêm các dependencies (Service, Repository) vào Controller.
- **Singleton Pattern**: Áp dụng cho Database Connection và Settings.

## 2. Cài đặt & Chạy (Môi trường Dev)

### Yêu cầu:
- Python 3.10+
- MongoDB (đang chạy ở port 27017)

### Bước 1: Sao chép cấu hình
Copy file `.env.example` thành `.env` và cập nhật thông số nếu cần:
```bash
cp .env.example .env
```
*Lưu ý: `JWT_SECRET_KEY` cần được bảo mật và đồng bộ với Core Service.*

### Bước 2: Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### Bước 3: Chạy ứng dụng
```bash
uvicorn app.main:app --reload --port 8001
```
Service sẽ chạy tại: `http://localhost:8001`
Docs API: `http://localhost:8001/docs`

## 3. Chạy bằng Docker

### Bước 1: Build Image
```bash
docker build -t airc-auth-service .
```

### Bước 2: Run Container
```bash
docker run -d -p 8001:8001 --env-file .env airc-auth-service
```

## 4. Luồng hoạt động (System Flow)
1. **User Login**: Frontend gửi credentials -> Auth Service.
2. **Issue Token**: Auth Service verify -> Trả về JWT Token (bao gồm thông tin Role).
3. **Verify Token**: Core Service nhận request từ User -> Gọi Auth Service (hoặc dùng Secret Key) để xác thực Token.
4. **RBAC**: Quản lý Permissions và Roles cho toàn bộ hệ thống.

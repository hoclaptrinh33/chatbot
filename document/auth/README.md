# 🔐 Auth Service - Tài liệu Chi tiết API

> **Service**: airc_internal_chatbot_auth  
> **Port**: 8001  
> **Framework**: FastAPI  
> **Database**: MongoDB (airc_auth_db)

---

## 📑 Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Endpoints đăng ký](#2-endpoints-đăng-ký)
3. [Endpoints đăng nhập](#3-endpoints-đăng-nhập)
4. [Endpoints xác thực token](#4-endpoints-xác-thực-token)
5. [Endpoints lấy thông tin user](#5-endpoints-lấy-thông-tin-user)
6. [Cơ chế bảo mật](#6-cơ-chế-bảo-mật)
7. [Cấu trúc JWT Token](#7-cấu-trúc-jwt-token)

---

## 1. Tổng quan

Auth Service chịu trách nhiệm quản lý **xác thực (Authentication)** cho toàn bộ hệ thống AIRC Chatbot.

### Chức năng chính:

- ✅ Đăng ký user mới
- ✅ Đăng nhập và cấp JWT token
- ✅ Xác thực token cho các service khác (Core Service)
- ✅ Quản lý thông tin user
- ✅ Rate limiting chống brute force
- ✅ Input validation bảo mật

### Base URL

```
http://localhost:8001/api/auth
```

### Collections MongoDB

| Collection         | Mô tả                                            |
| ------------------ | ------------------------------------------------ |
| `users`            | Thông tin user (email, password hash, full_name) |
| `roles`            | Danh sách roles (admin, teacher, student)        |
| `user_roles`       | Mapping user → role                              |
| `permissions`      | Danh sách permissions                            |
| `role_permissions` | Mapping role → permission                        |

---

## 2. Endpoints đăng ký

### `POST /api/auth/register`

Đăng ký tài khoản mới. User mới mặc định có role **student**.

#### Request Body

```json
{
  "email": "user@example.com",
  "password": "SecureP@ss123",
  "full_name": "Nguyễn Văn A"
}
```

#### Validation Rules

| Field       | Yêu cầu                                         |
| ----------- | ----------------------------------------------- |
| `email`     | Định dạng email hợp lệ, chưa được đăng ký       |
| `password`  | Tối thiểu 8 ký tự, có chữ hoa + chữ thường + số |
| `full_name` | 2-100 ký tự, chỉ chữ cái và khoảng trắng        |

#### Response thành công (201)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Response lỗi

| Code  | Mô tả                                  |
| ----- | -------------------------------------- |
| `400` | Email đã tồn tại / Validation thất bại |
| `500` | Lỗi hệ thống                           |

#### Ví dụ lỗi

```json
{
  "detail": "Email này đã được đăng ký. Vui lòng sử dụng email khác hoặc đăng nhập."
}
```

#### Luồng xử lý bên trong

```
1. InputValidator.validate_email()      → Kiểm tra định dạng email
2. InputValidator.validate_password()   → Kiểm tra độ mạnh password
3. InputValidator.validate_name()       → Kiểm tra tên hợp lệ
4. InputValidator.sanitize_string()     → Làm sạch input (XSS prevention)
5. user_repo.email_exists()             → Kiểm tra email đã tồn tại chưa
6. pbkdf2_sha256.hash()                 → Hash password
7. user_repo.create_user()              → Tạo user trong MongoDB
8. jwt_service.create_access_token()    → Tạo JWT token
9. Return token
```

---

## 3. Endpoints đăng nhập

### `POST /api/auth/login`

Đăng nhập với email và password. Có bảo vệ chống brute force.

#### Request Body

```json
{
  "email": "user@example.com",
  "password": "SecureP@ss123"
}
```

#### Response thành công (200)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Response lỗi

| Code  | Mô tả                                                  |
| ----- | ------------------------------------------------------ |
| `400` | Email format không hợp lệ                              |
| `401` | Email không tồn tại / Password sai / Tài khoản bị khóa |
| `429` | Quá nhiều lần thử (Rate limited)                       |
| `500` | Lỗi hệ thống                                           |

#### Ví dụ các lỗi 401

```json
// Email không tồn tại
{"detail": "Email không tồn tại trong hệ thống"}

// Password sai
{"detail": "Mật khẩu không chính xác"}

// Tài khoản bị vô hiệu hóa
{"detail": "Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên."}
```

#### Ví dụ lỗi 429 (Rate Limit)

```json
{
  "detail": "Quá nhiều lần đăng nhập thất bại. Vui lòng thử lại sau 300 giây."
}
```

#### Luồng xử lý bên trong

```
1. rate_limiter.is_blocked()            → Kiểm tra IP bị block chưa
2. InputValidator.validate_email()      → Validate email format
3. user_repo.get_by_email()             → Tìm user trong DB
4. pbkdf2_sha256.verify()               → So sánh password
5. user.is_active                       → Kiểm tra tài khoản còn active
6. _get_user_role()                     → Lấy role từ user_roles collection
7. rate_limiter.reset_failed_logins()   → Reset counter nếu login thành công
8. jwt_service.create_access_token()    → Tạo JWT token với user_id, email, role
9. Return token
```

---

## 4. Endpoints xác thực token

### `POST /api/auth/verify`

**⚠️ Endpoint nội bộ**: Dùng cho Core Service xác thực token của user.

#### Request Body

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Response thành công (200)

```json
{
  "id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "role": "teacher",
  "is_active": true
}
```

#### Response lỗi

| Code  | Mô tả                                             |
| ----- | ------------------------------------------------- |
| `401` | Token không hợp lệ / hết hạn / user không tồn tại |

#### Luồng xử lý bên trong

```
1. payload.get("token")              → Lấy token từ request body
2. jwt_service.verify_token()        → Decode và validate JWT
3. user_repo.get_by_id()             → Tìm user theo user_id trong token
4. Kiểm tra is_active                → User còn active không
5. _get_user_role()                  → Lấy role mới nhất từ DB
6. Return user info
```

#### Cách Core Service sử dụng

```python
# Core Service gọi Auth Service để verify token
async def verify_token_with_auth_service(token: str) -> User:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AUTH_SERVICE_URL}/api/auth/verify",
            json={"token": token},  # ← Token trong body, không phải header!
            timeout=5.0
        )

        if response.status_code != 200:
            raise HTTPException(401, "Token invalid")

        data = response.json()
        return User(
            user_id=data["id"],
            email=data["email"],
            role=UserRole(data["role"])
        )
```

---

## 5. Endpoints lấy thông tin user

### `GET /api/auth/me`

Lấy thông tin user hiện tại từ JWT token.

#### Headers

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

#### Response thành công (200)

```json
{
  "id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "full_name": "Nguyễn Văn A",
  "role": "teacher",
  "is_active": true,
  "permissions": [
    "chat:use",
    "dataset:create",
    "dataset:read:own",
    "file:upload"
  ],
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### Response lỗi

| Code  | Mô tả                               |
| ----- | ----------------------------------- |
| `401` | Không có token / Token không hợp lệ |

#### Luồng xử lý bên trong

```
1. get_current_user()                → Dependency inject từ Authorization header
2. jwt_service.decode_token()        → Decode JWT
3. user_repo.get_by_id()             → Lấy full user info
4. _get_user_permissions()           → Lấy danh sách permissions từ role
5. Return UserResponse
```

---

## 6. Cơ chế bảo mật

### 6.1 Rate Limiting

Bảo vệ chống brute force attacks:

| Metric                       | Giá trị           |
| ---------------------------- | ----------------- |
| Số lần login thất bại tối đa | 5 lần             |
| Thời gian block              | 5 phút (300 giây) |
| Reset counter sau            | Login thành công  |

```python
# Cấu hình trong core/rate_limiter.py
MAX_FAILED_ATTEMPTS = 5
BLOCK_DURATION_SECONDS = 300
```

### 6.2 Password Hashing

Sử dụng **PBKDF2-SHA256** - thuật toán được khuyến nghị bởi NIST:

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Hash password
hashed = pwd_context.hash("plain_password")

# Verify password
is_valid = pwd_context.verify("plain_password", hashed)
```

### 6.3 Input Validation

Tất cả input đều được validate và sanitize:

```python
# Email validation
InputValidator.validate_email(email)
# Kiểm tra: Format hợp lệ, không chứa ký tự đặc biệt nguy hiểm

# Password validation
InputValidator.validate_password(password)
# Kiểm tra: Độ dài ≥ 8, có uppercase, lowercase, số

# Name validation
InputValidator.validate_name(name)
# Kiểm tra: 2-100 ký tự, chỉ chữ cái và khoảng trắng

# Sanitize string (XSS prevention)
InputValidator.sanitize_string(text)
# Loại bỏ: <script>, javascript:, onclick, etc.
```

### 6.4 Security Headers

Middleware tự động thêm security headers:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

---

## 7. Cấu trúc JWT Token

### Payload Structure

```json
{
  "sub": "507f1f77bcf86cd799439011", // user_id
  "email": "user@example.com",
  "role": "teacher",
  "exp": 1705331400, // Expiration timestamp
  "iat": 1705327800 // Issued at timestamp
}
```

### Token Lifetime

| Environment | Duration |
| ----------- | -------- |
| Development | 7 ngày   |
| Production  | 24 giờ   |

### Decode Token (Debug)

```bash
# Sử dụng jwt.io hoặc Python
import jwt
payload = jwt.decode(token, options={"verify_signature": False})
print(payload)
```

---

## 📊 Tổng hợp Endpoints

| Method | Endpoint             | Mô tả                       | Auth Required |
| ------ | -------------------- | --------------------------- | ------------- |
| POST   | `/api/auth/register` | Đăng ký user mới            | ❌            |
| POST   | `/api/auth/login`    | Đăng nhập                   | ❌            |
| POST   | `/api/auth/verify`   | Xác thực token (internal)   | ❌            |
| GET    | `/api/auth/me`       | Lấy thông tin user hiện tại | ✅            |

---

**📝 Document Version:** 1.0  
**📅 Last Updated:** February 2025  
**👥 Author:** AIRC Team

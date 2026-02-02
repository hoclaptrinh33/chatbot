# 👥 RBAC Service - Tài liệu Chi tiết API

> **Service**: airc_internal_chatbot_auth (cùng service với Auth)  
> **Base Path**: /api/rbac  
> **Port**: 8001  
> **Quyền truy cập**: Phần lớn yêu cầu **Admin**

---

## 📑 Mục lục

1. [Tổng quan RBAC](#1-tổng-quan-rbac)
2. [Mô hình dữ liệu](#2-mô-hình-dữ-liệu)
3. [Quản lý Permissions](#3-quản-lý-permissions)
4. [Quản lý Roles](#4-quản-lý-roles)
5. [Gán Permission cho Role](#5-gán-permission-cho-role)
6. [Quản lý Users](#6-quản-lý-users)
7. [Permission Matrix](#7-permission-matrix)

---

## 1. Tổng quan RBAC

**RBAC (Role-Based Access Control)** là hệ thống phân quyền theo vai trò.

### Nguyên lý hoạt động

```
User → Role → Permissions
```

- Mỗi **User** được gán một hoặc nhiều **Role**
- Mỗi **Role** có một tập **Permissions**
- Khi kiểm tra quyền, hệ thống check xem Role của User có Permission tương ứng không

### Các Role mặc định

| Role       | Code      | Mô tả                                 |
| ---------- | --------- | ------------------------------------- |
| 🔴 Admin   | `admin`   | Toàn quyền hệ thống                   |
| 🟡 Teacher | `teacher` | Quản lý datasets, files, xem chatbots |
| 🟢 Student | `student` | Chỉ sử dụng chat                      |

### Base URL

```
http://localhost:8001/api/rbac
```

---

## 2. Mô hình dữ liệu

### 2.1 Permission Document

```json
{
  "_id": "ObjectId",
  "code": "dataset:create", // Unique code
  "name": "Tạo Dataset", // Tên hiển thị
  "resource": "dataset", // Resource type
  "action": "create", // Action verb
  "scope": "any", // Scope: own | any | all | shared
  "description": "Cho phép tạo dataset mới",
  "is_system": true, // System permission (không xóa được)
  "created_at": "2024-01-01T00:00:00Z",
  "created_by": "ObjectId"
}
```

### 2.2 Role Document

```json
{
  "_id": "ObjectId",
  "code": "teacher", // Unique code
  "name": "Giáo viên", // Tên hiển thị
  "description": "Role cho giáo viên quản lý tài liệu",
  "is_active": true,
  "is_system": true, // System role (không xóa được)
  "created_at": "2024-01-01T00:00:00Z",
  "created_by": "ObjectId"
}
```

### 2.3 Role-Permission Mapping

```json
// Collection: role_permissions
{
  "_id": "ObjectId",
  "role_id": "ObjectId",
  "permission_id": "ObjectId",
  "granted_at": "2024-01-01T00:00:00Z",
  "granted_by": "ObjectId"
}
```

### 2.4 User-Role Mapping

```json
// Collection: user_roles
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "role_id": "ObjectId",
  "assigned_at": "2024-01-01T00:00:00Z",
  "assigned_by": "ObjectId"
}
```

---

## 3. Quản lý Permissions

### `GET /api/rbac/permissions`

Lấy danh sách tất cả permissions.

**Quyền yêu cầu**: `Admin`

#### Query Parameters

| Param            | Type | Default | Mô tả                      |
| ---------------- | ---- | ------- | -------------------------- |
| `include_system` | bool | true    | Bao gồm system permissions |

#### Response (200)

```json
[
  {
    "id": "65a1b2c3d4e5f6789012345",
    "code": "chat:use",
    "name": "Sử dụng Chat",
    "resource": "chat",
    "action": "use",
    "scope": null,
    "description": "Cho phép sử dụng chức năng chat",
    "is_system": true,
    "created_at": "2024-01-01T00:00:00Z"
  },
  {
    "id": "65a1b2c3d4e5f6789012346",
    "code": "dataset:create",
    "name": "Tạo Dataset",
    "resource": "dataset",
    "action": "create",
    "scope": "any",
    "description": "Cho phép tạo dataset mới",
    "is_system": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### `POST /api/rbac/permissions`

Tạo permission mới.

**Quyền yêu cầu**: `Admin`

#### Request Body

```json
{
  "code": "report:export",
  "name": "Xuất báo cáo",
  "resource": "report",
  "action": "export",
  "scope": "own",
  "description": "Cho phép xuất báo cáo cá nhân",
  "is_system": false
}
```

#### Response (201)

```json
{
  "id": "65a1b2c3d4e5f6789012347",
  "code": "report:export",
  "name": "Xuất báo cáo",
  ...
}
```

**⚠️ Lưu ý**: Permission mới tự động được gán cho Admin role để đảm bảo Admin luôn có full quyền.

---

### `GET /api/rbac/permissions/{permission_id}`

Lấy chi tiết một permission.

**Quyền yêu cầu**: `Admin`

---

### `PATCH /api/rbac/permissions/{permission_id}`

Cập nhật permission (chỉ name và description).

**Quyền yêu cầu**: `Admin`

#### Request Body

```json
{
  "name": "Tên mới",
  "description": "Mô tả mới"
}
```

---

### `DELETE /api/rbac/permissions/{permission_id}`

Xóa permission.

**Quyền yêu cầu**: `Admin`

**⚠️ Hạn chế**: Không thể xóa system permissions (`is_system: true`).

#### Response (204)

No content.

---

## 4. Quản lý Roles

### `GET /api/rbac/roles`

Lấy danh sách roles.

**Quyền yêu cầu**: `Public` (không cần auth) ⚠️

> Endpoint này public để hỗ trợ UI chọn role khi đăng ký và setup scripts.

#### Query Parameters

| Param              | Type | Default | Mô tả                     |
| ------------------ | ---- | ------- | ------------------------- |
| `include_inactive` | bool | false   | Bao gồm roles đã inactive |

#### Response (200)

```json
[
  {
    "id": "65a1b2c3d4e5f6789012001",
    "code": "admin",
    "name": "Quản trị viên",
    "description": "Toàn quyền quản lý hệ thống",
    "is_active": true,
    "is_system": true
  },
  {
    "id": "65a1b2c3d4e5f6789012002",
    "code": "teacher",
    "name": "Giáo viên",
    "description": "Quản lý tài liệu và datasets",
    "is_active": true,
    "is_system": true
  },
  {
    "id": "65a1b2c3d4e5f6789012003",
    "code": "student",
    "name": "Học sinh",
    "description": "Sử dụng chatbot để học tập",
    "is_active": true,
    "is_system": true
  }
]
```

---

### `GET /api/rbac/roles/{role_id}`

Lấy role với danh sách permissions đã gán.

**Quyền yêu cầu**: `Authenticated` (bất kỳ user đã đăng nhập)

#### Response (200)

```json
{
  "id": "65a1b2c3d4e5f6789012002",
  "code": "teacher",
  "name": "Giáo viên",
  "description": "Quản lý tài liệu và datasets",
  "is_active": true,
  "permissions": [
    {
      "id": "65a1b2c3d4e5f6789012345",
      "code": "chat:use",
      "name": "Sử dụng Chat"
    },
    {
      "id": "65a1b2c3d4e5f6789012346",
      "code": "dataset:create",
      "name": "Tạo Dataset"
    },
    {
      "id": "65a1b2c3d4e5f6789012347",
      "code": "file:upload",
      "name": "Upload File"
    }
  ]
}
```

---

### `POST /api/rbac/roles`

Tạo role mới.

**Quyền yêu cầu**: `Admin`

#### Request Body

```json
{
  "code": "moderator",
  "name": "Điều phối viên",
  "description": "Quản lý nội dung chat",
  "is_active": true
}
```

**⚠️ Hạn chế**: Không thể tạo role với code `admin`.

---

### `PATCH /api/rbac/roles/{role_id}`

Cập nhật role.

**Quyền yêu cầu**: `Admin`

---

### `DELETE /api/rbac/roles/{role_id}`

Xóa role.

**Quyền yêu cầu**: `Admin`

**⚠️ Hạn chế**:

- Không thể xóa role `admin`
- Không thể xóa system roles (`is_system: true`)
- Khi xóa role, tất cả `role_permissions` và `user_roles` liên quan cũng bị xóa

---

## 5. Gán Permission cho Role

### `POST /api/rbac/roles/{role_id}/permissions`

Gán permissions cho role.

**Quyền yêu cầu**: `Admin`

#### Request Body

```json
{
  "permission_ids": ["65a1b2c3d4e5f6789012345", "65a1b2c3d4e5f6789012346"]
}
```

#### Response (200)

```json
{
  "status": "success",
  "granted": 2,
  "message": "Đã gán 2 permissions cho role"
}
```

---

### `DELETE /api/rbac/roles/{role_id}/permissions`

Gỡ permissions khỏi role.

**Quyền yêu cầu**: `Admin`

#### Request Body

```json
{
  "permission_ids": ["65a1b2c3d4e5f6789012345"]
}
```

---

## 6. Quản lý Users

### `GET /api/rbac/users`

Lấy danh sách tất cả users với role.

**Quyền yêu cầu**: `Admin`

#### Response (200)

```json
[
  {
    "id": "65a1b2c3d4e5f6789000001",
    "email": "admin@airc.edu.vn",
    "full_name": "Quản trị viên",
    "role": "admin",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  },
  {
    "id": "65a1b2c3d4e5f6789000002",
    "email": "teacher@airc.edu.vn",
    "full_name": "Nguyễn Văn A",
    "role": "teacher",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### `POST /api/rbac/users`

Admin tạo user mới (không cần register flow).

**Quyền yêu cầu**: `Admin`

#### Request Body

```json
{
  "email": "newuser@example.com",
  "password": "TempP@ss123",
  "full_name": "Trần Văn B",
  "role": "teacher"
}
```

**⚠️ Hạn chế**: Không thể tạo user với role `admin`.

---

### `PATCH /api/rbac/users/{user_id}`

Admin cập nhật user.

**Quyền yêu cầu**: `Admin`

#### Request Body

```json
{
  "full_name": "Tên mới",
  "is_active": false,
  "password": "NewP@ss456" // Optional: đặt lại password
}
```

---

### `DELETE /api/rbac/users/{user_id}`

Admin xóa user.

**Quyền yêu cầu**: `Admin`

---

### `POST /api/rbac/users/{user_id}/roles`

Gán role cho user.

**Quyền yêu cầu**: `Admin`

#### Request Body

```json
{
  "role_id": "65a1b2c3d4e5f6789012002"
}
```

---

### `DELETE /api/rbac/users/{user_id}/roles/{role_id}`

Gỡ role khỏi user.

**Quyền yêu cầu**: `Admin`

---

### `GET /api/rbac/users/{user_id}/permissions`

Lấy danh sách permissions của user (tổng hợp từ tất cả roles).

**Quyền yêu cầu**: `Admin`

#### Response (200)

```json
{
  "user_id": "65a1b2c3d4e5f6789000002",
  "roles": ["teacher"],
  "permissions": [
    "chat:use",
    "dataset:create",
    "dataset:read:own",
    "dataset:update:own",
    "file:upload",
    "file:read:own"
  ]
}
```

---

## 7. Permission Matrix

### Hệ thống permissions mặc định

| Permission Code       | Admin | Teacher | Student | Mô tả                    |
| --------------------- | :---: | :-----: | :-----: | ------------------------ |
| `system:manage`       |  ✅   |   ❌    |   ❌    | Quản lý RBAC             |
| `chat:use`            |  ✅   |   ✅    |   ✅    | Sử dụng chat             |
| `chatbot:create`      |  ✅   |   ❌    |   ❌    | Tạo chatbot              |
| `chatbot:read:any`    |  ✅   |   ✅    |   ❌    | Xem tất cả chatbots      |
| `chatbot:update:own`  |  ✅   |   ❌    |   ❌    | Sửa chatbot của mình     |
| `dataset:create`      |  ✅   |   ✅    |   ❌    | Tạo dataset              |
| `dataset:read:own`    |  ✅   |   ✅    |   ❌    | Xem dataset của mình     |
| `dataset:read:shared` |  ✅   |   ✅    |   ✅    | Xem dataset được chia sẻ |
| `dataset:update:own`  |  ✅   |   ✅    |   ❌    | Sửa dataset của mình     |
| `dataset:delete:own`  |  ✅   |   ✅    |   ❌    | Xóa dataset của mình     |
| `file:upload`         |  ✅   |   ✅    |   ❌    | Upload file              |
| `file:read:any`       |  ✅   |   ✅    |   ❌    | Xem tất cả files         |
| `stats:view`          |  ✅   |   ❌    |   ❌    | Xem thống kê             |

### Đặc biệt: Admin Bypass

**Admin** có đặc quyền bỏ qua tất cả permission checks:

```python
# Trong code check permission
if current_user.role == "admin":
    return True  # Admin luôn được phép
```

---

## 📊 Tổng hợp Endpoints

| Method | Endpoint                           | Mô tả                       | Auth   |
| ------ | ---------------------------------- | --------------------------- | ------ |
| GET    | `/api/rbac/permissions`            | Danh sách permissions       | Admin  |
| POST   | `/api/rbac/permissions`            | Tạo permission              | Admin  |
| GET    | `/api/rbac/permissions/{id}`       | Chi tiết permission         | Admin  |
| PATCH  | `/api/rbac/permissions/{id}`       | Sửa permission              | Admin  |
| DELETE | `/api/rbac/permissions/{id}`       | Xóa permission              | Admin  |
| GET    | `/api/rbac/roles`                  | Danh sách roles             | Public |
| GET    | `/api/rbac/roles/{id}`             | Chi tiết role + permissions | Auth   |
| POST   | `/api/rbac/roles`                  | Tạo role                    | Admin  |
| PATCH  | `/api/rbac/roles/{id}`             | Sửa role                    | Admin  |
| DELETE | `/api/rbac/roles/{id}`             | Xóa role                    | Admin  |
| POST   | `/api/rbac/roles/{id}/permissions` | Gán permissions             | Admin  |
| DELETE | `/api/rbac/roles/{id}/permissions` | Gỡ permissions              | Admin  |
| GET    | `/api/rbac/users`                  | Danh sách users             | Admin  |
| POST   | `/api/rbac/users`                  | Tạo user                    | Admin  |
| PATCH  | `/api/rbac/users/{id}`             | Sửa user                    | Admin  |
| DELETE | `/api/rbac/users/{id}`             | Xóa user                    | Admin  |
| POST   | `/api/rbac/users/{id}/roles`       | Gán role                    | Admin  |
| DELETE | `/api/rbac/users/{id}/roles/{rid}` | Gỡ role                     | Admin  |
| GET    | `/api/rbac/users/{id}/permissions` | Lấy permissions             | Admin  |

---

**📝 Document Version:** 1.0  
**📅 Last Updated:** February 2025  
**👥 Author:** AIRC Team

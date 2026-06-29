# Hướng Dẫn Seed Database - AIRC Internal Chatbot

## Mục Đích

Khởi tạo dữ liệu ban đầu cho hệ thống Auth:

- Collections và Indexes
- Roles & Permissions (RBAC)
- Sample Users (Admin, Teacher, Student)

---

## Cách Chạy

### Cách 1: Từ Docker Container (Khuyến nghị)

```bash
# Copy script vào container
docker cp airc_internal_chatbot_auth/migrate/seed_database.py airc_chatbot_auth:/app/seed_database.py

# Chạy seed
docker exec airc_chatbot_auth python /app/seed_database.py
```

### Cách 2: Từ Host Machine

```bash
# Drop database cũ (nếu cần)
docker exec -it airc_chatbot_mongodb mongosh airc_auth_db --eval "db.dropDatabase()"

# Chạy seed
python airc_internal_chatbot_auth/migrate/seed_database.py
```

---

## Dữ Liệu Được Tạo

### Users

| Email                      | Password  | Role    |
| -------------------------- | --------- | ------- |
| `admin@airc.edu.vn`        | `Pass123` | admin   |
| `nguyen.van.a@airc.edu.vn` | `Pass123` | teacher |
| `sv01@student.airc.edu.vn` | `Pass123` | student |

### Roles

| Role        | Mô tả                                      |
| ----------- | ------------------------------------------ |
| **admin**   | Toàn quyền hệ thống (duy nhất)             |
| **teacher** | Tạo dataset, upload tài liệu, chat với bot |
| **student** | Chỉ chat với bot                           |

### Permissions

| Resource     | Actions                             |
| ------------ | ----------------------------------- |
| **users**    | view, create, update, delete        |
| **rbac**     | manage_roles, manage_permissions    |
| **datasets** | view, create, update, delete, share |
| **chatbots** | create, use, manage:own, manage:any |
| **model**    | view, train                         |

---

## Kiểm Tra Seed

```bash
# Vào MongoDB shell
docker exec -it airc_chatbot_mongodb mongosh airc_auth_db

# Kiểm tra data
db.users.countDocuments()        # Expected: 3
db.roles.countDocuments()        # Expected: 4
db.permissions.countDocuments()  # Expected: 15

# Test login
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@airc.edu.vn", "password": "Pass123"}'
```

---

## Troubleshooting

| Lỗi                    | Nguyên nhân       | Giải pháp                           |
| ---------------------- | ----------------- | ----------------------------------- |
| `E11000 duplicate key` | Data cũ chưa xóa  | Drop database rồi seed lại          |
| `Connection refused`   | MongoDB chưa chạy | `docker start airc_chatbot_mongodb` |
| `WriteError`           | Schema conflict   | Drop và reseed                      |

---

## Lưu Ý

- **KHÔNG** chạy seed trên production
- Backup data trước khi drop database
- Sau khi seed xong, chạy test: `python tester/test_complete_47_apis.py`

---

**Cập nhật**: 2025-01-19

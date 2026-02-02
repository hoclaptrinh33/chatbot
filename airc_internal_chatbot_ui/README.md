# AIRC Frontend UI

Giao diện người dùng cho hệ thống Chatbot, được xây dựng bằng Next.js (App Router), cung cấp trải nghiệm Chat, quản lý Workspace và RBAC Admin.

## 1. Kiến trúc & Design Pattern
Dự án sử dụng **Component-Based Architecture** trên nền tảng **Next.js 14+ (App Router)**.

### Cấu trúc thư mục:
```
airc_internal_chatbot_ui/
├── src/
│   ├── app/          # Next.js App Router (Pages & Layouts)
│   ├── components/   # Reusable UI Components
│   │   ├── Admin/    # Admin specific components
│   │   └── Chat/     # Chat interface components
│   ├── services/     # API Client Services (Axios)
│   ├── stores/       # Global State (Zustand)
│   ├── hooks/        # Custom React Hooks
│   └── core/         # Shared Types/Interfaces
├── public/           # Static Assets
├── .env.example      # Environment template
├── Dockerfile        # Container config
├── next.config.ts    # Next.js Config
├── package.json      # Dependencies
└── README.md         # Documentation
```

### Design Patterns & Libraries:
- **Container/Presentational Pattern**: Tách biệt logic data fetching và hiển thị UI.
- **HOC (Higher-Order Components)**: Dùng cho `withAuth` để bảo vệ routes.
- **Zustand**: Quản lý Global State đơn giản và hiệu quả.
- **Ant Design**: UI Library chuẩn doanh nghiệp.

## 2. Cài đặt & Chạy (Môi trường Dev)

### Yêu cầu:
- Node.js 18+
- NPM hoặc Yarn

### Bước 1: Sao chép cấu hình
Copy file `.env.example` thành `.env.local`:
```bash
cp .env.example .env.local
```

### Bước 2: Cài đặt thư viện
```bash
npm install
```

### Bước 3: Chạy ứng dụng
```bash
npm run dev
```
Truy cập tại: `http://localhost:3000`

## 3. Chạy bằng Docker

### Bước 1: Build Image
```bash
docker build -t airc-frontend .
```

### Bước 2: Run Container
```bash
docker run -d -p 3000:3000 --env-file .env.local airc-frontend
```

## 4. Luồng hoạt động (System Flow)
1. **User Action**: Người dùng tương tác (Click Login, Chat).
2. **State Update**: Zustand store cập nhật state.
3. **API Call**: Service Layer gọi Auth Service (Port 8001) hoặc Core Service (Port 8000).
4. **Render**: Dữ liệu trả về được render ra UI Components.

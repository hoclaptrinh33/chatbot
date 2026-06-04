# CODEBASE_CONTEXT - UI Domain

Last updated: 2026-05-28

This file contains extracted context related to Next.js UI, stores, interceptors, and components.

## 1. Project Overview (UI)

### 1.1 Purpose and business domain
- Three core concerns are separated:
  - Web UI for admin + employee + intern/guest usage.

### 1.2 Architecture style
- Monorepo with service boundaries.
- Microservice runtime:
  - `airc_internal_chatbot_ui` (Next.js frontend).

### 1.3 Technology stack (UI)

| Area | Stack | Versions / notes |
|---|---|---|
| UI service | Next.js + React + TypeScript + AntD + Zustand + Axios | `next=16.1.2`, `react=19.2.3`, `antd^6.2.0`, `typescript^5` |

## 2. Directory Structure (UI extract)

```text
airc_internal_chatbot_ui/
|- src/
|  |- app/                       # Next App Router pages (auth/dashboard/admin)
|  |- components/                # UI components (Admin/Auth/Chat/Dataset/etc.)
|  |- core/                      # domain entities + repository interfaces
|  |- infrastructure/            # axios clients, interceptors, repository adapters
|  |- services/                  # API service facades
|  |- stores/                    # Zustand stores for auth/chat/dataset state
|  |- middleware.ts              # route guard middleware using auth cookie
|- next.config.ts                # standalone build + TS build behavior
|- k8s/                          # UI deployment/service
```

## 3. Entry Points and Runtime (UI)

### 3.1 Frontend entrypoint
- Next.js app router root: `airc_internal_chatbot_ui/src/app`.
- Route middleware: `airc_internal_chatbot_ui/src/middleware.ts`.
  - Protects `/dashboard/*` using cookie `access_token`.

## 4. Core Modules / Components (UI)

### 4.1 Frontend auth and chat state modules

#### Auth store
- Path: `airc_internal_chatbot_ui/src/stores/authStore.ts`
- Responsibility:
  - token/user/permission state, login/logout/checkAuth orchestration, persistence.
- Key signatures:

```ts
interface AuthState {
  login(email: string, password: string): Promise<void>
  logout(): void
  checkAuth(): Promise<void>
}
```

- Depends on:
  - `authService`, `storageService`, `chatStore`.
- Imported by:
  - route guards/components and HTTP interceptor token helper.

#### Chat store
- Path: `airc_internal_chatbot_ui/src/stores/chatStore.ts`
- Responsibility:
  - session list, active conversation state, message send flow, chatbot/dataset selection, debug metrics state.
- Key signatures:

```ts
interface ChatState {
  loadSessions(): Promise<void>
  createSession(name?: string): Promise<string>
  sendMessage(question: string): Promise<void>
  selectChatbot(id: string | null, datasetIds?: string[]): void
  resetStore(): void
}
```

- Depends on:
  - `chatService`.
- Imported by:
  - dashboard chat components and `authStore` reset flow.

## 5. API / Interface Contracts (UI)

### 5.1 Frontend public service interfaces (TypeScript)

| Module | Public contract |
|---|---|
| `src/services/authService.ts` | `login`, `getMe`, `getPermissions`, `getAllUsers`, admin user CRUD |
| `src/services/rbacService.ts` | permission CRUD, role CRUD, assign permissions, assign/remove/get user roles, matrix |
| `src/services/datasetService.ts` | dataset CRUD, dataset file ops, share, chunk retrieval |
| `src/services/chatService.ts` | session CRUD, message retrieval, `askQuestion` |
| `src/services/chatbotService.ts` | chatbot CRUD, assign datasets, access config by allowed_user_ids/allowed_departments |
| `src/stores/authStore.ts` | `login/logout/checkAuth`, token + user + permissions state |
| `src/stores/chatStore.ts` | chat sessions/messages flow with chatbot/dataset context |

## 6. Business Logic and Rules (UI)

### 6.1 UI behavioral rules
- `AuthGuard` and route middleware enforce auth for dashboard routes.
- Zustand stores use `skipHydration` to avoid SSR mismatch.
- On login/logout, chat store is reset to prevent cross-user data leakage.
- HTTP interceptors attach bearer token from store; 401 triggers client cleanup + redirect to login.
- Admin chatbot form configures access by explicit users and departments.
- User chat screens only render chatbots the current user can access (user ID OR department); empty allow-lists mean admin-only.

## 7. Configuration and Environment (UI)

### 7.1 Required env vars (UI)

| Variable | Required | Note |
|---|---|---|
| `NEXT_PUBLIC_AUTH_API` | yes | expected to include `/api/auth` |
| `NEXT_PUBLIC_API_URL` | yes | expected to include `/api/v1` |
| `NEXT_PUBLIC_APP_URL` | recommended | app absolute URL |

### 7.2 Config files and purpose (UI-related)

| File | Purpose |
|---|---|
| `airc_internal_chatbot_ui/next.config.ts` | Next build behavior (`output: standalone`) |
| `airc_internal_chatbot_ui/src/infrastructure/http/*.ts` | axios base URL + auth interceptors |

## 8. Conventions (UI-related)

### 8.1 Conventions used
- UI architecture has layered adapters:
  - `core/entities` + `core/repositories` interfaces
  - `infrastructure/repositories` implementations
  - `services/*` facades
  - `stores/*` app state orchestration.

## 9. Pitfalls (UI-related)

### 9.1 Important technical debt / anti-patterns
- UI build config sets `typescript.ignoreBuildErrors=true` (can hide TS regressions during build).

## 10. Quick Answer Index (UI)

If you need to answer quickly:
- Frontend auth state + route protection: `src/stores/authStore.ts`, `src/components/Auth/AuthGuard.tsx`, `src/middleware.ts`.
- Frontend chat state orchestration: `src/stores/chatStore.ts`, `src/services/chatService.ts`.

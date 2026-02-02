/**
 * User Entity - Domain Model
 * Align with Backend UserResponse
 */

export enum UserRole {
    ADMIN = 'admin',
    TEACHER = 'teacher',
    STUDENT = 'student'
}

export enum Permission {
    // User management
    USERS_VIEW = "users:view",
    USERS_CREATE = "users:create",
    USERS_UPDATE = "users:update",
    USERS_DELETE = "users:delete",

    // Dataset management
    DATASETS_VIEW_ALL = "datasets:view:all",
    DATASETS_VIEW_SHARED = "datasets:view:shared",
    DATASETS_CREATE = "datasets:create",
    DATASETS_UPDATE_OWN = "datasets:update:own",
    DATASETS_UPDATE_ANY = "datasets:update:any",
    DATASETS_DELETE_OWN = "datasets:delete:own",
    DATASETS_DELETE_ANY = "datasets:delete:any",
    DATASETS_SHARE = "datasets:share",

    // Chatbot management
    CHATBOTS_CREATE = "chatbots:create",
    CHATBOTS_USE = "chatbots:use",
    CHATBOTS_MANAGE_OWN = "chatbots:manage:own",
    CHATBOTS_MANAGE_ANY = "chatbots:manage:any",

    // Chat
    CHAT_USE = "chat:use",
    CHAT_VIEW_OWN = "chat:view:own",
    CHAT_VIEW_ANY = "chat:view:any",

    // Analytics
    ANALYTICS_VIEW = "analytics:view",
    SYSTEM_MANAGE = "system:manage",

    // RBAC Management
    RBAC_MANAGE_ROLES = "rbac:manage_roles",
    RBAC_MANAGE_PERMISSIONS = "rbac:manage_permissions"
}

export interface User {
    id: string;
    email: string;
    full_name: string;
    role: UserRole | string;
    is_active: boolean;
    avatar_url?: string;
    created_at: string;
    updated_at?: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    user?: User; // Optional if backend returns user info with token
}

import axios, { AxiosInstance } from 'axios';

import { UserRole, Permission as PermissionEnum } from '../types/auth';

// URL API Backend - RBAC routes are at /api/rbac/*
// Use base URL without /auth suffix since RBAC is at /api/rbac
const API_URL = process.env.NEXT_PUBLIC_AUTH_API?.replace('/api/auth', '/api') || 'http://localhost:8001/api';

export interface Permission {
    id: string;
    _id?: string; // Support MongoDB _id
    name: string;
    code: PermissionEnum | string;
    description?: string;
    resource: string;
    action: string;
    is_system?: boolean;
    created_at?: string;
}

export interface Role {
    id: string;
    _id?: string;
    name: string;
    code: UserRole | string;
    description?: string;
    is_system?: boolean;
    created_at?: string;
    permissions?: Permission[];
}

export interface CreatePermissionDto {
    name: string;
    code: PermissionEnum | string;
    description?: string;
    resource: string;
    action: string;
    is_system?: boolean;
}

export interface CreateRoleDto {
    name: string;
    code: UserRole | string;
    description?: string;
    is_system?: boolean;
}

export interface UpdateRoleDto {
    name?: string;
    description?: string;
}

export interface UserRoleAssignment {
    role_id: string;
    expires_at?: string;
}

/**
 * Interface cho RBAC Service
 */
export interface IRBACService {
    // Permissions
    getPermissions(token: string): Promise<Permission[]>;
    createPermission(data: CreatePermissionDto, token: string): Promise<Permission>;
    deletePermission(id: string, token: string): Promise<void>;

    // Roles
    getRoles(): Promise<Role[]>;
    getRole(id: string, token: string): Promise<Role>;
    createRole(data: CreateRoleDto, token: string): Promise<Role>;
    updateRole(id: string, data: UpdateRoleDto, token: string): Promise<Role>;
    deleteRole(id: string, token: string): Promise<void>;
    assignPermissionsToRole(roleId: string, permissionIds: string[], token: string): Promise<void>;

    // User Assignments
    assignRoleToUser(userId: string, roleId: string, token: string): Promise<void>;
    removeRoleFromUser(userId: string, roleId: string, token: string): Promise<void>;
    getUserRoles(userId: string, token: string): Promise<Role[]>;
}

/**
 * Service xu ly RBAC (Role-Based Access Control)
 * Su dung Class va Singleton Pattern
 */
class RBACService implements IRBACService {
    private static instance: RBACService;
    private api: AxiosInstance;

    private constructor() {
        this.api = axios.create({
            baseURL: API_URL,
            headers: {
                'Content-Type': 'application/json',
            },
        });
    }

    public static getInstance(): RBACService {
        if (!RBACService.instance) {
            RBACService.instance = new RBACService();
        }
        return RBACService.instance;
    }

    // === PERMISSIONS ===

    public async getPermissions(token: string): Promise<Permission[]> {
        const response = await this.api.get<Permission[]>('/rbac/permissions', {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    }

    public async createPermission(data: CreatePermissionDto, token: string): Promise<Permission> {
        const response = await this.api.post<Permission>('/rbac/permissions', data, {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    }

    public async deletePermission(id: string, token: string): Promise<void> {
        await this.api.delete(`/rbac/permissions/${id}`, {
            headers: { Authorization: `Bearer ${token}` }
        });
    }

    public async updatePermission(id: string, data: Partial<CreatePermissionDto>, token: string): Promise<Permission> {
        const response = await this.api.patch<Permission>(`/rbac/permissions/${id}`, data, {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    }

    // === ROLES ===

    public async getRoles(): Promise<Role[]> {
        // Public endpoint
        const response = await this.api.get<Role[]>('/rbac/roles');
        return response.data;
    }

    public async getRole(id: string, token: string): Promise<Role> {
        const response = await this.api.get<Role>(`/rbac/roles/${id}`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    }

    public async createRole(data: CreateRoleDto, token: string): Promise<Role> {
        const response = await this.api.post<Role>('/rbac/roles', data, {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    }

    public async updateRole(id: string, data: UpdateRoleDto, token: string): Promise<Role> {
        const response = await this.api.patch<Role>(`/rbac/roles/${id}`, data, {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    }

    public async deleteRole(id: string, token: string): Promise<void> {
        await this.api.delete(`/rbac/roles/${id}`, {
            headers: { Authorization: `Bearer ${token}` }
        });
    }

    public async assignPermissionsToRole(roleId: string, permissionIds: string[], token: string): Promise<void> {
        await this.api.post(
            `/rbac/roles/${roleId}/permissions`,
            { permission_ids: permissionIds },
            { headers: { Authorization: `Bearer ${token}` } }
        );
    }

    // === USER ASSIGNMENTS ===

    public async assignRoleToUser(userId: string, roleId: string, token: string): Promise<void> {
        await this.api.post(
            `/rbac/users/${userId}/roles`,
            { role_id: roleId },
            { headers: { Authorization: `Bearer ${token}` } }
        );
    }

    public async removeRoleFromUser(userId: string, roleId: string, token: string): Promise<void> {
        await this.api.delete(`/rbac/users/${userId}/roles/${roleId}`, {
            headers: { Authorization: `Bearer ${token}` }
        });
    }

    public async getUserRoles(userId: string, token: string): Promise<Role[]> {
        const response = await this.api.get<Role[]>(`/rbac/users/${userId}/roles`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    }

    // === MATRIX ===

    public async getPermissionMatrix(token: string): Promise<PermissionMatrixResponse> {
        const response = await this.api.get<PermissionMatrixResponse>('/rbac/matrix', {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    }
}

export interface PermissionMatrixResponse {
    roles: Role[];
    permissions: Permission[];
    matrix: Record<string, string[]>; // role_code -> permission_codes
}

export const rbacService = RBACService.getInstance();
export default rbacService;

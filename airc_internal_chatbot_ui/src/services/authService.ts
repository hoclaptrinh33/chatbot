import axios, { AxiosInstance } from 'axios';
import { storageService, StorageService } from './storageService';
import { User, UserRole } from '../types/auth';
export type { User, UserRole };

// URL API Backend - Auth service routes are at /api/auth/*
const API_URL = process.env.NEXT_PUBLIC_AUTH_API || 'http://localhost:8001/api/auth';

// Interface cho Login Response
export interface LoginResponse {
    access_token: string;
    token_type: string;
    user: User;
}

/**
 * Interface cho Auth Service
 * Dam bao Dependency Inversion Principle
 */
export interface IAuthService {
    login(email: string, password: string): Promise<LoginResponse>;
    getMe(token: string): Promise<User>;
    getPermissions(token: string): Promise<string[]>;
}

/**
 * Service xu ly Authentication
 * Su dung Class va Singleton Pattern
 */
class AuthService implements IAuthService {
    private static instance: AuthService;
    private api: AxiosInstance;
    private storage: StorageService;

    private constructor() {
        this.api = axios.create({
            baseURL: API_URL,
            headers: {
                'Content-Type': 'application/json',
            },
        });
        this.storage = storageService;
    }

    public static getInstance(): AuthService {
        if (!AuthService.instance) {
            AuthService.instance = new AuthService();
        }
        return AuthService.instance;
    }

    /**
     * Dang nhap nguoi dung
     */
    public async login(email: string, password: string): Promise<LoginResponse> {
        const response = await this.api.post<LoginResponse>('/login', {
            email,
            password
        });
        return response.data;
    }

    /**
     * Lay thong tin user hien tai
     */
    public async getMe(token: string): Promise<User> {
        const response = await this.api.get<User>('/me', {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    }

    /**
     * Lay danh sach permissions cua user
     */
    public async getPermissions(token: string): Promise<string[]> {
        const response = await this.api.get<string[]>('/me/permissions', {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    }

    /**
     * Lay danh sach tat ca users (Admin only)
     */
    public async getAllUsers(token: string): Promise<User[]> {
        const response = await this.api.get<User[]>('/users', {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    }

    // === USER MANAGEMENT (ADMIN) ===

    public async createUser(data: CreateUserDto, token: string): Promise<User> {
        const response = await this.api.post<User>('/users', data, {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    }

    public async updateUser(id: string, data: UpdateUserDto, token: string): Promise<User> {
        const response = await this.api.patch<User>(`/users/${id}`, data, {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    }

    public async deleteUser(id: string, token: string): Promise<void> {
        await this.api.delete(`/users/${id}`, {
            headers: { Authorization: `Bearer ${token}` }
        });
    }
}

export interface CreateUserDto {
    email: string;
    password: string;
    full_name: string;
    role: UserRole | string;
}

export interface UpdateUserDto {
    full_name?: string;
    role?: UserRole | string;
    is_active?: boolean;
    password?: string;
}

export const authService = AuthService.getInstance();
export default authService;

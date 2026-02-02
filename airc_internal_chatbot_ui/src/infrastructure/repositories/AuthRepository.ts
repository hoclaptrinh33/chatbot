import { IAuthRepository } from '@/core/repositories/IAuthRepository';
import { LoginDTO, RegisterDTO, AuthResponse } from '@/core/entities/Auth';
import { User } from '@/core/entities/User';
import { authClient } from '@/infrastructure/http/auth.client';

export const authRepository: IAuthRepository = {
    /**
     * Đăng nhập người dùng.
     * Gửi credentials (email/password) lên Auth Service để lấy token.
     * @param credentials - Thông tin đăng nhập
     */
    async login(credentials: LoginDTO): Promise<AuthResponse> {
        // Gọi API login. Backend nhận body JSON.
        const response = await authClient.post<AuthResponse>('/login', credentials);
        return response.data;
    },

    /**
     * Đăng ký user mới
     * @param data - Thông tin đăng ký
     */
    async register(data: RegisterDTO): Promise<AuthResponse> {
        const response = await authClient.post<AuthResponse>('/register', data);
        return response.data;
    },

    /**
     * Lấy thông tin user hiện tại
     */
    async getMe(): Promise<User> {
        const response = await authClient.get<User>('/me');
        return response.data;
    },

    /**
     * Lấy danh sách permissions
     */
    async getPermissions(): Promise<string[]> {
        const response = await authClient.get<string[]>('/me/permissions');
        return response.data;
    },

    /**
     * Đăng xuất (Client side only, trừ khi BE có blacklist token)
     */
    async logout(): Promise<void> {
        // Chỉ cần xóa token ở client (đã xử lý bởi store/interceptor)
        return Promise.resolve();
    }
};

import { LoginDTO, RegisterDTO, AuthResponse } from '@/core/entities/Auth';
import { User } from '@/core/entities/User';

export interface IAuthRepository {
    login(credentials: LoginDTO): Promise<AuthResponse>;
    register(data: RegisterDTO): Promise<AuthResponse>;
    getMe(): Promise<User>;
    getPermissions(): Promise<string[]>;
    logout(): Promise<void>;
}

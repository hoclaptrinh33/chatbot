import { User, UserRole } from './User';

export interface AuthResponse {
    access_token: string;
    token_type: string;
    user?: User;
}

// Re-export User related stuff if needed
export type { User };

export interface LoginDTO {
    email: string;
    password: string;
}

export interface RegisterDTO {
    email: string;
    password: string;
    full_name: string;
    role?: UserRole | string;
}

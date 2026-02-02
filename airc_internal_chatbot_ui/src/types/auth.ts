// Re-export Enums & Entities from Core to ensure Single Source of Truth
export { UserRole } from '../core/entities/User';
export { Permission } from '../core/entities/User';
export type { User } from '../core/entities/User';

import { User } from '../core/entities/User';

export interface LoginResponse {
    access_token: string;
    token_type: string;
    user: User;
}

export interface RegisterDto {
    email: string;
    password: string;
    full_name: string;
    role?: string;
}

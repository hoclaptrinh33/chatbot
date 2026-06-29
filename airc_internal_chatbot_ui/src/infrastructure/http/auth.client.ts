import axios from 'axios';
import { authErrorInterceptor, authRequestInterceptor } from './interceptors';

// Base URL cho Auth Service  
// NEXT_PUBLIC_AUTH_API = https://ragairc.neovort.shop/api/auth
// AuthRepository calls /login, /me, etc. which become /api/auth/login, /api/auth/me
const BASE_URL = process.env.NEXT_PUBLIC_AUTH_API || 'http://localhost:8001/api/auth';

export const authClient = axios.create({
    baseURL: BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 10000,
});

// Apply interceptors
authClient.interceptors.request.use(authRequestInterceptor);
authClient.interceptors.response.use((response) => response, authErrorInterceptor);

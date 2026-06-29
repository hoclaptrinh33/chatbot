import { AxiosError, InternalAxiosRequestConfig } from 'axios';

/**
 * Request Interceptor - Thêm token vào header
 * @param config - Axios config
 */
import { getAuthToken } from '@/stores/authStore';

/**
 * Request Interceptor - Thêm token vào header
 * @param config - Axios config
 */
export const authRequestInterceptor = (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
        // Use the centralized helper from authStore to get the token
        const token = getAuthToken();
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
    }
    return config;
};

/**
 * Response Error Interceptor - Handle 401 Unauthorized
 * Xử lý auto redirect và tránh infinite loop
 */
export const authErrorInterceptor = (error: AxiosError) => {
    if (error.response?.status === 401) {
        if (typeof window !== 'undefined') {
            const currentPath = window.location.pathname;
            const isAuthPage = currentPath.startsWith('/auth/');

            if (!isAuthPage) {
                // Chỉ redirect khi KHÔNG ở trang auth
                localStorage.removeItem('access_token');
                localStorage.removeItem('user_info');
                window.location.href = '/auth/login';
            } else {
                console.warn('401 on auth page - skipping redirect');
            }
        }
    }
    return Promise.reject(error);
};

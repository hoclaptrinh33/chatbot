import { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { storageService } from '@/services/storageService';

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
        // Ưu tiên token trong store, fallback từ storage khi store chưa hydrate
        const token = getAuthToken() || storageService.getAccessToken();
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
                // Dọn auth state nhất quán (cookie + localStorage)
                storageService.removeAccessToken();
                localStorage.removeItem('airc-auth-storage');
                localStorage.removeItem('user_info');
                window.location.href = '/auth/login';
            } else {
                console.warn('401 on auth page - skipping redirect');
            }
        }
    }
    return Promise.reject(error);
};

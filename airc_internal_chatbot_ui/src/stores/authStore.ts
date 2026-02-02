import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { AxiosError } from 'axios';
import { authService, User } from '../services/authService';
import { storageService } from '@/services/storageService';
import useChatStore from './chatStore';

interface AuthState {
    user: User | null;
    token: string | null;
    permissions: string[];
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;

    // Actions
    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
    checkAuth: () => Promise<void>;
}

/**
 * Store quan ly trang thai Authentication
 * Su dung Zustand + Persist de luu vao localStorage
 * 
 * QUAN TRONG: KHONG dung Ant Design message trong store
 * Vi store khong co React context. Notifications phai o component level.
 */
const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            user: null,
            token: null,
            permissions: [],
            isAuthenticated: false,
            isLoading: false,
            error: null,

            /**
             * Ham login
             * KHONG show notification o day - de component xu ly
             */
            login: async (email, password) => {
                set({ isLoading: true, error: null });
                try {
                    console.log('[AuthStore] Login attempt for:', email);
                    const data = await authService.login(email, password);

                    // CRITICAL: Set token and authenticate immediately
                    storageService.setAccessToken(data.access_token);
                    useChatStore.getState().resetStore();

                    set({
                        token: data.access_token,
                        isAuthenticated: true,
                        isLoading: false,
                        error: null,
                    });

                    console.log('[AuthStore] Login successful, token saved. Fetching user info in background...');

                    // Fetch user info and permissions in background (non-blocking)
                    Promise.all([
                        authService.getMe(data.access_token),
                        authService.getPermissions(data.access_token)
                    ]).then(([user, permissions]) => {
                        console.log('[AuthStore] User info loaded:', user.email, 'Permissions:', permissions.length);
                        set({ user, permissions });
                    }).catch((err) => {
                        console.error('[AuthStore] Failed to fetch user info (non-critical):', err);
                        // User is still authenticated, will retry on next checkAuth
                    });

                    // QUAN TRONG: KHONG goi message.success() o day
                    // Component se tu hien thi notification
                } catch (error: unknown) {
                    console.error('[AuthStore] Login failed:', error);
                    const err = error as AxiosError<{ detail: string }>;
                    const errorMsg = err.response?.data?.detail || err.message || 'Dang nhap that bai';

                    set({
                        error: errorMsg,
                        isLoading: false,
                    });

                    // QUAN TRONG: KHONG goi message.error() o day
                    // Throw error de component bat duoc va hien thi notification
                    throw error;
                }
            },

            /**
             * Ham logout
             */
            logout: () => {
                console.log('[AuthStore] Logging out...');

                // CRITICAL: Remove cookie using StorageService
                storageService.removeAccessToken();

                // CRITICAL: Reset chat store to prevent data leakage between users
                useChatStore.getState().resetStore();

                set({
                    user: null,
                    token: null,
                    permissions: [],
                    isAuthenticated: false,
                });
                // KHONG goi message.info() o day
            },

            /**
             * Kiem tra token con hop le khong
             * CRITICAL: Khong xoa state neu co loi, chi log ra de debug
             * Vi neu vua login xong ma API /me bi loi, se mat het state
             */
            checkAuth: async () => {
                const { token } = get();

                // Neu khong co token thi khong lam gi
                if (!token) {
                    // Try to restore from cookie via StorageService if localStorage empty? 
                    // For now, stick to localStorage as primary source of truth for Zustand Persist.
                    console.log('[AuthStore] checkAuth: No token found, skipping');
                    return;
                }

                try {
                    console.log('[AuthStore] checkAuth: Verifying token with backend...');
                    const user = await authService.getMe(token);

                    // Fetch fresh permissions
                    const permissions = await authService.getPermissions(token);

                    console.log('[AuthStore] checkAuth: Token valid, user:', user.email);

                    // CRITICAL: Sync cookie (ensure middleware passes)
                    storageService.setAccessToken(token);

                    set({ user, permissions, isAuthenticated: true });
                } catch (error: unknown) {
                    const err = error as AxiosError;
                    console.error('[AuthStore] checkAuth: Token verification failed:', err.message);
                    // Check if 401/403 -> Force logout
                    if (err.response?.status === 401) {
                        console.log('[AuthStore] checkAuth: Token expired, logging out');
                        get().logout();
                    }
                }
            },
        }),
        {
            name: 'airc-auth-storage', // Ten key trong localStorage
            skipHydration: true, // CRITICAL: Skip automatic hydration to prevent SSR mismatch
            partialize: (state) => ({
                token: state.token,
                user: state.user,
                permissions: state.permissions,
                isAuthenticated: state.isAuthenticated
            }), // Chi luu nhung truong nay
            onRehydrateStorage: () => (state) => {
                // Callback sau khi rehydrate xong
                console.log('Auth store rehydrated:', state?.isAuthenticated);
            },
        }
    )
);

export const getAuthToken = () => useAuthStore.getState().token;

export default useAuthStore;

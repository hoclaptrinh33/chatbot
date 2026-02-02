/**
 * Service quan ly luu tru (LocalStorage + Cookies)
 * Ap dung Single Responsibility Principle
 */
export class StorageService {
    private static instance: StorageService;
    private readonly TOKEN_KEY = 'access_token';

    private constructor() { }

    public static getInstance(): StorageService {
        if (!StorageService.instance) {
            StorageService.instance = new StorageService();
        }
        return StorageService.instance;
    }

    /**
     * Set Cookie (cho Middleware)
     */
    public setCookie(name: string, value: string, days: number = 7): void {
        if (typeof document === 'undefined') return;

        const expires = new Date(Date.now() + days * 864e5).toUTCString();
        document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
    }

    /**
     * Get Cookie
     */
    public getCookie(name: string): string | null {
        if (typeof document === 'undefined') return null;

        return document.cookie.split('; ').reduce((r, v) => {
            const parts = v.split('=');
            return parts[0] === name ? decodeURIComponent(parts[1]) : r;
        }, '') || null;
    }

    /**
     * Remove Cookie
     */
    public removeCookie(name: string): void {
        if (typeof document === 'undefined') return;
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
    }

    /**
     * Luu Access Token vao ca Cookie (cho Middleware) va LocalStorage (cho Axios Interceptor)
     */
    public setAccessToken(token: string): void {
        this.setCookie(this.TOKEN_KEY, token);
        if (typeof window !== 'undefined') {
            localStorage.setItem(this.TOKEN_KEY, token);
        }
    }

    public removeAccessToken(): void {
        this.removeCookie(this.TOKEN_KEY);
        if (typeof window !== 'undefined') {
            localStorage.removeItem(this.TOKEN_KEY);
        }
    }

    public getAccessToken(): string | null {
        // Prioritize Cookie, fallback to LocalStorage
        let token = this.getCookie(this.TOKEN_KEY);
        if (!token && typeof window !== 'undefined') {
            token = localStorage.getItem(this.TOKEN_KEY);
        }
        return token;
    }
}

export const storageService = StorageService.getInstance();

'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import useAuthStore from '@/stores/authStore';
import { Spin, Result, Button } from 'antd';
import { useRole } from '@/hooks/useRole';
import { usePermission } from '@/hooks/usePermission';

interface AuthGuardProps {
    children: React.ReactNode;
    requiredRole?: string | string[];
    requiredPermission?: string | string[];
}

/**
 * Component bao ve cac route can dang nhap
 * Kiem tra token va redirect neu chua dang nhap
 * Ho tro check role va permission
 */
const AuthGuard: React.FC<AuthGuardProps> = ({ children, requiredRole, requiredPermission }) => {
    const router = useRouter();
    const pathname = usePathname();
    const { isAuthenticated, checkAuth } = useAuthStore();
    const { hasRole } = useRole();
    const { hasPermission } = usePermission();

    const [isChecking, setIsChecking] = useState(true);
    const [hasHydrated, setHasHydrated] = useState(false);

    // CRITICAL: Manually rehydrate the store on mount (client-side only)
    useEffect(() => {
        // Rehydrate from localStorage manually because skipHydration is true
        const rehydrate = async () => {
            if (typeof window !== 'undefined') {
                // Use Zustand's persist rehydrate function
                await useAuthStore.persist.rehydrate();
                setHasHydrated(true);
            }
        };
        rehydrate();
    }, []);

    // After hydration, check auth
    useEffect(() => {
        if (!hasHydrated) return;

        const verifyAuth = async () => {
            // Optimimization: If already authenticated in store, trusted for navigation
            // We can do a background check if needed, but for now prevent blocking
            if (isAuthenticated) {
                setIsChecking(false);
                return;
            }

            try {
                await checkAuth();
            } catch (error) {
                console.error('[AuthGuard] Check auth failed', error);
                // If checkAuth throws (e.g. 401), store will likely handle logout
            } finally {
                setIsChecking(false);
            }
        };
        verifyAuth();
    }, [hasHydrated, checkAuth, isAuthenticated]);

    // Redirect if not authenticated AND we are done checking
    useEffect(() => {
        if (hasHydrated && !isChecking && !isAuthenticated && pathname !== '/login' && pathname !== '/auth/login') {
            console.log('[AuthGuard] Redirecting to login. State:', { hasHydrated, isChecking, isAuthenticated, pathname });
            router.push('/auth/login');
        }
    }, [hasHydrated, isChecking, isAuthenticated, router, pathname]);

    // Show loading while checking or hydrating
    if (!hasHydrated || isChecking) {
        return (
            <div className="h-screen w-full flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <Spin size="large" />
                    <div className="mt-4 text-gray-500 font-medium">Loading AIRC System...</div>
                    <div className="text-xs text-gray-400 mt-2">Checking Auth...</div>
                </div>
            </div>
        );
    }

    // Neu chua login thi return null (se redirect boi useEffect)
    if (!isAuthenticated && pathname !== '/login' && pathname !== '/auth/login') {
        return null;
    }

    // --- RBAC CHECKS ---

    // Check Role
    if (requiredRole) {
        const rolesToCheck = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
        const hasRequiredRole = rolesToCheck.some(r => hasRole(r));

        if (!hasRequiredRole) {
            return (
                <div className="h-screen flex items-center justify-center">
                    <Result
                        status="403"
                        title="403"
                        subTitle="Xin lỗi, bạn không có quyền truy cập trang này."
                        extra={<Button type="primary" onClick={() => router.push('/dashboard')}>Về trang chủ</Button>}
                    />
                </div>
            );
        }
    }

    // Check Permission
    if (requiredPermission) {
        const permsToCheck = Array.isArray(requiredPermission) ? requiredPermission : [requiredPermission];
        const hasRequiredPerm = permsToCheck.some(p => hasPermission(p));

        if (!hasRequiredPerm) {
            return (
                <div className="h-screen flex items-center justify-center">
                    <Result
                        status="403"
                        title="403"
                        subTitle="Xin lỗi, bạn không có quyền thực hiện chức năng này."
                        extra={<Button type="primary" onClick={() => router.push('/dashboard')}>Về trang chủ</Button>}
                    />
                </div>
            );
        }
    }

    return <>{children}</>;
};

export default AuthGuard;

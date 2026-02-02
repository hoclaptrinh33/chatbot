import useAuthStore from '@/stores/authStore';

/**
 * Hook để kiểm tra permission của user hiện tại
 * Usage:
 * const { hasPermission } = usePermission();
 * if (hasPermission('users:view')) { ... }
 */
export const usePermission = () => {
    const { permissions, user } = useAuthStore();

    /**
     * Check if user has specific permission
     * Admin role always returns true
     */
    const hasPermission = (permissionCode: string): boolean => {
        // Admin bypass
        if (user?.role === 'admin') return true;

        if (!permissions) return false;

        // Check exact match
        if (permissions.includes(permissionCode)) return true;

        // Check wildcard (e.g., "users:*" matches "users:view")
        const baseResource = permissionCode.split(':')[0];
        if (permissions.includes(`${baseResource}:*`)) return true;

        return false;
    };

    /**
     * Check if user has ANY of the given permissions
     */
    const hasAnyPermission = (permissionCodes: string[]): boolean => {
        return permissionCodes.some(code => hasPermission(code));
    };

    /**
     * Check if user has ALL of the given permissions
     */
    const hasAllPermissions = (permissionCodes: string[]): boolean => {
        return permissionCodes.every(code => hasPermission(code));
    };

    return {
        hasPermission,
        hasAnyPermission,
        hasAllPermissions,
        permissions
    };
};

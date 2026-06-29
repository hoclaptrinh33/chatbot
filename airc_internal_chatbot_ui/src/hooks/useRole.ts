import useAuthStore from '@/stores/authStore';

/**
 * Hook để kiểm tra role của user hiện tại
 * Usage:
 * const { hasRole, isAdmin } = useRole();
 * if (isAdmin) { ... }
 */
export const useRole = () => {
    const { user } = useAuthStore();

    const hasRole = (roleCode: string): boolean => {
        return user?.role === roleCode;
    };

    const isAdmin = user?.role === 'admin';
    const isTeacher = user?.role === 'teacher';
    const isStudent = user?.role === 'student';

    return {
        role: user?.role,
        hasRole,
        isAdmin,
        isTeacher,
        isStudent
    };
};

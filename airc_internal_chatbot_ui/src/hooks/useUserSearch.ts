import { useState, useCallback, useMemo, useEffect } from 'react';
import { User } from '@/services/authService';
import { authService } from '@/services/authService';
import { notification } from 'antd';

interface UseUserSearchOptions {
    token?: string;
}

interface UseUserSearchReturn {
    users: User[];
    filteredUsers: User[];
    searchQuery: string;
    selectedRole: string;
    loading: boolean;
    setSearchQuery: (query: string) => void;
    setSelectedRole: (role: string) => void;
    resetFilters: () => void;
    refetch: () => Promise<void>;
}

/**
 * Hook custom để xử lý tìm kiếm và lọc users
 * 
 * Features:
 * - Fetch users từ backend với filter theo role
 * - Local search theo tên hoặc email
 * - Filter theo vai trò (admin/employee/intern_guest)
 * - Reset filters
 * 
 * @example
 * const { filteredUsers, searchQuery, setSearchQuery, selectedRole, setSelectedRole } = useUserSearch({ token });
 */
export function useUserSearch(options: UseUserSearchOptions): UseUserSearchReturn {
    const { token } = options;
    const [users, setUsers] = useState<User[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedRole, setSelectedRole] = useState<string>('');
    const [loading, setLoading] = useState(false);

    // Fetch users từ backend
    const fetchUsers = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await authService.getAllUsers(token, selectedRole || undefined);
            setUsers(data);
        } catch (error: unknown) {
            console.error('Failed to fetch users:', error);
            notification.error({
                message: 'Loi tai du lieu',
                description: 'Khong the lay danh sach users (chi Admin moi co quyen).',
            });
        } finally {
            setLoading(false);
        }
    }, [token, selectedRole]);

    // Tự động fetch khi token hoặc selectedRole thay đổi
    useEffect(() => {
        fetchUsers();
    }, [fetchUsers]);

    // Lọc users dựa trên searchQuery
    const filteredUsers = useMemo(() => {
        if (!searchQuery) return users;
        
        const query = searchQuery.toLowerCase();
        return users.filter(user => 
            user.full_name.toLowerCase().includes(query) ||
            user.email.toLowerCase().includes(query)
        );
    }, [users, searchQuery]);

    // Reset tất cả filters
    const resetFilters = useCallback(() => {
        setSearchQuery('');
        setSelectedRole('');
    }, []);

    return {
        users,
        filteredUsers,
        searchQuery,
        selectedRole,
        loading,
        setSearchQuery,
        setSelectedRole,
        resetFilters,
        refetch: fetchUsers,
    };
}

export default useUserSearch;

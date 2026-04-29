'use client';

import React, { useEffect, useState } from 'react';
import { Card, notification, Breadcrumb, Button } from 'antd';
import { TeamOutlined, UserAddOutlined } from '@ant-design/icons';
import MainLayout from '@/components/Layout/MainLayout';
import AuthGuard from '@/components/Auth/AuthGuard';
import UserTable from '@/components/Admin/UserTable';
import UserSearchFilter from '@/components/Admin/UserSearchFilter';
import AssignUserRolesModal from '@/components/Admin/AssignUserRolesModal';
import CreateUserModal from '@/components/Admin/CreateUserModal';
import EditUserModal from '@/components/Admin/EditUserModal';
import { authService, User } from '@/services/authService';
import useAuthStore from '@/stores/authStore';
import useUserSearch from '@/hooks/useUserSearch';
import { AxiosError } from 'axios';

/**
 * Trang Quan ly Users (Full CRUD + Roles + Search & Filter)
 */
export default function UsersPage() {
    const { token } = useAuthStore();

    // Use custom hook for search and filter
    const {
        filteredUsers,
        searchQuery,
        selectedRole,
        loading,
        setSearchQuery,
        setSelectedRole,
        resetFilters,
        refetch,
    } = useUserSearch({ token });

    // Modal state
    const [isRoleModalVisible, setIsRoleModalVisible] = useState(false);
    const [isCreateModalVisible, setIsCreateModalVisible] = useState(false);
    const [isEditModalVisible, setIsEditModalVisible] = useState(false);
    const [selectedUser, setSelectedUser] = useState<User | null>(null);

    const handleCreateUser = () => {
        setIsCreateModalVisible(true);
    };

    const handleEditUser = (user: User) => {
        setSelectedUser(user);
        setIsEditModalVisible(true);
    };

    const handleDeleteUser = async (user: User) => {
        if (!token) return;
        try {
            await authService.deleteUser(user.id, token);
            notification.success({ message: 'Da xoa user' });
            refetch();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Loi xoa user',
                description: err.response?.data?.detail || 'Khong the xoa user',
            });
        }
    };

    const handleManageRoles = (user: User) => {
        setSelectedUser(user);
        setIsRoleModalVisible(true);
    };

    return (
        <AuthGuard>
            <MainLayout>
                <div className="mb-6">
                    <Breadcrumb
                        items={[
                            { title: 'Dashboard', href: '/dashboard' },
                            { title: 'Admin' },
                            { title: 'Users' },
                        ]}
                    />

                    <div className="flex justify-between items-center mt-4">
                        <div className="flex items-center gap-3">
                            <TeamOutlined className="text-2xl text-red-700" />
                            <h1 className="text-2xl font-bold m-0">Quan ly Users</h1>
                        </div>
                        <Button
                            type="primary"
                            icon={<UserAddOutlined />}
                            onClick={handleCreateUser}
                            className="bg-red-700 hover:bg-red-800"
                        >
                            Tao User
                        </Button>
                    </div>
                </div>

                <Card bordered={false} className="shadow-sm rounded-lg">
                    {/* Search and Filter Component */}
                    <UserSearchFilter
                        searchQuery={searchQuery}
                        selectedRole={selectedRole}
                        onSearchChange={setSearchQuery}
                        onRoleChange={setSelectedRole}
                        onReset={resetFilters}
                        loading={loading}
                        resultCount={filteredUsers.length}
                    />

                    <UserTable
                        users={filteredUsers}
                        loading={loading}
                        onManageRoles={handleManageRoles}
                        onEditUser={handleEditUser}
                        onDeleteUser={handleDeleteUser}
                    />
                </Card>

                <AssignUserRolesModal
                    visible={isRoleModalVisible}
                    user={selectedUser}
                    onCancel={() => setIsRoleModalVisible(false)}
                    onSuccess={() => {
                        // Roles updated
                    }}
                />

                <CreateUserModal
                    visible={isCreateModalVisible}
                    onCancel={() => setIsCreateModalVisible(false)}
                    onSuccess={() => {
                        setIsCreateModalVisible(false);
                        refetch();
                    }}
                />

                <EditUserModal
                    visible={isEditModalVisible}
                    user={selectedUser}
                    onCancel={() => setIsEditModalVisible(false)}
                    onSuccess={() => {
                        setIsEditModalVisible(false);
                        refetch();
                    }}
                />
            </MainLayout>
        </AuthGuard>
    );
}

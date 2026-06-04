'use client';

import React, { useState } from 'react';
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
        selectedDepartment,
        loading,
        setSearchQuery,
        setSelectedRole,
        setSelectedDepartment,
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
            notification.success({ message: 'Đã xóa người dùng' });
            refetch();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Lỗi xóa người dùng',
                description: err.response?.data?.detail || 'Không thể xóa người dùng',
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
                    {/* Sticky header: breadcrumb + title + search filter */}
                    <div style={{ position: 'sticky', top: 0, zIndex: 10, background: '#f5f5f5', paddingBottom: 16 }}>
                        <div className="mb-4">
                            <Breadcrumb
                                items={[
                                    { title: 'Tổng quan', href: '/dashboard' },
                                    { title: 'Admin' },
                                    { title: 'Người dùng' },
                                ]}
                            />

                            <div className="flex justify-between items-center mt-4">
                                <div className="flex items-center gap-3">
                                    <TeamOutlined className="text-2xl text-red-700" />
                                    <h1 className="text-2xl font-bold m-0">Quản lý người dùng</h1>
                                </div>
                                <Button
                                    type="primary"
                                    icon={<UserAddOutlined />}
                                    onClick={handleCreateUser}
                                    className="bg-red-700 hover:bg-red-800"
                                >
                                    Tạo người dùng
                                </Button>
                            </div>
                    </div>

                        <Card bordered={false} className="shadow-sm rounded-lg">
                            <UserSearchFilter
                                searchQuery={searchQuery}
                                selectedRole={selectedRole}
                                selectedDepartment={selectedDepartment}
                                onSearchChange={setSearchQuery}
                                onRoleChange={setSelectedRole}
                                onDepartmentChange={setSelectedDepartment}
                                onReset={resetFilters}
                                loading={loading}
                                resultCount={filteredUsers.length}
                            />
                        </Card>
                    </div>

                    {/* Scrollable table */}
                    <Card bordered={false} className="shadow-sm rounded-lg">
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

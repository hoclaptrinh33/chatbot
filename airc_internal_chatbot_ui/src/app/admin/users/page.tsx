'use client';

import React, { useEffect, useState } from 'react';
import { Card, notification, Breadcrumb, Button } from 'antd';
import { TeamOutlined, UserAddOutlined } from '@ant-design/icons';
import MainLayout from '@/components/Layout/MainLayout';
import AuthGuard from '@/components/Auth/AuthGuard';
import UserTable from '@/components/Admin/UserTable';
import AssignUserRolesModal from '@/components/Admin/AssignUserRolesModal';
import CreateUserModal from '@/components/Admin/CreateUserModal';
import EditUserModal from '@/components/Admin/EditUserModal';
import { authService, User } from '@/services/authService';
import useAuthStore from '@/stores/authStore';
import { AxiosError } from 'axios';

/**
 * Trang Quan ly Users (Full CRUD + Roles)
 */
export default function UsersPage() {
    const { token } = useAuthStore();
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(false);

    // Modal state
    const [isRoleModalVisible, setIsRoleModalVisible] = useState(false);
    const [isCreateModalVisible, setIsCreateModalVisible] = useState(false);
    const [isEditModalVisible, setIsEditModalVisible] = useState(false);
    const [selectedUser, setSelectedUser] = useState<User | null>(null);

    const fetchUsers = React.useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await authService.getAllUsers(token);
            setUsers(data);
        } catch (error: unknown) {
            console.error(error);
            notification.error({
                message: 'Loi tai du lieu',
                description: 'Khong the lay danh sach users (chi Admin moi co quyen).',
            });
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        fetchUsers();
    }, [fetchUsers]);

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
            fetchUsers();
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
                    <UserTable
                        users={users}
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
                        fetchUsers();
                    }}
                />

                <EditUserModal
                    visible={isEditModalVisible}
                    user={selectedUser}
                    onCancel={() => setIsEditModalVisible(false)}
                    onSuccess={() => {
                        setIsEditModalVisible(false);
                        fetchUsers();
                    }}
                />
            </MainLayout>
        </AuthGuard>
    );
}

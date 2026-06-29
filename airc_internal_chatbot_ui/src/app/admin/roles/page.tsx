'use client';

import React, { useEffect, useState } from 'react';
import { Card, Button, notification, Breadcrumb } from 'antd';
import { AxiosError } from 'axios';
import { PlusOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import MainLayout from '@/components/Layout/MainLayout';
import AuthGuard from '@/components/Auth/AuthGuard';
import RoleTable from '@/components/Admin/RoleTable';
import CreateRoleModal from '@/components/Admin/CreateRoleModal';
import EditRoleModal from '@/components/Admin/EditRoleModal';
import AssignPermissionsModal from '@/components/Admin/AssignPermissionsModal';
import { rbacService, Role } from '@/services/rbacService';
import useAuthStore from '@/stores/authStore';

/**
 * Trang Quan ly Roles
 */
export default function RolesPage() {
    const { token } = useAuthStore();
    const [roles, setRoles] = useState<Role[]>([]);
    const [loading, setLoading] = useState(false);

    // Modals state
    const [isCreateModalVisible, setIsCreateModalVisible] = useState(false);
    const [isAssignModalVisible, setIsAssignModalVisible] = useState(false);
    const [isEditModalVisible, setIsEditModalVisible] = useState(false);
    const [selectedRole, setSelectedRole] = useState<Role | null>(null);

    const fetchRoles = React.useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await rbacService.getRoles();
            setRoles(data);
        } catch {
            notification.error({
                message: 'Loi tai du lieu',
                description: 'Khong the lay danh sach roles.',
            });
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        fetchRoles();
    }, [fetchRoles]);

    const handleDelete = async (id: string) => {
        if (!token) return;
        try {
            await rbacService.deleteRole(id, token);
            notification.success({
                message: 'Xoa thanh cong',
                description: 'Role da duoc xoa.',
            });
            fetchRoles();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Xoa that bai',
                description: err.response?.data?.detail || 'Co loi xay ra.',
            });
        }
    };

    const handleAssignPermissions = (role: Role) => {
        setSelectedRole(role);
        setIsAssignModalVisible(true);
    };

    const handleEdit = (role: Role) => {
        setSelectedRole(role);
        setIsEditModalVisible(true);
    };

    return (
        <AuthGuard>
            <MainLayout>
                <div className="mb-6">
                    <Breadcrumb
                        items={[
                            { title: 'Dashboard', href: '/dashboard' },
                            { title: 'Admin' },
                            { title: 'Roles' },
                        ]}
                    />

                    <div className="flex justify-between items-center mt-4">
                        <div className="flex items-center gap-3">
                            <SafetyCertificateOutlined className="text-2xl text-red-700" />
                            <h1 className="text-2xl font-bold m-0">Quan ly Roles</h1>
                        </div>

                        <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            onClick={() => setIsCreateModalVisible(true)}
                            className="bg-red-700 hover:bg-red-800"
                        >
                            Tao Role
                        </Button>
                    </div>
                </div>

                <Card bordered={false} className="shadow-sm rounded-lg">
                    <RoleTable
                        roles={roles}
                        loading={loading}
                        onDelete={handleDelete}
                        onEdit={handleEdit}
                        onAssignPermissions={handleAssignPermissions}
                    />
                </Card>

                <CreateRoleModal
                    visible={isCreateModalVisible}
                    onCancel={() => setIsCreateModalVisible(false)}
                    onSuccess={() => {
                        setIsCreateModalVisible(false);
                        fetchRoles();
                    }}
                />

                <AssignPermissionsModal
                    visible={isAssignModalVisible}
                    role={selectedRole}
                    onCancel={() => setIsAssignModalVisible(false)}
                    onSuccess={() => {
                        setIsAssignModalVisible(false);
                        fetchRoles(); // Reload to get updated permissions if API returns them
                    }}
                />

                <EditRoleModal
                    visible={isEditModalVisible}
                    role={selectedRole}
                    onCancel={() => setIsEditModalVisible(false)}
                    onSuccess={() => {
                        setIsEditModalVisible(false);
                        fetchRoles();
                    }}
                />
            </MainLayout>
        </AuthGuard>
    );
}

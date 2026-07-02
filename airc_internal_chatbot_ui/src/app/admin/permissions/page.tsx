'use client';

import React, { useEffect, useState } from 'react';
import { Card, Button, notification, Breadcrumb } from 'antd';
import { AxiosError } from 'axios';
import { PlusOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import MainLayout from '@/components/Layout/MainLayout';
import AuthGuard from '@/components/Auth/AuthGuard';
import PermissionTable from '@/components/Admin/PermissionTable';
import EditPermissionModal from '@/components/Admin/EditPermissionModal';
import CreatePermissionModal from '@/components/Admin/CreatePermissionModal';
import { rbacService, Permission } from '@/services/rbacService';
import useAuthStore from '@/stores/authStore';

/**
 * Trang Quan ly Permissions
 * Hien thi danh sach permissions va cac action
 */
export default function PermissionsPage() {
    const { token } = useAuthStore();
    const [permissions, setPermissions] = useState<Permission[]>([]);
    const [loading, setLoading] = useState(false);
    const [isCreateModalVisible, setIsCreateModalVisible] = useState(false);
    const [isEditModalVisible, setIsEditModalVisible] = useState(false);
    const [selectedPermission, setSelectedPermission] = useState<Permission | null>(null);

    // Lay danh sach permissions khi component mount
    const fetchPermissions = React.useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await rbacService.getPermissions(token);
            setPermissions(data);
        } catch (error: unknown) {
            console.error('Fetch permissions error:', error);
            notification.error({
                message: 'Lỗi tải dữ liệu',
                description: 'Không thể lấy danh sách quyền hạn từ server.',
            });
        } finally {
            setLoading(false);
        }
    }, [token]);

    // Lay danh sach permissions khi component mount
    useEffect(() => {
        fetchPermissions();
    }, [fetchPermissions]);

    const handleEdit = (permission: Permission) => {
        setSelectedPermission(permission);
        setIsEditModalVisible(true);
    };

    // Xu ly xoa permission
    const handleDelete = async (id: string) => {
        if (!token) return;
        try {
            await rbacService.deletePermission(id, token);
            notification.success({
                message: 'Xóa thành công',
                description: 'Quyền hạn đã được xóa.',
            });
            fetchPermissions(); // Reload list
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Xóa thất bại',
                description: err.response?.data?.detail || 'Có lỗi xảy ra khi xóa.',
            });
        }
    };

    return (
        <AuthGuard>
            <MainLayout>
                <div className="mb-6">
                    <Breadcrumb
                        items={[
                            { title: 'Dashboard', href: '/dashboard' },
                            { title: 'Admin' },
                            { title: 'Quyền hạn' },
                        ]}
                    />

                    <div className="flex justify-between items-center mt-4">
                        <div className="flex items-center gap-3">
                            <SafetyCertificateOutlined className="text-2xl text-red-700" />
                            <h1 className="text-2xl font-bold m-0">Quản lý quyền hạn</h1>
                        </div>

                        <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            onClick={() => setIsCreateModalVisible(true)}
                            className="bg-red-700 hover:bg-red-800"
                        >
                            Tạo quyền hạn
                        </Button>
                    </div>
                </div>

                <Card bordered={false} className="shadow-sm rounded-lg">
                    <PermissionTable
                        permissions={permissions}
                        loading={loading}
                        onDelete={handleDelete}
                        onEdit={handleEdit}
                    />
                </Card>

                <CreatePermissionModal
                    visible={isCreateModalVisible}
                    onCancel={() => setIsCreateModalVisible(false)}
                    onSuccess={() => {
                        setIsCreateModalVisible(false);
                        fetchPermissions();
                    }}
                />

                <EditPermissionModal
                    visible={isEditModalVisible}
                    permission={selectedPermission}
                    onCancel={() => setIsEditModalVisible(false)}
                    onSuccess={() => {
                        setIsEditModalVisible(false);
                        fetchPermissions();
                    }}
                />
            </MainLayout>
        </AuthGuard>
    );
}

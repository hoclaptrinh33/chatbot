'use client';

import React, { useEffect, useState } from 'react';
import { Card, Button, notification, Breadcrumb, Transfer, Tag, Space, Descriptions } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { useRouter, useParams } from 'next/navigation';
import MainLayout from '@/components/Layout/MainLayout';
import AuthGuard from '@/components/Auth/AuthGuard';
import rbacService, { Role } from '@/services/rbacService';
import useAuthStore from '@/stores/authStore';
import type { TransferDirection } from 'antd/es/transfer';

/**
 * Trang Quan ly Roles cua User
 */
export default function ManageUserRolesPage() {
    const router = useRouter();
    const params = useParams();
    const { token } = useAuthStore();
    const [loading, setLoading] = useState(false);

    // State cho Transfer
    const [allRoles, setAllRoles] = useState<Role[]>([]);
    const [targetKeys, setTargetKeys] = useState<string[]>([]);
    const [selectedKeys, setSelectedKeys] = useState<string[]>([]);

    const userId = params?.id as string;

    useEffect(() => {
        const fetchData = async () => {
            if (!token) return;
            setLoading(true);
            try {
                // 1. Lay tat ca roles
                const roles = await rbacService.getRoles();
                setAllRoles(roles);

                // 2. Lay roles hien tai cua user (TODO: API chua co endpoint get user roles truc tiep neu khong phai me)
                // Tam thoi mock data dua theo user id
                // FIXME: Can bo sung API GET /rbac/users/{id}/roles
                const mockUserRoles = ['teacher'];

                // Map role name -> role id
                const roleIds = roles
                    .filter(r => mockUserRoles.includes(r.name))
                    .map(r => r.id);

                setTargetKeys(roleIds);

            } catch (_error: unknown) {
                notification.error({ message: 'Lỗi tải dữ liệu' });
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [token, userId]);

    // Xu ly thay doi roles
    const handleChange = (newTargetKeys: React.Key[], _direction: TransferDirection, _moveKeys: React.Key[]) => {
        setTargetKeys(newTargetKeys as string[]);
    };

    const handleSelectChange = (sourceSelectedKeys: React.Key[], targetSelectedKeys: React.Key[]) => {
        setSelectedKeys([...sourceSelectedKeys, ...targetSelectedKeys] as string[]);
    };

    const handleSave = async () => {
        if (!token) return;
        setLoading(true);
        try {
            // Goi API assign roles (loop qua tung role de assign hoac API bulk)
            // Hien tai API la POST /rbac/users/{id}/roles (assign single role)
            // Can loop: 
            // 1. Xoa roles cu (neu API support remove) -> Chua co remove
            // 2. Them roles moi

            // FIXME: API hien tai support assign role (add/assign?). Can check ky lai logic backend.
            // Backend: POST /users/{id}/roles -> Assign a role.

            notification.info({
                message: 'Tính năng đang phát triển',
                description: 'Backend cần bổ sung API cập nhật vai trò hàng loạt (bulk update roles)',
            });

        } catch (_error: unknown) {
            notification.error({
                message: 'Lưu thất bại',
                description: 'Có lỗi xảy ra.',
            });
        } finally {
            setLoading(false);
        }
    };

    // Data source cho Transfer
    const dataSource = allRoles.map(role => ({
        key: role.id,
        title: role.name,
        description: role.description,
        tag: role.name === 'admin' ? 'red' : role.name === 'teacher' ? 'blue' : 'green'
    }));

    return (
        <AuthGuard>
            <MainLayout>
                <div className="mb-6">
                    <Breadcrumb
                        items={[
                            { title: 'Dashboard', href: '/dashboard' },
                            { title: 'Admin' },
                            { title: 'Người dùng', href: '/admin/users' },
                            { title: 'Quản lý vai trò' },
                        ]}
                    />

                    <div className="flex items-center gap-4 mt-4">
                        <Button
                            icon={<ArrowLeftOutlined />}
                            onClick={() => router.back()}
                        />
                        <h1 className="text-2xl font-bold m-0">Quản lý vai trò cho người dùng</h1>
                    </div>
                </div>

                <div className="max-w-4xl mx-auto">
                    <Card bordered={false} className="shadow-sm rounded-lg mb-6">
                        <Descriptions title="Thông tin người dùng">
                            <Descriptions.Item label="User ID">{userId}</Descriptions.Item>
                            <Descriptions.Item label="Tên">Nguyễn Văn A (Mock)</Descriptions.Item>
                        </Descriptions>
                    </Card>

                    <Card title="Phân quyền vai trò" bordered={false} className="shadow-sm rounded-lg">
                        <div className="flex justify-center">
                            <Transfer
                                dataSource={dataSource}
                                titles={['Vai trò khả dụng', 'Vai trò đã gán']}
                                targetKeys={targetKeys}
                                selectedKeys={selectedKeys}
                                onChange={handleChange}
                                onSelectChange={handleSelectChange}
                                render={item => (
                                    <Space>
                                        <Tag color={item.tag}>{item.title.toUpperCase()}</Tag>
                                        <span className="text-gray-500 text-xs">{item.description}</span>
                                    </Space>
                                )}
                                listStyle={{
                                    width: 300,
                                    height: 300,
                                }}
                            />
                        </div>

                        <div className="mt-8 text-center">
                            <Button
                                type="primary"
                                icon={<SaveOutlined />}
                                size="large"
                                onClick={handleSave}
                                loading={loading}
                                className="bg-red-700 w-48"
                            >
                                Lưu thay đổi
                            </Button>
                        </div>
                    </Card>
                </div>
            </MainLayout>
        </AuthGuard>
    );
}

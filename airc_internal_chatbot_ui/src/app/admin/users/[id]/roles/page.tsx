'use client';

import React, { useEffect, useState } from 'react';
import { Card, Button, notification, Breadcrumb, Transfer, Tag, Space, Descriptions, Spin } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { useRouter, useParams } from 'next/navigation';
import MainLayout from '@/components/Layout/MainLayout';
import AuthGuard from '@/components/Auth/AuthGuard';
import rbacService, { Role } from '@/services/rbacService';
import authService, { User } from '@/services/authService';
import useAuthStore from '@/stores/authStore';
import type { TransferDirection } from 'antd/es/transfer';

export default function ManageUserRolesPage() {
    const router = useRouter();
    const params = useParams();
    const { token } = useAuthStore();
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [allRoles, setAllRoles] = useState<Role[]>([]);
    const [targetKeys, setTargetKeys] = useState<string[]>([]);
    const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
    const [user, setUser] = useState<User | null>(null);

    const userId = params?.id as string;

    useEffect(() => {
        const fetchData = async () => {
            if (!token || !userId) return;
            setLoading(true);
            try {
                const [roles, userRoles, userInfo] = await Promise.all([
                    rbacService.getRoles(),
                    rbacService.getUserRoles(userId, token),
                    authService.getUser(userId, token),
                ]);
                setAllRoles(roles);
                setUser(userInfo);
                setTargetKeys(userRoles.map((role) => role.id || role._id || '').filter(Boolean));
            } catch (_error: unknown) {
                notification.error({
                    message: 'Lỗi tải dữ liệu',
                    description: 'Không lấy được vai trò hiện tại của người dùng.',
                });
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [token, userId]);

    const handleChange = (newTargetKeys: React.Key[], _direction: TransferDirection, _moveKeys: React.Key[]) => {
        setTargetKeys(newTargetKeys as string[]);
    };

    const handleSelectChange = (sourceSelectedKeys: React.Key[], targetSelectedKeys: React.Key[]) => {
        setSelectedKeys([...sourceSelectedKeys, ...targetSelectedKeys] as string[]);
    };

    const handleSave = async () => {
        if (!token) return;
        setSaving(true);
        try {
            const updated = await rbacService.setUserRoles(userId, targetKeys, token);
            setTargetKeys(updated.map((role) => role.id || role._id || '').filter(Boolean));
            notification.success({
                message: 'Đã cập nhật vai trò',
                description: 'Người dùng cần đăng nhập lại để token phản ánh role mới.',
            });
        } catch (_error: unknown) {
            notification.error({
                message: 'Lưu thất bại',
                description: 'Không thể cập nhật vai trò. Kiểm tra quyền admin và không gán role Admin thủ công.',
            });
        } finally {
            setSaving(false);
        }
    };

    const dataSource = allRoles.map((role) => ({
        key: role.id || role._id || role.code,
        title: role.name,
        description: role.description,
        disabled: role.code === 'admin',
        tag: role.code === 'admin' ? 'red' : role.code === 'teacher' ? 'blue' : 'green',
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
                        <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()} />
                        <h1 className="text-2xl font-bold m-0">Quản lý vai trò cho người dùng</h1>
                    </div>
                </div>

                <Spin spinning={loading}>
                    <div className="max-w-4xl mx-auto">
                        <Card bordered={false} className="shadow-sm rounded-lg mb-6">
                            <Descriptions title="Thông tin người dùng">
                                <Descriptions.Item label="User ID">{userId}</Descriptions.Item>
                                <Descriptions.Item label="Tên">{user?.full_name || '—'}</Descriptions.Item>
                                <Descriptions.Item label="Email">{user?.email || '—'}</Descriptions.Item>
                                <Descriptions.Item label="Role hiện tại">{user?.role || '—'}</Descriptions.Item>
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
                                    render={(item) => (
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
                                    loading={saving}
                                    className="bg-red-700 w-48"
                                >
                                    Lưu thay đổi
                                </Button>
                            </div>
                        </Card>
                    </div>
                </Spin>
            </MainLayout>
        </AuthGuard>
    );
}

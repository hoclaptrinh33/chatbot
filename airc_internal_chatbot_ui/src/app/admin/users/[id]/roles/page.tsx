'use client';

import React, { useEffect, useState } from 'react';
import { Card, Button, notification, Breadcrumb, Transfer, Tag, Space, Descriptions } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { useRouter, useParams } from 'next/navigation';
import MainLayout from '@/components/Layout/MainLayout';
import AuthGuard from '@/components/Auth/AuthGuard';
import rbacService, { Role } from '@/services/rbacService';
import authService from '@/services/authService';
import useAuthStore from '@/stores/authStore';
import type { TransferDirection } from 'antd/es/transfer';

type RoleTransferItem = {
    key: string;
    title: string;
    description?: string;
    tag: string;
};

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
    const [initialTargetKeys, setInitialTargetKeys] = useState<string[]>([]);
    const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
    const [userName, setUserName] = useState<string>('N/A');

    const userId = params?.id as string;

    useEffect(() => {
        const fetchData = async () => {
            if (!token) return;
            setLoading(true);
            try {
                // 1. Lay tat ca roles
                const roles = await rbacService.getRoles();
                setAllRoles(roles);

                // 2. Lay roles hien tai cua user tu API
                const currentRoles = await rbacService.getUserRoles(userId, token);
                const assignedRoleIds = currentRoles
                    .map(r => r.id || r._id)
                    .filter((id): id is string => Boolean(id));
                setTargetKeys(assignedRoleIds);
                setInitialTargetKeys(assignedRoleIds);

                // 3. Lay thong tin user de hien thi ten
                const users = await authService.getAllUsers(token);
                const selectedUser = users.find(u => u.id === userId);
                if (selectedUser) {
                    setUserName(selectedUser.full_name);
                }

            } catch (_error: unknown) {
                notification.error({ message: 'Loi tai du lieu' });
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
        if (!token || !userId) return;

        const rolesToAdd = targetKeys.filter((roleId: string) => !initialTargetKeys.includes(roleId));
        const rolesToRemove = initialTargetKeys.filter((roleId: string) => !targetKeys.includes(roleId));

        if (rolesToAdd.length === 0 && rolesToRemove.length === 0) {
            notification.info({
                message: 'Khong co thay doi',
                description: 'Ban chua thay doi role nao.',
            });
            return;
        }

        setLoading(true);
        try {
            await Promise.all([
                ...rolesToAdd.map((roleId: string) => rbacService.assignRoleToUser(userId, roleId, token)),
                ...rolesToRemove.map((roleId: string) => rbacService.removeRoleFromUser(userId, roleId, token)),
            ]);

            setInitialTargetKeys(targetKeys);
            setSelectedKeys([]);
            notification.success({
                message: 'Luu thanh cong',
                description: `Da them ${rolesToAdd.length} role va xoa ${rolesToRemove.length} role.`,
            });

        } catch (_error: unknown) {
            notification.error({
                message: 'Luu that bai',
                description: 'Co loi xay ra khi cap nhat role.',
            });
        } finally {
            setLoading(false);
        }
    };

    const hasChanges =
        targetKeys.length !== initialTargetKeys.length ||
        targetKeys.some((roleId: string) => !initialTargetKeys.includes(roleId));

    // Data source cho Transfer
    const dataSource: RoleTransferItem[] = allRoles.map((role: Role) => ({
        key: role.id || role._id || '',
        title: role.name,
        description: role.description,
        tag: role.code === 'admin' ? 'red' : role.code === 'employee' ? 'blue' : 'green'
    })).filter((item: RoleTransferItem) => item.key);

    return (
        <AuthGuard>
            <MainLayout>
                <div className="mb-6">
                    <Breadcrumb
                        items={[
                            { title: 'Dashboard', href: '/dashboard' },
                            { title: 'Admin' },
                            { title: 'Users', href: '/admin/users' },
                            { title: 'Quan ly Roles' },
                        ]}
                    />

                    <div className="flex items-center gap-4 mt-4">
                        <Button
                            icon={<ArrowLeftOutlined />}
                            onClick={() => router.back()}
                        />
                        <h1 className="text-2xl font-bold m-0">Quan ly Roles cho User</h1>
                    </div>
                </div>

                <div className="max-w-4xl mx-auto">
                    <Card bordered={false} className="shadow-sm rounded-lg mb-6">
                        <Descriptions title="Thong tin User">
                            <Descriptions.Item label="User ID">{userId}</Descriptions.Item>
                            <Descriptions.Item label="Ten">{userName}</Descriptions.Item>
                        </Descriptions>
                    </Card>

                    <Card title="Phan quyen Roles" bordered={false} className="shadow-sm rounded-lg">
                        <div className="flex justify-center">
                            <Transfer
                                dataSource={dataSource}
                                titles={['Roles Kha dung', 'Roles Da gan']}
                                targetKeys={targetKeys}
                                selectedKeys={selectedKeys}
                                onChange={handleChange}
                                onSelectChange={handleSelectChange}
                                render={(item: RoleTransferItem) => (
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
                                disabled={!hasChanges}
                                className="bg-red-700 w-48"
                            >
                                Luu Thay Doi
                            </Button>
                        </div>
                    </Card>
                </div>
            </MainLayout>
        </AuthGuard>
    );
}

import React, { useEffect, useState } from 'react';
import { Modal, Checkbox, notification, Spin, Tag, Card } from 'antd';
import { AxiosError } from 'axios';
import { rbacService, Role } from '@/services/rbacService';
import { User } from '@/services/authService';
import useAuthStore from '@/stores/authStore';

interface AssignUserRolesModalProps {
    visible: boolean;
    user: User | null;
    onCancel: () => void;
    onSuccess: () => void;
}

const AssignUserRolesModal: React.FC<AssignUserRolesModalProps> = ({
    visible,
    user,
    onCancel,
    onSuccess: _onSuccess
}) => {
    const { token } = useAuthStore();
    const [loading, setLoading] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    const [allRoles, setAllRoles] = useState<Role[]>([]);
    const [userRoles, setUserRoles] = useState<string[]>([]); // IDs of assigned roles

    const fetchData = React.useCallback(async () => {
        if (!token || !user) return;
        setLoading(true);
        try {
            // 1. Get all roles
            const roles = await rbacService.getRoles();
            setAllRoles(roles);

            // 2. Get user's current roles
            const currentRoles = await rbacService.getUserRoles(user.id, token);
            setUserRoles(currentRoles.map(r => r.id || r._id!));

        } catch (_error: unknown) {
            notification.error({
                message: 'Loi tai du lieu',
                description: 'Khong the tai thong tin roles.',
            });
        } finally {
            setLoading(false);
        }
    }, [token, user]);

    useEffect(() => {
        if (visible && user && token) {
            fetchData();
        }
    }, [visible, user, token, fetchData]);

    const handleToggleRole = async (roleId: string, checked: boolean) => {
        if (!token || !user) return;
        setSubmitting(true);
        try {
            if (checked) {
                await rbacService.assignRoleToUser(user.id, roleId, token);
                setUserRoles(prev => [...prev, roleId]);
                notification.success({ message: 'Da them role' });
            } else {
                await rbacService.removeRoleFromUser(user.id, roleId, token);
                setUserRoles(prev => prev.filter(id => id !== roleId));
                notification.success({ message: 'Da xoa role' });
            }
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Loi cap nhat',
                description: err.response?.data?.detail || 'Khong the cap nhat role.',
            });
            // Revert state if failed (optional, but good UX)
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Modal
            title={`Quan ly vai tro cho: ${user?.full_name}`}
            open={visible}
            onCancel={onCancel}
            footer={null} // Direct action on checkbox
            width={600}
        >
            <Spin spinning={loading}>
                <div className="mb-4 text-gray-500">
                    Chon cac vai tro de gan cho nguoi dung nay. Thay doi se duoc luu ngay lap tuc.
                </div>
                <div className="max-h-96 overflow-y-auto">
                    {allRoles.map(role => (
                        <Card
                            key={role.id || role._id}
                            size="small"
                            className="mb-2 hover:bg-gray-50 cursor-pointer"
                        >
                            <Checkbox
                                checked={userRoles.includes(role.id || role._id!)}
                                onChange={(e) => handleToggleRole(role.id || role._id!, e.target.checked)}
                                disabled={submitting || role.code === 'admin'}
                                className="w-full"
                            >
                                <div className="flex justify-between w-full items-center ml-2">
                                    <span className="font-medium text-base">{role.name}</span>
                                    <Tag color={role.is_system ? 'purple' : 'blue'}>
                                        {role.code}
                                    </Tag>
                                </div>
                                <div className="text-gray-500 text-sm ml-2 mt-1">
                                    {role.description}
                                </div>
                            </Checkbox>
                        </Card>
                    ))}
                </div>
            </Spin>
        </Modal>
    );
};

export default AssignUserRolesModal;

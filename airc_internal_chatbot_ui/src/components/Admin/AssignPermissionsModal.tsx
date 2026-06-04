import React, { useEffect, useState } from 'react';
import { Drawer, Button, Space, notification, Spin } from 'antd';
import { AxiosError } from 'axios';
import { rbacService, Role, PermissionMatrixResponse } from '@/services/rbacService';
import useAuthStore from '@/stores/authStore';
import PermissionMatrix from './PermissionMatrix';

interface AssignPermissionsModalProps {
    visible: boolean;
    role: Role | null;
    onCancel: () => void;
    onSuccess: () => void;
}

const AssignPermissionsModal: React.FC<AssignPermissionsModalProps> = ({
    visible,
    role,
    onCancel,
    onSuccess
}) => {
    const { token } = useAuthStore();
    const [loading, setLoading] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    // Matrix State
    const [matrixData, setMatrixData] = useState<PermissionMatrixResponse | null>(null);
    const [localMatrix, setLocalMatrix] = useState<Record<string, string[]>>({});

    const fetchData = React.useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await rbacService.getPermissionMatrix(token);
            setMatrixData(data);
            setLocalMatrix(data.matrix); // Initialize local state
        } catch (_error: unknown) {
            notification.error({
                message: 'Lỗi tải dữ liệu',
                description: 'Không thể tải ma trận phân quyền.',
            });
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        if (visible && role && token) {
            fetchData();
        }
    }, [visible, role, token, fetchData]);

    const handleMatrixChange = (roleCode: string, permissionCode: string, checked: boolean) => {
        setLocalMatrix(prev => {
            const currentPerms = prev[roleCode] || [];
            if (checked) {
                return { ...prev, [roleCode]: [...currentPerms, permissionCode] };
            } else {
                return { ...prev, [roleCode]: currentPerms.filter(c => c !== permissionCode) };
            }
        });
    };

    const handleSubmit = async () => {
        if (!token || !role || !matrixData) return;
        setSubmitting(true);
        try {
            // Find permission IDs from codes (Backend expects IDs)
            const rolePermCodes = localMatrix[role.code] || [];
            const permIds = matrixData.permissions
                .filter(p => rolePermCodes.includes(p.code))
                .map(p => p.id || p._id!);

            await rbacService.assignPermissionsToRole(role.id || role._id!, permIds, token);

            notification.success({
                message: 'Thành công',
                description: `Đã cập nhật permissions cho vai trò ${role.name}`,
            });
            onSuccess();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Lỗi lưu',
                description: err.response?.data?.detail || 'Không thể lưu thay đổi.',
            });
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Drawer
            title={`Phân quyền cho vai trò: ${role?.name} (Dạng ma trận)`}
            placement="right"
            onClose={onCancel}
            open={visible}
            width={1200} // Wide enough for Matrix
            extra={
                <Space>
                    <Button onClick={onCancel}>Hủy</Button>
                    <Button type="primary" onClick={handleSubmit} loading={submitting}>
                        Lưu thay đổi
                    </Button>
                </Space>
            }
        >
            <div className="p-4" style={{ minHeight: '100%' }}>
                {loading || !matrixData ? (
                    <div className="flex justify-center items-center h-64">
                        <Spin tip="Đang tải ma trận..." />
                    </div>
                ) : (
                    <PermissionMatrix
                        roles={matrixData.roles}
                        permissions={matrixData.permissions}
                        matrix={localMatrix}
                        onChange={handleMatrixChange}
                        targetRole={role}
                    />
                )}
            </div>
        </Drawer>
    );
};

export default AssignPermissionsModal;

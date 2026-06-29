import React, { useEffect, useState } from 'react';
import { Modal, Form, Input, notification } from 'antd';
import { AxiosError } from 'axios';
import { rbacService, Permission, CreatePermissionDto } from '@/services/rbacService';
import useAuthStore from '@/stores/authStore';

interface EditPermissionModalProps {
    visible: boolean;
    permission: Permission | null;
    onCancel: () => void;
    onSuccess: () => void;
}

const EditPermissionModal: React.FC<EditPermissionModalProps> = ({
    visible,
    permission,
    onCancel,
    onSuccess
}) => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const { token } = useAuthStore();

    useEffect(() => {
        if (visible && permission) {
            form.setFieldsValue({
                name: permission.name,
                description: permission.description,
                // code, resource, action usually immutable for consistency, but we allow simple metadata edits
            });
        }
    }, [visible, permission, form]);

    const handleSubmit = async (values: CreatePermissionDto) => {
        if (!token || !permission) return;
        setLoading(true);
        try {
            // Only update name and description
            const payload: Partial<CreatePermissionDto> = {
                name: values.name,
                description: values.description
            };

            const id = permission.id || permission._id!;
            await rbacService.updatePermission(id, payload, token);

            notification.success({
                message: 'Thanh cong',
                description: 'Cap nhat permission thanh cong',
            });

            onSuccess();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Loi',
                description: err.response?.data?.detail || 'Khong the update permission',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            title={`Sua Permission: ${permission?.code}`}
            open={visible}
            onCancel={onCancel}
            onOk={form.submit}
            confirmLoading={loading}
            okText="Luu thay doi"
            cancelText="Huy"
        >
            <Form
                form={form}
                layout="vertical"
                onFinish={handleSubmit}
            >
                <Form.Item
                    name="name"
                    label="Ten Permission"
                    rules={[{ required: true, message: 'Vui long nhap ten permission' }]}
                >
                    <Input />
                </Form.Item>

                <Form.Item
                    name="description"
                    label="Mo ta"
                >
                    <Input.TextArea rows={3} />
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default EditPermissionModal;

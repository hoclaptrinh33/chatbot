import React, { useEffect, useState } from 'react';
import { Modal, Form, Input, notification } from 'antd';
import { AxiosError } from 'axios';
import { rbacService, Role, UpdateRoleDto } from '@/services/rbacService';
import useAuthStore from '@/stores/authStore';

interface EditRoleModalProps {
    visible: boolean;
    role: Role | null;
    onCancel: () => void;
    onSuccess: () => void;
}

const EditRoleModal: React.FC<EditRoleModalProps> = ({
    visible,
    role,
    onCancel,
    onSuccess
}) => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const { token } = useAuthStore();

    useEffect(() => {
        if (visible && role) {
            form.setFieldsValue({
                name: role.name,
                description: role.description
            });
        }
    }, [visible, role, form]);

    const handleSubmit = async (values: UpdateRoleDto) => {
        if (!token || !role) return;
        setLoading(true);
        try {
            const payload: UpdateRoleDto = {
                name: values.name,
                description: values.description
            };

            const id = role.id || role._id!;
            await rbacService.updateRole(id, payload, token);

            notification.success({
                message: 'Thanh cong',
                description: 'Cap nhat role thanh cong',
            });

            onSuccess();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Loi',
                description: err.response?.data?.detail || 'Khong the update role',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            title={`Sua Role: ${role?.code}`}
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
                    label="Ten Role"
                    rules={[{ required: true, message: 'Vui long nhap ten role' }]}
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

export default EditRoleModal;

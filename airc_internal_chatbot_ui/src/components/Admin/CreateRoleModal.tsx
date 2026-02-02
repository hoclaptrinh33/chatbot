import React, { useState } from 'react';
import { Modal, Form, Input, notification } from 'antd';
import { AxiosError } from 'axios';
import { rbacService, CreateRoleDto } from '@/services/rbacService';
import useAuthStore from '@/stores/authStore';

interface CreateRoleModalProps {
    visible: boolean;
    onCancel: () => void;
    onSuccess: () => void;
}

const CreateRoleModal: React.FC<CreateRoleModalProps> = ({
    visible,
    onCancel,
    onSuccess
}) => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const { token } = useAuthStore();

    const handleSubmit = async (values: CreateRoleDto) => {
        if (!token) return;
        setLoading(true);
        try {
            // Auto-generate code if not provided (simple slugify)
            const code = values.code || values.name.toLowerCase().replace(/\s+/g, '_');

            const payload: CreateRoleDto = {
                name: values.name,
                code: code,
                description: values.description,
                is_system: false
            };

            await rbacService.createRole(payload, token);

            notification.success({
                message: 'Thanh cong',
                description: 'Tao role moi thanh cong',
            });

            form.resetFields();
            onSuccess();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Loi',
                description: err.response?.data?.detail || 'Khong the tao role',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            title="Tao Role Moi"
            open={visible}
            onCancel={onCancel}
            onOk={form.submit}
            confirmLoading={loading}
            okText="Tao moi"
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
                    <Input placeholder="Vi du: Manager" />
                </Form.Item>

                <Form.Item
                    name="code"
                    label="Code (Unique)"
                    tooltip="Ma dinh danh role (e.g., manager). Tu dong tao neu de trong."
                >
                    <Input placeholder="manager" />
                </Form.Item>

                <Form.Item
                    name="description"
                    label="Mo ta"
                >
                    <Input.TextArea rows={3} placeholder="Mo ta ve role nay" />
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default CreateRoleModal;

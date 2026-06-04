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
                message: 'Thành công',
                description: 'Tạo role mới thành công',
            });

            form.resetFields();
            onSuccess();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Lỗi',
                description: err.response?.data?.detail || 'Không thể tạo role',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            title="Tạo vai trò mới"
            open={visible}
            onCancel={onCancel}
            onOk={form.submit}
            confirmLoading={loading}
            okText="Tạo mới"
            cancelText="Hủy"
        >
            <Form
                form={form}
                layout="vertical"
                onFinish={handleSubmit}
            >
                <Form.Item
                    name="name"
                    label="Tên vai trò"
                    rules={[{ required: true, message: 'Vui lòng nhập tên role' }]}
                >
                    <Input placeholder="Ví dụ: Manager" />
                </Form.Item>

                <Form.Item
                    name="code"
                    label="Mã (duy nhất)"
                    tooltip="Mã định danh vai trò (ví dụ: manager). Tự động tạo nếu để trống."
                >
                    <Input placeholder="manager" />
                </Form.Item>

                <Form.Item
                    name="description"
                    label="Mô tả"
                >
                    <Input.TextArea rows={3} placeholder="Mô tả về Vai trò này" />
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default CreateRoleModal;

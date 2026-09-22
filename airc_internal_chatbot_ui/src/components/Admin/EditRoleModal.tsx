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
                message: 'Thành công',
                description: 'Cập nhật vai trò thành công',
            });

            onSuccess();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Lỗi',
                description: err.response?.data?.detail || 'Không thể cập nhật vai trò',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            title={`Sửa vai trò: ${role?.code}`}
            open={visible}
            onCancel={onCancel}
            onOk={form.submit}
            confirmLoading={loading}
            okText="Lưu thay đổi"
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
                    rules={[{ required: true, message: 'Vui lòng nhập tên vai trò' }]}
                >
                    <Input />
                </Form.Item>

                <Form.Item
                    name="description"
                    label="Mô tả"
                >
                    <Input.TextArea rows={3} />
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default EditRoleModal;

import React, { useEffect, useState } from 'react';
import { Modal, Form, Input, notification, Checkbox } from 'antd';
import { AxiosError } from 'axios';
import { authService, UpdateUserDto, User } from '@/services/authService';
import useAuthStore from '@/stores/authStore';

interface EditUserModalProps {
    visible: boolean;
    user: User | null;
    onCancel: () => void;
    onSuccess: () => void;
}

const EditUserModal: React.FC<EditUserModalProps> = ({
    visible,
    user,
    onCancel,
    onSuccess
}) => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const { token } = useAuthStore();

    useEffect(() => {
        if (visible && user) {
            form.setFieldsValue({
                full_name: user.full_name,
                role: user.role,
                is_active: user.is_active,
                // password fields blank
            });
        }
    }, [visible, user, form]);

    const handleSubmit = async (values: UpdateUserDto) => {
        if (!token || !user) return;
        setLoading(true);
        try {
            const payload: UpdateUserDto = {
                full_name: values.full_name,
                role: values.role, // Usually role is updated via AssignUserRolesModal but this is base role
                is_active: values.is_active,
                password: values.password || undefined // Only send if changed
            };

            await authService.updateUser(user.id, payload, token);

            notification.success({
                message: 'Thanh cong',
                description: 'Cap nhat user thanh cong',
            });

            onSuccess();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Loi',
                description: err.response?.data?.detail || 'Khong the update user',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            title={`Sua User: ${user?.email}`}
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
                    name="full_name"
                    label="Ho va ten"
                    rules={[{ required: true, message: 'Vui long nhap ho ten' }]}
                >
                    <Input />
                </Form.Item>

                <Form.Item
                    name="password"
                    label="Mat khau moi (De trong neu khong doi)"
                >
                    <Input.Password placeholder="Nhap mat khau moi" />
                </Form.Item>

                <Form.Item
                    name="is_active"
                    valuePropName="checked"
                    label="Trang thai hoat dong"
                >
                    <Checkbox>Kich hoat</Checkbox>
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default EditUserModal;

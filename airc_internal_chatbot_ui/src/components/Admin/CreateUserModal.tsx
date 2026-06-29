import React, { useState } from 'react';
import { Modal, Form, Input, Select, notification } from 'antd';
import { AxiosError } from 'axios';
import { authService, CreateUserDto } from '@/services/authService';
import useAuthStore from '@/stores/authStore';

interface CreateUserModalProps {
    visible: boolean;
    onCancel: () => void;
    onSuccess: () => void;
}

const CreateUserModal: React.FC<CreateUserModalProps> = ({
    visible,
    onCancel,
    onSuccess
}) => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const { token } = useAuthStore();

    const handleSubmit = async (values: CreateUserDto) => {
        if (!token) return;
        setLoading(true);
        try {
            const payload: CreateUserDto = {
                email: values.email,
                password: values.password,
                full_name: values.full_name,
                role: values.role
            };

            await authService.createUser(payload, token);

            notification.success({
                message: 'Thanh cong',
                description: 'Tao user moi thanh cong',
            });

            form.resetFields();
            onSuccess();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Loi',
                description: err.response?.data?.detail || 'Khong the tao user',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            title="Tao User Moi"
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
                initialValues={{ role: 'student' }}
            >
                <Form.Item
                    name="email"
                    label="Email"
                    rules={[
                        { required: true, message: 'Vui long nhap email' },
                        { type: 'email', message: 'Email khong hop le' }
                    ]}
                >
                    <Input placeholder="user@example.com" />
                </Form.Item>

                <Form.Item
                    name="full_name"
                    label="Ho va ten"
                    rules={[{ required: true, message: 'Vui long nhap ho ten' }]}
                >
                    <Input placeholder="Nguyen Van A" />
                </Form.Item>

                <Form.Item
                    name="password"
                    label="Mat khau"
                    rules={[{ required: true, message: 'Vui long nhap mat khau', min: 6 }]}
                >
                    <Input.Password placeholder="Password123" />
                </Form.Item>

                <Form.Item
                    name="role"
                    label="Vai tro khoi tao"
                    rules={[{ required: true, message: 'Vui long chon vai tro' }]}
                >
                    <Select>
                        <Select.Option value="student">Student</Select.Option>
                        <Select.Option value="teacher">Teacher</Select.Option>
                        {/* Admin creation disabled via UI to enforce unique admin policy */}
                        {/* <Select.Option value="admin">Admin</Select.Option> */}
                    </Select>
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default CreateUserModal;

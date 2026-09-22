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
                message: 'Thành công',
                description: 'Tạo người dùng mới thành công',
            });

            form.resetFields();
            onSuccess();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Lỗi',
                description: err.response?.data?.detail || 'Không thể tạo người dùng mới',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            title="Tạo người dùng mới"
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
                initialValues={{ role: 'student' }}
            >
                <Form.Item
                    name="email"
                    label="Email"
                    rules={[
                        { required: true, message: 'Vui lòng nhập email' },
                        { type: 'email', message: 'Email không hợp lệ' }
                    ]}
                >
                    <Input placeholder="user@example.com" />
                </Form.Item>

                <Form.Item
                    name="full_name"
                    label="Họ và tên"
                    rules={[{ required: true, message: 'Vui lòng nhập họ tên' }]}
                >
                    <Input placeholder="Nguyễn Văn A" />
                </Form.Item>

                <Form.Item
                    name="password"
                    label="Mật khẩu"
                    rules={[{ required: true, message: 'Vui lòng nhập mật khẩu', min: 6 }]}
                >
                    <Input.Password placeholder="Password123" />
                </Form.Item>

                <Form.Item
                    name="role"
                    label="Vai trò khởi tạo"
                    rules={[{ required: true, message: 'Vui lòng chọn vai trò' }]}
                >
                    <Select>
                        <Select.Option value="student">Sinh viên (Student)</Select.Option>
                        <Select.Option value="teacher">Giáo viên (Teacher)</Select.Option>
                        {/* Admin creation disabled via UI to enforce unique admin policy */}
                        {/* <Select.Option value="admin">Admin</Select.Option> */}
                    </Select>
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default CreateUserModal;

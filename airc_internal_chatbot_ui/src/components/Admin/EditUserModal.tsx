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
                department: user.department,
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
                department: values.department?.trim() || undefined,
                role: values.role, // Usually role is updated via AssignUserRolesModal but this is base role
                is_active: values.is_active,
                password: values.password || undefined // Only send if changed
            };

            await authService.updateUser(user.id, payload, token);

            notification.success({
                message: 'Thành công',
                description: 'Cập nhật người dùng thành công',
            });

            onSuccess();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Lỗi',
                description: err.response?.data?.detail || 'Không thể cập nhật người dùng',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            title={`Sửa người dùng: ${user?.email}`}
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
                    name="full_name"
                    label="Họ và tên"
                    rules={[{ required: true, message: 'Vui lòng nhập họ tên' }]}
                >
                    <Input />
                </Form.Item>

                <Form.Item
                    name="department"
                    label="Phòng ban/Đơn vị"
                >
                    <Input placeholder="Ví dụ: Phòng Kỹ thuật" />
                </Form.Item>

                <Form.Item
                    name="password"
                    label="Mật khẩu mới (để trống nếu không đổi)"
                >
                    <Input.Password placeholder="Nhập mật khẩu mới" />
                </Form.Item>

                <Form.Item
                    name="is_active"
                    valuePropName="checked"
                    label="Trạng thái hoạt động"
                >
                    <Checkbox>Kích hoạt</Checkbox>
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default EditUserModal;

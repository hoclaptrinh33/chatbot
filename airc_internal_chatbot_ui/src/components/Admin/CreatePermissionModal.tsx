import React, { useState } from 'react';
import { Modal, Form, Input, Select, notification } from 'antd';
import { AxiosError } from 'axios';
import { rbacService, CreatePermissionDto } from '@/services/rbacService';
import useAuthStore from '@/stores/authStore';

interface CreatePermissionModalProps {
    visible: boolean;
    onCancel: () => void;
    onSuccess: () => void;
}

const { Option } = Select;

const CreatePermissionModal: React.FC<CreatePermissionModalProps> = ({
    visible,
    onCancel,
    onSuccess
}) => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const { token } = useAuthStore();

    const handleSubmit = async (values: CreatePermissionDto) => {
        if (!token) return;
        setLoading(true);
        try {
            // Auto-generate code if empty or custom logic
            const code = values.code || `${values.resource}:${values.action}`;

            const payload: CreatePermissionDto = {
                name: values.name,
                code: code,
                resource: values.resource,
                action: values.action,
                description: values.description,
                is_system: false // Created via UI is always custom
            };

            await rbacService.createPermission(payload, token);

            notification.success({
                message: 'Thành công',
                description: 'Tạo quyền hạn mới thành công',
            });

            form.resetFields();
            onSuccess();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Lỗi',
                description: err.response?.data?.detail || 'Không thể tạo quyền hạn',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            title="Tạo quyền hạn mới"
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
                initialValues={{
                    resource: 'custom',
                    action: 'view'
                }}
            >
                <Form.Item
                    name="name"
                    label="Tên quyền hạn"
                    rules={[{ required: true, message: 'Vui lòng nhập tên Quyền hạn' }]}
                >
                    <Input placeholder="Ví dụ: Xem báo cáo tùy chỉnh" />
                </Form.Item>

                <Form.Item
                    name="code"
                    label="Mã quyền hạn (duy nhất)"
                    tooltip="Tài nguyên:Hành vi (ví dụ: reports:view). Nếu để trống sẽ tự động tạo."
                >
                    <Input placeholder="reports:view" />
                </Form.Item>

                <div className="grid grid-cols-2 gap-4">
                    <Form.Item
                        name="resource"
                        label="Tài nguyên"
                        rules={[{ required: true }]}
                    >
                        <Select showSearch allowClear>
                            <Option value="users">Người dùng</Option>
                            <Option value="roles">Vai trò</Option>
                            <Option value="datasets">Dataset</Option>
                            <Option value="chatbots">Chatbot</Option>
                            <Option value="chat">Chat</Option>
                            <Option value="custom">Tùy chỉnh</Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="action"
                        label="Hành vi"
                        rules={[{ required: true }]}
                    >
                        <Select>
                            <Option value="view">Xem</Option>
                            <Option value="create">Tạo</Option>
                            <Option value="update">Cập nhật</Option>
                            <Option value="delete">Xóa</Option>
                            <Option value="manage">Quản lý</Option>
                            <Option value="use">Sử dụng</Option>
                        </Select>
                    </Form.Item>
                </div>

                <Form.Item
                    name="description"
                    label="Mô tả"
                >
                    <Input.TextArea rows={3} placeholder="Mô tả chi tiết về quyền hạn này" />
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default CreatePermissionModal;

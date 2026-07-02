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
                description: err.response?.data?.detail || 'Không thể tạo quyền hạn mới',
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
                    rules={[{ required: true, message: 'Vui lòng nhập tên quyền hạn' }]}
                >
                    <Input placeholder="Ví dụ: Xem báo cáo tùy chỉnh" />
                </Form.Item>

                <Form.Item
                    name="code"
                    label="Mã quyền hạn (Duy nhất)"
                    tooltip="Đối tượng:Thao tác (ví dụ: reports:view). Nếu để trống sẽ tự động tạo."
                >
                    <Input placeholder="reports:view" />
                </Form.Item>

                <div className="grid grid-cols-2 gap-4">
                    <Form.Item
                        name="resource"
                        label="Đối tượng (Resource)"
                        rules={[{ required: true }]}
                    >
                        <Select showSearch allowClear>
                            <Option value="users">Users</Option>
                            <Option value="roles">Roles</Option>
                            <Option value="datasets">Datasets</Option>
                            <Option value="chatbots">Chatbots</Option>
                            <Option value="chat">Chat</Option>
                            <Option value="custom">Custom</Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="action"
                        label="Thao tác (Action)"
                        rules={[{ required: true }]}
                    >
                        <Select>
                            <Option value="view">View</Option>
                            <Option value="create">Create</Option>
                            <Option value="update">Update</Option>
                            <Option value="delete">Delete</Option>
                            <Option value="manage">Manage</Option>
                            <Option value="use">Use</Option>
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

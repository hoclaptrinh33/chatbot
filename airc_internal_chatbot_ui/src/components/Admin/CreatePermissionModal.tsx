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
                message: 'Thanh cong',
                description: 'Tao permission khac thanh cong',
            });

            form.resetFields();
            onSuccess();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Loi',
                description: err.response?.data?.detail || 'Khong the tao permission',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            title="Tao Permission Moi"
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
                initialValues={{
                    resource: 'custom',
                    action: 'view'
                }}
            >
                <Form.Item
                    name="name"
                    label="Ten Permission"
                    rules={[{ required: true, message: 'Vui long nhap ten permission' }]}
                >
                    <Input placeholder="Vi du: View Custom Reports" />
                </Form.Item>

                <Form.Item
                    name="code"
                    label="Permission Code (Unique)"
                    tooltip="Resource:Action (e.g., reports:view). Neu de trong se tu dong tao."
                >
                    <Input placeholder="reports:view" />
                </Form.Item>

                <div className="grid grid-cols-2 gap-4">
                    <Form.Item
                        name="resource"
                        label="Resource"
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
                        label="Action"
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
                    label="Mo ta"
                >
                    <Input.TextArea rows={3} placeholder="Mo ta chi tiet ve quyen han nay" />
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default CreatePermissionModal;

'use client';

import React, { useState } from 'react';
import { Card, Form, Input, Button, Select, notification, Breadcrumb, Space } from 'antd';
import { AxiosError } from 'axios';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import MainLayout from '@/components/Layout/MainLayout';
import AuthGuard from '@/components/Auth/AuthGuard';
import rbacService, { CreatePermissionDto } from '@/services/rbacService';
import useAuthStore from '@/stores/authStore';

const { TextArea } = Input;

/**
 * Trang Tao Permission moi
 */
export default function CreatePermissionPage() {
    const router = useRouter();
    const { token } = useAuthStore();
    const [loading, setLoading] = useState(false);
    const [form] = Form.useForm();

    const onFinish = async (values: CreatePermissionDto) => {
        if (!token) return;
        setLoading(true);
        try {
            await rbacService.createPermission(values, token);
            notification.success({
                message: 'Tạo thành công',
                description: `Quyền hạn "${values.name}" đã được tạo.`,
            });
            router.push('/admin/permissions');
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Tạo thất bại',
                description: err.response?.data?.detail || 'Có lỗi xảy ra.',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthGuard>
            <MainLayout>
                <div className="mb-6">
                    <Breadcrumb
                        items={[
                            { title: 'Tổng quan', href: '/dashboard' },
                            { title: 'Admin' },
                            { title: 'Quyền hạn', href: '/admin/permissions' },
                            { title: 'Tạo mới' },
                        ]}
                    />

                    <div className="flex items-center gap-4 mt-4">
                        <Button
                            icon={<ArrowLeftOutlined />}
                            onClick={() => router.back()}
                        />
                        <h1 className="text-2xl font-bold m-0">Tạo quyền hạn mới</h1>
                    </div>
                </div>

                <div className="max-w-3xl mx-auto">
                    <Card bordered={false} className="shadow-sm rounded-lg">
                        <Form
                            form={form}
                            layout="vertical"
                            onFinish={onFinish}
                            initialValues={{
                                action: 'read',
                                resource: 'dataset'
                            }}
                        >
                            <Form.Item
                                name="name"
                                label="Tên quyền hạn"
                                rules={[{ required: true, message: 'Vui lòng nhập tên permission' }]}
                                help="Ví dụ: dataset:create, chatbot:use"
                            >
                                <Input placeholder="Nhập tên permission duy nhất" />
                            </Form.Item>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <Form.Item
                                    name="resource"
                                    label="Tài nguyên"
                                    rules={[{ required: true, message: 'Vui lòng chọn resource' }]}
                                >
                                    <Select>
                                        <Select.Option value="auth">Hệ thống Auth</Select.Option>
                                        <Select.Option value="rbac">Hệ thống RBAC</Select.Option>
                                        <Select.Option value="dataset">Dataset</Select.Option>
                                        <Select.Option value="chatbot">Chatbot</Select.Option>
                                        <Select.Option value="chat">Hệ thống chat</Select.Option>
                                        <Select.Option value="system">Lõi hệ thống</Select.Option>
                                    </Select>
                                </Form.Item>

                                <Form.Item
                                    name="action"
                                    label="Hành vi"
                                    rules={[{ required: true, message: 'Vui lòng chọn action' }]}
                                >
                                    <Select>
                                        <Select.Option value="create">Tạo</Select.Option>
                                        <Select.Option value="read">Đọc</Select.Option>
                                        <Select.Option value="update">Cập nhật</Select.Option>
                                        <Select.Option value="delete">Xóa</Select.Option>
                                        <Select.Option value="manage">Toàn quyền</Select.Option>
                                    </Select>
                                </Form.Item>
                            </div>

                            <Form.Item
                                name="description"
                                label="Mô tả"
                            >
                                <TextArea rows={4} placeholder="Mô tả chi tiết về Quyền này" />
                            </Form.Item>

                            <Form.Item className="mb-0 text-right">
                                <Space>
                                    <Button onClick={() => router.back()}>
                                        Hủy
                                    </Button>
                                    <Button
                                        type="primary"
                                        htmlType="submit"
                                        loading={loading}
                                        icon={<SaveOutlined />}
                                        className="bg-red-700"
                                    >
                                        Lưu quyền hạn
                                    </Button>
                                </Space>
                            </Form.Item>
                        </Form>
                    </Card>
                </div>
            </MainLayout>
        </AuthGuard>
    );
}

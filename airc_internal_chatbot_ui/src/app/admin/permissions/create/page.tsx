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
                message: 'Tao thanh cong',
                description: `Permission "${values.name}" da duoc tao.`,
            });
            router.push('/admin/permissions');
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            notification.error({
                message: 'Tao that bai',
                description: err.response?.data?.detail || 'Co loi xay ra.',
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
                            { title: 'Dashboard', href: '/dashboard' },
                            { title: 'Admin' },
                            { title: 'Permissions', href: '/admin/permissions' },
                            { title: 'Tao moi' },
                        ]}
                    />

                    <div className="flex items-center gap-4 mt-4">
                        <Button
                            icon={<ArrowLeftOutlined />}
                            onClick={() => router.back()}
                        />
                        <h1 className="text-2xl font-bold m-0">Tao Permission Moi</h1>
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
                                label="Ten Permission"
                                rules={[{ required: true, message: 'Vui long nhap ten permission' }]}
                                help="Vi du: dataset:create, chatbot:use"
                            >
                                <Input placeholder="Nhap ten permission unique" />
                            </Form.Item>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <Form.Item
                                    name="resource"
                                    label="Resource (Tai nguyen)"
                                    rules={[{ required: true, message: 'Vui long chon resource' }]}
                                >
                                    <Select>
                                        <Select.Option value="auth">Auth System</Select.Option>
                                        <Select.Option value="rbac">RBAC System</Select.Option>
                                        <Select.Option value="dataset">Dataset</Select.Option>
                                        <Select.Option value="chatbot">Chatbot</Select.Option>
                                        <Select.Option value="chat">Chat System</Select.Option>
                                        <Select.Option value="system">System Core</Select.Option>
                                    </Select>
                                </Form.Item>

                                <Form.Item
                                    name="action"
                                    label="Action (Hanh dong)"
                                    rules={[{ required: true, message: 'Vui long chon action' }]}
                                >
                                    <Select>
                                        <Select.Option value="create">Create</Select.Option>
                                        <Select.Option value="read">Read</Select.Option>
                                        <Select.Option value="update">Update</Select.Option>
                                        <Select.Option value="delete">Delete</Select.Option>
                                        <Select.Option value="manage">Manage (Full)</Select.Option>
                                    </Select>
                                </Form.Item>
                            </div>

                            <Form.Item
                                name="description"
                                label="Mo ta"
                            >
                                <TextArea rows={4} placeholder="Mo ta chi tiet ve permission nay" />
                            </Form.Item>

                            <Form.Item className="mb-0 text-right">
                                <Space>
                                    <Button onClick={() => router.back()}>
                                        Huy
                                    </Button>
                                    <Button
                                        type="primary"
                                        htmlType="submit"
                                        loading={loading}
                                        icon={<SaveOutlined />}
                                        className="bg-red-700"
                                    >
                                        Luu Permission
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

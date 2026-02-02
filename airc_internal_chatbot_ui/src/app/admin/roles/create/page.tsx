'use client';

import React, { useState } from 'react';
import { Card, Form, Input, Button, notification, Breadcrumb, Space } from 'antd';
import { AxiosError } from 'axios';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import MainLayout from '@/components/Layout/MainLayout';
import AuthGuard from '@/components/Auth/AuthGuard';
import rbacService, { CreateRoleDto } from '@/services/rbacService';
import useAuthStore from '@/stores/authStore';

const { TextArea } = Input;

/**
 * Trang Tao Role moi
 */
export default function CreateRolePage() {
    const router = useRouter();
    const { token } = useAuthStore();
    const [loading, setLoading] = useState(false);
    const [form] = Form.useForm();

    const onFinish = async (values: CreateRoleDto) => {
        if (!token) return;
        setLoading(true);
        try {
            await rbacService.createRole(values, token);
            notification.success({
                message: 'Tao thanh cong',
                description: `Role "${values.name}" da duoc tao.`,
            });
            router.push('/admin/roles');
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
                            { title: 'Roles', href: '/admin/roles' },
                            { title: 'Tao moi' },
                        ]}
                    />

                    <div className="flex items-center gap-4 mt-4">
                        <Button
                            icon={<ArrowLeftOutlined />}
                            onClick={() => router.back()}
                        />
                        <h1 className="text-2xl font-bold m-0">Tao Role Moi</h1>
                    </div>
                </div>

                <div className="max-w-3xl mx-auto">
                    <Card bordered={false} className="shadow-sm rounded-lg">
                        <Form
                            form={form}
                            layout="vertical"
                            onFinish={onFinish}
                        >
                            <Form.Item
                                name="name"
                                label="Ten Role"
                                rules={[{ required: true, message: 'Vui long nhap ten role' }]}
                                help="Vi du: editor, viewer"
                            >
                                <Input placeholder="Nhap ten role unique" />
                            </Form.Item>

                            <Form.Item
                                name="description"
                                label="Mo ta"
                            >
                                <TextArea rows={4} placeholder="Mo ta chi tiet ve role nay" />
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
                                        Luu Role
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

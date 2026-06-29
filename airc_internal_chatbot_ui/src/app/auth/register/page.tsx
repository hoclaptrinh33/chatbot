'use client';

import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, Alert, message } from 'antd';

import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { AxiosError } from 'axios';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { authRepository } from '@/infrastructure/repositories/AuthRepository';
import { UserRole } from '@/core/entities/User';

const { Title, Text } = Typography;

export default function RegisterPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const onFinish = async (values: Record<string, string>) => {
        setLoading(true);
        setError(null);
        try {
            await authRepository.register({
                email: values.email,
                password: values.password,
                full_name: values.fullName,
                role: UserRole.STUDENT, // Mac dinh la Sinh vien (Student)
            });
            message.success('Đăng ký thành công! Vui lòng đăng nhập.');
            router.push('/auth/login');
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            console.error(err);
            setError(err.response?.data?.detail || 'Đăng ký thất bại. Vui lòng thử lại.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="shadow-lg border-0">
            <div className="text-center mb-6">
                {/* Logo AIRC */}
                <div className="flex justify-center mb-4 relative h-16 w-full">
                    <Image
                        src="/logo_airc.jpg"
                        alt="AIRC Logo"
                        fill
                        className="object-contain"
                        priority
                        sizes="(max-width: 768px) 100vw, 33vw"
                    />
                </div>
                <Title level={2} style={{ color: '#c82b2b' }}>Đăng Ký</Title>
                <Text type="secondary">Tạo tài khoản mới</Text>
            </div>

            {error && (
                <Alert
                    message="Lỗi đăng ký"
                    description={error}
                    type="error"
                    showIcon
                    className="mb-4"
                />
            )}

            <Form
                name="register_form"
                onFinish={onFinish}
                layout="vertical"
                size="large"
                initialValues={{ role: UserRole.STUDENT }}
            >
                <Form.Item
                    name="email"
                    rules={[
                        { required: true, message: 'Vui lòng nhập Email!' },
                        { type: 'email', message: 'Email không hợp lệ!' },
                    ]}
                >
                    <Input
                        prefix={<MailOutlined className="site-form-item-icon" />}
                        placeholder="Email"
                    />
                </Form.Item>

                <Form.Item
                    name="fullName"
                    rules={[{ required: true, message: 'Vui lòng nhập họ tên!' }]}
                >
                    <Input
                        prefix={<UserOutlined className="site-form-item-icon" />}
                        placeholder="Họ và tên"
                    />
                </Form.Item>

                <Form.Item
                    name="password"
                    rules={[
                        { required: true, message: 'Vui lòng nhập mật khẩu!' },
                        { min: 6, message: 'Mật khẩu phải có ít nhất 6 ký tự!' }
                    ]}
                >
                    <Input.Password
                        prefix={<LockOutlined className="site-form-item-icon" />}
                        placeholder="Mật khẩu"
                    />
                </Form.Item>

                <Form.Item
                    name="confirmPassword"
                    dependencies={['password']}
                    hasFeedback
                    rules={[
                        { required: true, message: 'Vui lòng xác nhận mật khẩu!' },
                        ({ getFieldValue }) => ({
                            validator(_, value) {
                                if (!value || getFieldValue('password') === value) {
                                    return Promise.resolve();
                                }
                                return Promise.reject(new Error('Mật khẩu xác nhận không khớp!'));
                            },
                        }),
                    ]}
                >
                    <Input.Password
                        prefix={<LockOutlined className="site-form-item-icon" />}
                        placeholder="Xác nhận mật khẩu"
                    />
                </Form.Item>

                {/* Role selection removed - Defaults to Student */}
                {/* <Form.Item name="role" label="Vai trò (Testing)" hidden>
                    <Select>
                        <Option value={UserRole.STUDENT}>Sinh viên</Option>
                    </Select>
                </Form.Item> */}

                <Form.Item>
                    <Button type="primary" htmlType="submit" className="w-full" loading={loading}>
                        Đăng ký
                    </Button>
                </Form.Item>

                <div className="text-center mt-4">
                    <Text>Đã có tài khoản? </Text>
                    <Link href="/auth/login" style={{ color: '#c61a1a', fontWeight: 500 }}>
                        Đăng nhập ngay
                    </Link>
                </div>
            </Form>
        </Card>
    );
}

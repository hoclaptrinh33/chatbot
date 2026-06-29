'use client';

import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Checkbox, Card, Typography, Alert, message } from 'antd';
import { LockOutlined, MailOutlined } from '@ant-design/icons';
import { AxiosError } from 'axios';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import useAuthStore from '@/stores/authStore';

const { Title, Text } = Typography;

/**
 * Trang Dang nhap cho Admin/Teacher/Student
 * Su dung store @/stores/authStore (CHINH XAC)
 */
export default function LoginPage() {
    const router = useRouter();
    const { login, isLoading, error, isAuthenticated } = useAuthStore();
    const [formError, setFormError] = useState<string | null>(null);

    // Redirect neu da login
    useEffect(() => {
        if (isAuthenticated) {
            console.log('[LoginPage] Already authenticated, redirecting to dashboard');
            router.push('/dashboard');
        }
    }, [isAuthenticated, router]);

    const onFinish = async (values: Record<string, string>) => {
        setFormError(null);
        try {
            console.log('[LoginPage] Attempting login...');
            await login(values.email, values.password);

            // QUAN TRONG: Hien thi notification o component level
            // Khong dung message trong store vi khong co React context
            message.success('Đăng nhập thành công!');

            console.log('[LoginPage] Login successful! isAuthenticated will trigger redirect');
            // Redirect se duoc xu ly boi useEffect khi isAuthenticated = true
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string | Record<string, string> }>;
            console.error('[LoginPage] Login error:', err);

            // Xu ly error message an toan
            let errorMessage = 'Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.';

            if (err.response?.data?.detail) {
                errorMessage = typeof err.response.data.detail === 'string'
                    ? err.response.data.detail
                    : JSON.stringify(err.response.data.detail);
            } else if (err.response?.status === 401) {
                errorMessage = 'Email hoặc mật khẩu không đúng!';
            } else if (err.response?.status === 404) {
                errorMessage = 'Không tìm thấy tài khoản này!';
            } else if (err.code === 'ERR_NETWORK') {
                errorMessage = 'Không thể kết nối đến server!';
            } else if (err.message) {
                errorMessage = err.message;
            }

            setFormError(errorMessage);
            // Removed message.error(errorMessage) as requested - displaying inline Alert only
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
            <div className="max-w-md w-full">
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
                        <Title level={2} style={{ color: '#c82b2b' }}>AIRC Internal Chatbot</Title>
                        <Text type="secondary">Đăng nhập vào hệ thống nội bộ</Text>
                    </div>

                    {(error || formError) && (
                        <Alert
                            message="Lỗi đăng nhập"
                            description={formError || error || 'Đăng nhập thất bại'}
                            type="error"
                            showIcon
                            className="mb-4"
                        />
                    )}

                    <Form
                        name="login_form"
                        onFinish={onFinish}
                        layout="vertical"
                        size="large"
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
                            name="password"
                            rules={[{ required: true, message: 'Vui lòng nhập mật khẩu!' }]}
                        >
                            <Input.Password
                                prefix={<LockOutlined className="site-form-item-icon" />}
                                placeholder="Mật khẩu"
                            />
                        </Form.Item>

                        <Form.Item>
                            <Form.Item name="remember" valuePropName="checked" noStyle>
                                <Checkbox>Ghi nhớ đăng nhập</Checkbox>
                            </Form.Item>
                        </Form.Item>

                        <Form.Item>
                            <Button type="primary" htmlType="submit" className="w-full" loading={isLoading}>
                                Đăng nhập
                            </Button>
                        </Form.Item>

                        <div className="text-center mt-4">
                            <Text>Chưa có tài khoản? </Text>
                            <Link href="/auth/register" style={{ color: '#c61a1a', fontWeight: 500 }}>
                                Đăng ký ngay
                            </Link>
                        </div>
                    </Form>
                </Card>
            </div>
        </div>
    );
}

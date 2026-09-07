'use client';

import React, { useMemo, useState } from 'react';
import { Form, Input, Button, Card, Typography, Alert } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { AxiosError } from 'axios';
import { Suspense } from 'react';
import authService from '@/services/authService';

const { Title, Text } = Typography;

function ResetPasswordForm() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const token = useMemo(() => searchParams.get('token') || '', [searchParams]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [done, setDone] = useState(false);

    const onFinish = async (values: { password: string }) => {
        if (!token) {
            setError('Thiếu token đặt lại mật khẩu.');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            await authService.resetPassword(token, values.password);
            setDone(true);
            setTimeout(() => router.push('/auth/login'), 1500);
        } catch (err: unknown) {
            const axiosErr = err as AxiosError<{ detail: string }>;
            setError(axiosErr.response?.data?.detail || 'Không đặt lại được mật khẩu.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="shadow-lg border-0">
            <div className="text-center mb-6">
                <div className="flex justify-center mb-4 relative h-16 w-full">
                    <Image src="/logo_airc.jpg" alt="AIRC Logo" fill className="object-contain" />
                </div>
                <Title level={3} style={{ color: '#c82b2b' }}>Đặt lại mật khẩu</Title>
                <Text type="secondary">Nhập mật khẩu mới cho tài khoản của bạn</Text>
            </div>

            {!token && (
                <Alert type="error" showIcon className="mb-4" message="Liên kết không hợp lệ hoặc thiếu token." />
            )}
            {error && <Alert type="error" showIcon className="mb-4" message={error} />}
            {done && (
                <Alert type="success" showIcon className="mb-4" message="Đặt lại thành công. Đang chuyển tới trang đăng nhập..." />
            )}

            <Form layout="vertical" size="large" onFinish={onFinish} disabled={!token || done}>
                <Form.Item
                    name="password"
                    rules={[
                        { required: true, message: 'Vui lòng nhập mật khẩu mới!' },
                        { min: 8, message: 'Mật khẩu tối thiểu 8 ký tự' },
                    ]}
                >
                    <Input.Password prefix={<LockOutlined />} placeholder="Mật khẩu mới" />
                </Form.Item>
                <Form.Item
                    name="confirm"
                    dependencies={['password']}
                    rules={[
                        { required: true, message: 'Xác nhận mật khẩu!' },
                        ({ getFieldValue }) => ({
                            validator(_, value) {
                                if (!value || getFieldValue('password') === value) {
                                    return Promise.resolve();
                                }
                                return Promise.reject(new Error('Mật khẩu xác nhận không khớp'));
                            },
                        }),
                    ]}
                >
                    <Input.Password prefix={<LockOutlined />} placeholder="Xác nhận mật khẩu" />
                </Form.Item>
                <Form.Item>
                    <Button type="primary" htmlType="submit" className="w-full" loading={loading}>
                        Cập nhật mật khẩu
                    </Button>
                </Form.Item>
            </Form>

            <div className="text-center">
                <Link href="/auth/login" style={{ color: '#c61a1a' }}>Quay lại đăng nhập</Link>
            </div>
        </Card>
    );
}

export default function ResetPasswordPage() {
    return (
        <Suspense fallback={<Card loading />}>
            <ResetPasswordForm />
        </Suspense>
    );
}

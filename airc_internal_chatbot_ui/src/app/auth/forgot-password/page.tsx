'use client';

import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, Alert, message } from 'antd';
import { MailOutlined } from '@ant-design/icons';
import Image from 'next/image';
import Link from 'next/link';
import { AxiosError } from 'axios';
import authService from '@/services/authService';

const { Title, Text } = Typography;

export default function ForgotPasswordPage() {
    const [loading, setLoading] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const onFinish = async (values: { email: string }) => {
        setLoading(true);
        setError(null);
        try {
            await authService.forgotPassword(values.email);
            setSent(true);
            message.success('Nếu email tồn tại, hướng dẫn đã được gửi.');
        } catch (err: unknown) {
            const axiosErr = err as AxiosError<{ detail: string }>;
            setError(axiosErr.response?.data?.detail || 'Không gửi được yêu cầu. Thử lại sau.');
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
                <Title level={3} style={{ color: '#c82b2b' }}>Quên mật khẩu</Title>
                <Text type="secondary">Nhập email để nhận liên kết đặt lại mật khẩu</Text>
            </div>

            {error && <Alert type="error" showIcon className="mb-4" message={error} />}
            {sent && (
                <Alert
                    type="success"
                    showIcon
                    className="mb-4"
                    message="Yêu cầu đã được ghi nhận"
                    description="Nếu email tồn tại trong hệ thống, bạn sẽ nhận được hướng dẫn. Trong môi trường dev, kiểm tra log Auth service để lấy liên kết."
                />
            )}

            <Form layout="vertical" size="large" onFinish={onFinish}>
                <Form.Item
                    name="email"
                    rules={[
                        { required: true, message: 'Vui lòng nhập Email!' },
                        { type: 'email', message: 'Email không hợp lệ!' },
                    ]}
                >
                    <Input prefix={<MailOutlined />} placeholder="Email" />
                </Form.Item>
                <Form.Item>
                    <Button type="primary" htmlType="submit" className="w-full" loading={loading}>
                        Gửi liên kết
                    </Button>
                </Form.Item>
            </Form>

            <div className="text-center">
                <Link href="/auth/login" style={{ color: '#c61a1a' }}>Quay lại đăng nhập</Link>
            </div>
        </Card>
    );
}

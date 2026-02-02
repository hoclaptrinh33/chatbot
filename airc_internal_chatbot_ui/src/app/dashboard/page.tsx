'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Row, Col, Typography, Space, Avatar, Divider, Spin, message } from 'antd';
import {
    TeamOutlined,
    DatabaseOutlined,
    MessageOutlined,
    RobotOutlined,
    ClockCircleOutlined,
    ThunderboltOutlined,
    LoadingOutlined
} from '@ant-design/icons';
import AuthGuard from '@/components/Auth/AuthGuard';
import useAuthStore from '@/stores/authStore';
import statsService, { DashboardStats, RecentActivity } from '@/services/statsService';
import Image from 'next/image';

const { Title, Text } = Typography;

/**
 * Trang Dashboard chinh
 * Hien thi tong quan he thong
 * Duoc bao ve boi AuthGuard
 * 
 * QUAN TRONG: KHONG wrap voi MainLayout o day
 * Vi dashboard/layout.tsx da wrap tat ca children voi MainLayout roi
 */
export default function DashboardPage() {
    const { user } = useAuthStore();
    const [mounted, setMounted] = useState(false);
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [activities, setActivities] = useState<RecentActivity[]>([]);

    const router = useRouter();

    // Fetch dashboard data
    const fetchDashboardData = async () => {
        try {
            setLoading(true);
            const [statsData, activityData] = await Promise.all([
                statsService.getDashboardStats(),
                statsService.getRecentActivity(5)
            ]);
            setStats(statsData);
            setActivities(activityData);
        } catch (error) {
            console.error('Failed to fetch dashboard data:', error);
            message.error('Không thể tải dữ liệu dashboard');
        } finally {
            setLoading(false);
        }
    };

    // CRITICAL: Chi render user name khi da mount (client-side)
    // De tranh hydration mismatch
    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setMounted(true);
        if (user?.role === 'student') {
            router.push('/dashboard/chat');
        } else {
            fetchDashboardData();
        }
    }, [user, router]);

    if (user?.role === 'student') return null; // Prevent flash of dashboard content

    // Helper function to format time ago
    const formatTimeAgo = (timestamp: string) => {
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now.getTime() - time.getTime();
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);

        if (diffDays > 0) return `${diffDays} ngày trước`;
        if (diffHours > 0) return `${diffHours} giờ trước`;
        return 'Vừa xong';
    };

    // Get icon for activity type
    const getActivityIcon = (type: string) => {
        switch (type) {
            case 'chatbot': return <RobotOutlined />;
            case 'dataset': return <DatabaseOutlined />;
            case 'conversation': return <MessageOutlined />;
            default: return <ClockCircleOutlined />;
        }
    };

    // Get icon color for activity type
    const getActivityColor = (type: string) => {
        switch (type) {
            case 'chatbot': return '#10b981';
            case 'dataset': return '#3b82f6';
            case 'conversation': return '#8b5cf6';
            default: return '#6b7280';
        }
    };

    return (
        <AuthGuard>
            {/* Welcome Section */}
            <div className="mb-8">
                <div className="flex items-center gap-4 mb-2">
                    <div className="w-14 h-14 rounded-xl overflow-hidden shadow-md">
                        <Image
                            src="/logo_airc.jpg"
                            alt="AIRC"
                            width={56}
                            height={56}
                            className="object-cover"
                        />
                    </div>
                    <div>
                        <Title level={2} className="!mb-0" style={{ color: '#1a1a2e' }}>
                            Xin chào, {mounted ? (user?.full_name || 'Quản trị viên') : 'Quản trị viên'}!
                        </Title>
                        <Text type="secondary" style={{ fontSize: 15 }}>
                            Chào mừng bạn đến với hệ thống AIRC Internal Chatbot
                        </Text>
                    </div>
                </div>
            </div>

            {/* Statistics Cards */}
            <Row gutter={[20, 20]}>
                <Col xs={24} sm={12} lg={6}>
                    <Card
                        hoverable
                        className="border-0 shadow-sm hover:shadow-md transition-shadow"
                        style={{ borderRadius: 16 }}
                    >
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}>
                                <RobotOutlined style={{ fontSize: 24, color: '#fff' }} />
                            </div>
                            <div>
                                <Text type="secondary" className="text-sm">Chatbots</Text>
                                <div className="text-2xl font-bold" style={{ color: '#10b981' }}>
                                    {loading ? <LoadingOutlined /> : stats?.chatbot_count ?? 0}
                                </div>
                            </div>
                        </div>
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card
                        hoverable
                        className="border-0 shadow-sm hover:shadow-md transition-shadow"
                        style={{ borderRadius: 16 }}
                    >
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' }}>
                                <DatabaseOutlined style={{ fontSize: 24, color: '#fff' }} />
                            </div>
                            <div>
                                <Text type="secondary" className="text-sm">Datasets</Text>
                                <div className="text-2xl font-bold" style={{ color: '#3b82f6' }}>
                                    {loading ? <LoadingOutlined /> : stats?.dataset_count ?? 0}
                                </div>
                            </div>
                        </div>
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card
                        hoverable
                        className="border-0 shadow-sm hover:shadow-md transition-shadow"
                        style={{ borderRadius: 16 }}
                    >
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)' }}>
                                <MessageOutlined style={{ fontSize: 24, color: '#fff' }} />
                            </div>
                            <div>
                                <Text type="secondary" className="text-sm">Cuộc hội thoại</Text>
                                <div className="text-2xl font-bold" style={{ color: '#8b5cf6' }}>
                                    {loading ? <LoadingOutlined /> : stats?.conversation_count ?? 0}
                                </div>
                            </div>
                        </div>
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card
                        hoverable
                        className="border-0 shadow-sm hover:shadow-md transition-shadow"
                        style={{ borderRadius: 16 }}
                    >
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)' }}>
                                <TeamOutlined style={{ fontSize: 24, color: '#fff' }} />
                            </div>
                            <div>
                                <Text type="secondary" className="text-sm">Người dùng</Text>
                                <div className="text-2xl font-bold" style={{ color: '#dc2626' }}>
                                    {loading ? <LoadingOutlined /> : stats?.user_count ?? 0}
                                </div>
                            </div>
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* Quick Stats & Activity */}
            <Row gutter={[20, 20]} className="mt-6">
                <Col xs={24} lg={16}>
                    <Card
                        title={
                            <Space>
                                <ClockCircleOutlined style={{ color: '#dc2626' }} />
                                <span>Hoạt động gần đây</span>
                            </Space>
                        }
                        className="border-0 shadow-sm"
                        style={{ borderRadius: 16 }}
                    >
                        <div className="space-y-4">
                            {loading ? (
                                <div className="flex justify-center py-8">
                                    <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
                                </div>
                            ) : activities.length > 0 ? (
                                activities.map((activity, index) => (
                                    <div key={index} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors">
                                        <Avatar style={{ backgroundColor: getActivityColor(activity.type) }} icon={getActivityIcon(activity.type)} />
                                        <div className="flex-1">
                                            <Text strong>{activity.title} {activity.description}</Text>
                                            <div className="text-xs text-gray-400">{formatTimeAgo(activity.timestamp)}</div>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="text-center py-8 text-gray-400">
                                    Chưa có hoạt động nào
                                </div>
                            )}
                        </div>
                    </Card>
                </Col>
                <Col xs={24} lg={8}>
                    <Card
                        title={
                            <Space>
                                <ThunderboltOutlined style={{ color: '#f59e0b' }} />
                                <span>Hiệu suất RAG</span>
                            </Space>
                        }
                        className="border-0 shadow-sm"
                        style={{ borderRadius: 16 }}
                    >
                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <Text type="secondary">Thời gian phản hồi TB</Text>
                                <Text strong style={{ color: '#10b981' }}>
                                    {loading ? <LoadingOutlined /> : `${stats?.avg_response_time ?? 0}s`}
                                </Text>
                            </div>
                            <Divider className="my-2" />
                            <div className="flex justify-between items-center">
                                <Text type="secondary">Độ chính xác</Text>
                                <Text strong style={{ color: '#3b82f6' }}>
                                    {loading ? <LoadingOutlined /> : `${stats?.accuracy_rate ?? 0}%`}
                                </Text>
                            </div>
                            <Divider className="my-2" />
                            <div className="flex justify-between items-center">
                                <Text type="secondary">Cache hit rate</Text>
                                <Text strong style={{ color: '#8b5cf6' }}>
                                    {loading ? <LoadingOutlined /> : `${stats?.cache_hit_rate ?? 0}%`}
                                </Text>
                            </div>
                            <Divider className="my-2" />
                            <div className="flex justify-between items-center">
                                <Text type="secondary">Tổng chunks indexed</Text>
                                <Text strong>
                                    {loading ? <LoadingOutlined /> : (stats?.total_chunks_indexed ?? 0).toLocaleString()}
                                </Text>
                            </div>
                        </div>
                    </Card>
                </Col>
            </Row>
        </AuthGuard>
    );
}

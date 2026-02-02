'use client';

import React, { useEffect, useState } from 'react';
import { Card, notification, Breadcrumb, Button } from 'antd';
import { RobotOutlined, PlusOutlined } from '@ant-design/icons';
import MainLayout from '@/components/Layout/MainLayout';
import AuthGuard from '@/components/Auth/AuthGuard';
import ChatbotTable from '@/components/Admin/ChatbotTable';
import { chatbotService } from '@/services/chatbotService';
import { Chatbot } from '@/types/chatbot';
import { useRouter } from 'next/navigation';

export default function ChatbotsPage() {
    const router = useRouter();
    const [chatbots, setChatbots] = useState<Chatbot[]>([]);
    const [loading, setLoading] = useState(false);

    const fetchChatbots = React.useCallback(async () => {
        setLoading(true);
        try {
            const data = await chatbotService.getChatbots();
            setChatbots(data);
        } catch (error) {
            console.error(error);
            notification.error({
                message: 'Error fetching chatbots',
                description: 'Could not load chatbot list.',
            });
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchChatbots();
    }, [fetchChatbots]);

    const handleCreate = () => {
        router.push('/admin/chatbots/create');
    };

    const handleEdit = (chatbot: Chatbot) => {
        router.push(`/admin/chatbots/${chatbot.id}`);
    };

    const handleDelete = async (chatbot: Chatbot) => {
        try {
            await chatbotService.deleteChatbot(chatbot.id);
            notification.success({ message: 'Chatbot deleted successfully' });
            fetchChatbots();
        } catch (error) {
            console.error(error);
            notification.error({
                message: 'Error deleting chatbot',
                description: 'Could not delete chatbot.',
            });
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
                            { title: 'Chatbots' },
                        ]}
                    />

                    <div className="flex justify-between items-center mt-4">
                        <div className="flex items-center gap-3">
                            <RobotOutlined className="text-2xl text-blue-600" />
                            <h1 className="text-2xl font-bold m-0">Chatbot Management</h1>
                        </div>
                        <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            onClick={handleCreate}
                            className="bg-blue-600 hover:bg-blue-700"
                        >
                            Create Chatbot
                        </Button>
                    </div>
                </div>

                <Card bordered={false} className="shadow-sm rounded-lg">
                    <ChatbotTable
                        chatbots={chatbots}
                        loading={loading}
                        onEdit={handleEdit}
                        onDelete={handleDelete}
                    />
                </Card>
            </MainLayout>
        </AuthGuard>
    );
}

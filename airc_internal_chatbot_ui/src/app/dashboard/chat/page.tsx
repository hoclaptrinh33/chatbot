'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
    Input, Button, Typography,
    Card, Space, Avatar, Spin, Select
} from 'antd';
import { SendOutlined, UserOutlined, RobotOutlined } from '@ant-design/icons';
import Image from 'next/image';
import useChatStore from '@/stores/chatStore';
import useDatasetStore from '@/stores/datasetStore';
import StudentChat from '@/components/Student/StudentChat';
import ChatSidebar from './ChatSidebar';
import ChatMessageItem from '@/components/Chat/ChatMessageItem';
import useAuthStore from '@/stores/authStore';



import AuthGuard from '@/components/Auth/AuthGuard';
import { chatbotService } from '@/services/chatbotService';
import { Chatbot } from '@/types/chatbot';
import RAGDebugPanel from '@/components/Chat/RAGDebugPanel';

const { Title, Text } = Typography;
const { TextArea } = Input;
const { Option } = Select;

export default function ChatPage() {
    const { user } = useAuthStore();
    const {
        messages, loading: chatLoading, chatbotId, lastDebugMetrics,
        sendMessage, loadSessions, selectChatbot, createBranch, regenerateMessage,
        sessions, selectSession, currentSessionId
    } = useChatStore();

    const { fetchDatasets } = useDatasetStore();

    const [input, setInput] = useState('');
    const [chatbots, setChatbots] = useState<Chatbot[]>([]);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const lastUserIdRef = useRef<string | null>(null);
    const isInitializedRef = useRef(false);

    // Initialize chat - load chatbots, datasets, sessions
    useEffect(() => {
        if (!user?.id) return;

        // Check if user changed or first init
        const userChanged = lastUserIdRef.current !== null && user.id !== lastUserIdRef.current;
        const shouldInitialize = !isInitializedRef.current || userChanged;

        if (!shouldInitialize) return;

        const initializeChat = async () => {
            try {
                // Fetch Chatbots - API trả về theo role/user
                const data = await chatbotService.getChatbots();
                setChatbots(data);
                console.log('[ChatPage] Available chatbots:', data.map(c => ({ id: c.id, name: c.name })));

                // Luôn chọn chatbot đầu tiên
                if (data.length > 0) {
                    selectChatbot(data[0].id, data[0].dataset_ids);
                    console.log('[ChatPage] Selected chatbot:', data[0].name);
                }

                // Fetch datasets and sessions
                await Promise.all([
                    fetchDatasets(),
                    loadSessions()
                ]);

                // Update refs after successful init
                lastUserIdRef.current = user.id;
                isInitializedRef.current = true;
            } catch (err) {
                console.error("Failed to initialize chat", err);
                lastUserIdRef.current = user.id;
                isInitializedRef.current = true;
            }
        };

        initializeChat();
    }, [user?.id, selectChatbot, fetchDatasets, loadSessions]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || chatLoading) return;

        const question = input;
        setInput('');
        await sendMessage(question);
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleChatbotChange = (value: string) => {
        const bot = chatbots.find(c => c.id === value);
        selectChatbot(value, bot?.dataset_ids || []);
    };

    // Lấy danh sách các nhánh session tại vị trí tin nhắn có index
    const getBranchesAt = (idx: number) => {
        if (!currentSessionId || !sessions) return [];
        
        // 1. Tìm root session
        let rootId = currentSessionId;
        let current = sessions.find(s => s.id === currentSessionId);
        while (current && current.parent_id) {
            const currentParentId = current.parent_id;
            const parent = sessions.find(s => s.id === currentParentId);
            if (!parent) break;
            current = parent;
            rootId = current.id;
        }

        // 2. Tìm tất cả session con/cháu trong gia đình
        const familyIds = [rootId];
        let added = true;
        while (added) {
            added = false;
            for (const s of sessions) {
                if (s.parent_id && familyIds.includes(s.parent_id) && !familyIds.includes(s.id)) {
                    familyIds.push(s.id);
                    added = true;
                }
            }
        }
        const familySessions = sessions.filter(s => familyIds.includes(s.id));

        // 3. Tìm các session rẽ nhánh tại index idx
        const branchSessions = familySessions.filter(s => s.branch_message_index === idx);
        if (branchSessions.length === 0) return [];

        // 4. Các nhánh tại vị trí idx gồm session cha và các con rẽ nhánh từ cha tại index idx
        const parentId = branchSessions[0].parent_id;
        if (!parentId) return [];

        const allBranches = [
            parentId,
            ...familySessions
                .filter(s => s.parent_id === parentId && s.branch_message_index === idx)
                .map(s => s.id)
        ];

        return Array.from(new Set(allBranches));
    };

    // STUDENT VIEW: Use StudentChat component
    if (user?.role === 'student') {
        return (
            <AuthGuard>
                <StudentChat />
            </AuthGuard>
        );
    }

    const currentChatbot = chatbots.find(c => c.id === chatbotId);

    return (
        <AuthGuard>
            <div className="h-[calc(100vh-96px)] flex flex-col md:flex-row border border-gray-200 rounded-lg shadow-sm overflow-hidden bg-white">
                {/* Left Sidebar: Session & Dataset Manager */}
                <div className="w-full md:w-80 shrink-0 h-full border-b md:border-b-0 md:border-r border-gray-200">
                    <ChatSidebar className="h-full" />
                </div>

                {/* Main Chat Area */}
                <div className="flex-1 flex flex-col h-full bg-white">
                    {/* Header with AIRC Logo */}
                    <div className="p-4 border-b flex justify-between items-center bg-white rounded-t-lg">
                        <Space>
                            <Image
                                src="/logo_airc.jpg"
                                alt="AIRC Logo"
                                width={48}
                                height={48}
                                className="object-contain"
                            />
                            <div>
                                {chatbots.length > 1 ? (
                                    <Space direction="vertical" size={0}>
                                        <Text type="secondary" className="text-xs">Trợ lý hiện tại</Text>
                                        <Select
                                            value={chatbotId}
                                            onChange={handleChatbotChange}
                                            style={{ width: 220, fontWeight: 600 }}
                                            bordered={false}
                                            className="-ml-3"
                                            dropdownMatchSelectWidth={false}
                                        >
                                            {chatbots.map(bot => (
                                                <Option key={bot.id} value={bot.id}>{bot.name}</Option>
                                            ))}
                                        </Select>
                                    </Space>
                                ) : (
                                    <Title level={5} className="mb-0">
                                        {currentChatbot?.name || "Trợ lý AI AIRC"}
                                    </Title>
                                )}
                            </div>
                        </Space>
                    </div>

                    {/* Messages List */}
                    <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
                        {messages.length === 0 ? (
                            <div className="h-full flex flex-col justify-center items-center text-gray-400">
                                <div className="w-24 h-24 mb-6">
                                    <Image
                                        src="/logo_airc.jpg"
                                        alt="AIRC Logo"
                                        width={96}
                                        height={96}
                                        className="object-contain"
                                    />
                                </div>
                                <Title level={4} style={{ color: '#bfbfbf' }}>Bắt đầu trò chuyện</Title>
                                <Text type="secondary">Đặt câu hỏi về quy chế, đào tạo, hoặc bất kỳ vấn đề nào.</Text>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {messages.map((msg, idx) => {
                                    const branches = getBranchesAt(idx);
                                    const currentBranchIndex = branches.indexOf(currentSessionId || '');
                                    return (
                                        <ChatMessageItem
                                            key={idx}
                                            message={msg}
                                            index={idx}
                                            isLast={idx === messages.length - 1}
                                            loading={chatLoading}
                                            onEditAndSubmit={createBranch}
                                            onRegenerate={regenerateMessage}
                                            branches={branches}
                                            currentBranchIndex={currentBranchIndex}
                                            onBranchChange={selectSession}
                                        />
                                    );
                                })}
                                {chatLoading && (
                                    <div className="flex justify-start">
                                        <div className="max-w-[80%] flex gap-3">
                                            <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#dc2626' }} />
                                            <div className="bg-white border p-3 rounded-lg shadow-sm">
                                                <Spin /> <span className="text-gray-400 text-sm ml-2">Đang xử lý...</span>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Debug Panel - Show after last response */}
                                {lastDebugMetrics && !chatLoading && messages.length > 0 && (
                                    <RAGDebugPanel metrics={lastDebugMetrics} />
                                )}

                                <div ref={messagesEndRef} />
                            </div>
                        )}
                    </div>

                    {/* Input Area */}
                    <div className="p-4 bg-white border-t border-gray-100">
                        <div className="max-w-3xl mx-auto relative">
                            <div className="flex gap-2 items-end bg-white border border-gray-200 rounded-2xl p-2 shadow-sm focus-within:ring-2 focus-within:ring-red-100 focus-within:border-red-400 transition-all">
                                <TextArea
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyDown={handleKeyPress}
                                    placeholder="Nhập câu hỏi của bạn ở đây..."
                                    autoSize={{ minRows: 1, maxRows: 6 }}
                                    className="border-none shadow-none bg-transparent text-[16px] px-3 py-2 focus:ring-0 focus:border-transparent"
                                    style={{ resize: 'none' }}
                                    disabled={chatLoading}
                                    bordered={false}
                                    variant="borderless"
                                />
                                <Button
                                    type="primary"
                                    shape="circle"
                                    size="large"
                                    icon={<SendOutlined />}
                                    onClick={handleSend}
                                    disabled={!input.trim() || chatLoading}
                                    loading={chatLoading}
                                    className={`mb-0.5 mr-0.5 shadow-md flex items-center justify-center ${
                                        input.trim() && !chatLoading
                                            ? 'bg-red-600 hover:bg-red-700 border-none text-white'
                                            : 'bg-gray-100 text-gray-400 border-none'
                                    }`}
                                />
                            </div>
                            <div className="mt-2 text-xs text-gray-400 text-center">
                                AIRC Assistant có thể mắc lỗi. Vui lòng kiểm tra lại thông tin quan trọng.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </AuthGuard>
    );
}

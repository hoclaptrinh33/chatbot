'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';

import { Input, Button, Avatar, Spin, List, Typography, message as antMessage } from 'antd';
import { SendOutlined, RobotOutlined, UserOutlined, PlusOutlined, MessageOutlined, DeleteOutlined, LogoutOutlined, WarningOutlined } from '@ant-design/icons';
import useAuthStore from '@/stores/authStore';
import useChatStore from '@/stores/chatStore';
import { chatbotService } from '@/services/chatbotService';
import { Chatbot } from '@/types/chatbot';
import ChatMessageItem from '@/components/Chat/ChatMessageItem';

const { TextArea } = Input;
const { Text } = Typography;

/**
 * Component Chat cho Student/Teacher - Giao diện AIRC màu đỏ
 */
export default function StudentChat() {
    const { user } = useAuthStore();
    const {
        messages,
        loading,
        sendMessage,
        loadSessions,
        sessions,
        createSession,
        selectSession,
        currentSessionId,
        deleteSession,
        selectChatbot,
        chatbotId,
        createBranch,
        regenerateMessage
    } = useChatStore();

    const router = useRouter();
    const { logout } = useAuthStore();

    const handleLogout = () => {
        logout();
        router.push('/auth/login');
    };

    const [inputValue, setInputValue] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const [searchTerm, setSearchTerm] = useState('');

    // CRITICAL: Track selected chatbot locally to avoid race condition with Zustand state
    const [selectedChatbot, setSelectedChatbot] = useState<Chatbot | null>(null);
    const [noChatbotAvailable, setNoChatbotAvailable] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    // Track user ID để detect khi user thay đổi
    const lastUserIdRef = useRef<string | null>(null);

    // Load chatbot và sessions khi mount hoặc khi user thay đổi
    useEffect(() => {
        if (!user?.id) {
            setIsLoading(false);
            return;
        }

        // Check if user changed
        const userChanged = lastUserIdRef.current !== null && user.id !== lastUserIdRef.current;

        // Skip if already loaded for same user
        if (!userChanged && selectedChatbot !== null) {
            setIsLoading(false);
            return;
        }

        const initializeChat = async () => {
            setIsLoading(true);
            try {
                // Load chatbot for this user - API trả về chatbot theo role/user
                const chatbots = await chatbotService.getChatbots();
                console.log('[StudentChat] Available chatbots for user:', chatbots.map(c => ({ id: c.id, name: c.name })));

                if (chatbots.length > 0) {
                    // Luôn chọn chatbot đầu tiên được trả về (đã lọc theo user)
                    const chatbot = chatbots[0];
                    selectChatbot(chatbot.id, chatbot.dataset_ids);
                    setSelectedChatbot(chatbot); // CRITICAL: Track locally
                    setNoChatbotAvailable(false);
                    console.log('[StudentChat] Selected chatbot:', chatbot.name, 'ID:', chatbot.id);
                } else {
                    console.warn('[StudentChat] No chatbots available for this user!');
                    setNoChatbotAvailable(true);
                    setSelectedChatbot(null);
                }

                // Load sessions
                await loadSessions();

                lastUserIdRef.current = user.id;
            } catch (err) {
                console.error("Failed to initialize chat", err);
                setNoChatbotAvailable(true);
                setSelectedChatbot(null);
            } finally {
                setIsLoading(false);
            }
        };

        initializeChat();
    }, [user?.id, selectChatbot, loadSessions, selectedChatbot]);

    // Scroll to bottom effect
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    const handleSend = async () => {
        if (!inputValue.trim()) return;

        // CRITICAL: Kiểm tra selectedChatbot local state (không phải Zustand state)
        // vì Zustand state có thể chưa được update do async nature
        if (!selectedChatbot) {
            console.error('[StudentChat] No chatbot selected! Cannot send message.');
            antMessage.error('Chưa có chatbot được cấu hình. Vui lòng liên hệ Admin.');
            return;
        }

        // Đảm bảo chatbot đã được set trong store trước khi gửi
        // Double-check và sync lại nếu cần
        if (chatbotId !== selectedChatbot.id) {
            console.warn('[StudentChat] Syncing chatbot to store:', selectedChatbot.id);
            selectChatbot(selectedChatbot.id, selectedChatbot.dataset_ids);
            // Đợi một tick để state update
            await new Promise(resolve => setTimeout(resolve, 0));
        }

        console.log('[StudentChat] Sending message with chatbot:', selectedChatbot.name, 'ID:', selectedChatbot.id);

        const msg = inputValue;
        setInputValue('');
        await sendMessage(msg);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const filteredSessions = sessions.filter(s =>
        !s.parent_id && s.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const activeSessionName = sessions.find(s => s.id === currentSessionId)?.name || 'Cuộc trò chuyện mới';

    // Show loading state
    if (isLoading) {
        return (
            <div className="flex h-screen items-center justify-center bg-gray-50">
                <div className="text-center">
                    <Spin size="large" />
                    <p className="mt-4 text-gray-500">Đang tải chatbot...</p>
                </div>
            </div>
        );
    }

    // Show error if no chatbot available for this user
    if (noChatbotAvailable || !selectedChatbot) {
        return (
            <div className="flex h-screen items-center justify-center bg-gray-50">
                <div className="text-center max-w-md p-8">
                    <WarningOutlined className="text-6xl text-orange-400 mb-4" />
                    <h2 className="text-xl font-semibold text-gray-700 mb-2">Chưa có Chatbot</h2>
                    <p className="text-gray-500 mb-4">
                        Hiện tại chưa có chatbot nào được cấu hình cho tài khoản của bạn.
                        Vui lòng liên hệ Admin để được hỗ trợ.
                    </p>
                    <Button
                        type="primary"
                        danger
                        onClick={() => {
                            // Reset to trigger reload
                            setSelectedChatbot(null);
                            setNoChatbotAvailable(false);
                            lastUserIdRef.current = null;
                        }}
                    >
                        Thử lại
                    </Button>
                </div>
            </div>
        );
    }

    // Render empty state if no messages
    const renderEmptyState = () => (
        <div className="flex flex-col items-center justify-center h-full text-center p-8 opacity-80">
            <div className="w-24 h-24 mb-6">
                <Image
                    src="/logo_airc.jpg"
                    alt="AIRC Logo"
                    width={96}
                    height={96}
                    className="object-contain"
                />
            </div>
            <h1 className="text-2xl font-bold mb-3 text-gray-800">Xin chào! Tôi là AIRC Assistant</h1>
            <p className="text-gray-500 max-w-md">Hãy đặt câu hỏi về quy chế, đào tạo, hoặc bất kỳ vấn đề nào bạn cần hỗ trợ.</p>
        </div>
    );

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

    return (
        <div className="flex h-screen overflow-hidden bg-gray-50">
            {/* Sidebar List Sessions - AIRC Red Theme */}
            <div className="w-80 bg-white border-r border-gray-200 flex-col hidden md:flex">
                {/* Header with AIRC branding */}
                <div className="p-4 border-b border-gray-100 bg-white">
                    <div className="flex items-center gap-3">
                        <Image
                            src="/logo_airc.jpg"
                            alt="AIRC Logo"
                            width={48}
                            height={48}
                            className="object-contain"
                        />
                        <div>
                            <span className="text-lg font-bold text-red-700">AIRC Chat</span>
                            <div className="text-xs text-gray-500">Key to Success</div>
                        </div>
                    </div>
                </div>

                {/* Search */}
                <div className="p-3">
                    <Input
                        placeholder="Tìm kiếm cuộc trò chuyện..."
                        className="rounded-lg bg-gray-50 border-gray-200"
                        prefix={<MessageOutlined className="text-gray-400" />}
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                    />
                </div>

                {/* New Chat Button */}
                <div className="px-3 pb-2">
                    <Button
                        type="primary"
                        block
                        icon={<PlusOutlined />}
                        onClick={() => createSession('Cuộc trò chuyện mới')}
                        className="h-10 bg-red-600 hover:bg-red-700 border-none rounded-lg"
                    >
                        Cuộc trò chuyện mới
                    </Button>
                </div>

                {/* Sessions List */}
                <div className="flex-1 overflow-y-auto px-2">
                    <List
                        dataSource={filteredSessions}
                        locale={{ emptyText: <span className="text-gray-400 text-sm p-4 block text-center">Chưa có cuộc trò chuyện</span> }}
                        renderItem={item => (
                            <div
                                className={`
                                    group flex items-center gap-3 p-3 mb-1 rounded-lg cursor-pointer transition-all
                                    ${currentSessionId === item.id
                                        ? 'bg-red-50 text-red-700 border border-red-200'
                                        : 'hover:bg-gray-50 text-gray-700'}
                                `}
                                onClick={() => selectSession(item.id)}
                            >
                                <MessageOutlined className={currentSessionId === item.id ? 'text-red-500' : 'text-gray-400'} />
                                <div className="flex-1 truncate font-medium text-sm">
                                    {item.name}
                                </div>
                                <div className="opacity-0 group-hover:opacity-100 flex gap-1">
                                    <Button
                                        type="text"
                                        size="small"
                                        icon={<DeleteOutlined />}
                                        danger
                                        onClick={(e) => { e.stopPropagation(); deleteSession(item.id); }}
                                    />
                                </div>
                            </div>
                        )}
                    />
                </div>

                {/* User Profile & Logout */}
                <div className="p-4 border-t border-gray-200 bg-gray-50">
                    <div className="flex items-center gap-3">
                        <Avatar
                            icon={<UserOutlined />}
                            src={user?.avatar_url}
                            className="bg-red-500"
                        />
                        <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium truncate text-gray-800">
                                {user?.full_name || 'Người dùng'}
                            </div>
                            <div className="text-xs text-gray-500 truncate">{user?.email}</div>
                        </div>
                        <Button
                            type="text"
                            icon={<LogoutOutlined />}
                            onClick={handleLogout}
                            title="Đăng xuất"
                            className="text-gray-500 hover:text-red-600 hover:bg-red-50"
                        />
                    </div>
                </div>
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col bg-white">
                {/* Chat Header */}
                <div className="h-14 border-b border-gray-100 flex items-center px-4 justify-between bg-white shadow-sm">
                    <div className="flex items-center gap-3">
                        <Image
                            src="/logo_airc.jpg"
                            alt="AIRC"
                            width={32}
                            height={32}
                            className="object-contain md:hidden"
                        />
                        <span className="font-semibold text-gray-700 truncate max-w-[200px]">
                            {activeSessionName}
                        </span>
                    </div>

                    <div className="flex items-center gap-2">
                        <span className="hidden sm:inline text-xs text-white bg-red-500 px-2 py-1 rounded-full">
                            Đã bật RAG
                        </span>
                        {/* Mobile Logout */}
                        <Button
                            className="md:hidden"
                            type="text"
                            icon={<LogoutOutlined />}
                            onClick={handleLogout}
                            title="Đăng xuất"
                        />
                    </div>
                </div>

                {/* Messages List */}
                <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-gray-50">
                    {messages.length === 0 ? renderEmptyState() : (
                        <div className="max-w-3xl mx-auto space-y-6">
                            {messages.map((msg, idx) => {
                                const branches = getBranchesAt(idx);
                                const currentBranchIndex = branches.indexOf(currentSessionId || '');
                                return (
                                    <ChatMessageItem
                                        key={msg.id || idx}
                                        message={msg}
                                        index={idx}
                                        isLast={idx === messages.length - 1}
                                        loading={loading}
                                        onEditAndSubmit={createBranch}
                                        onRegenerate={regenerateMessage}
                                        branches={branches}
                                        currentBranchIndex={currentBranchIndex}
                                        onBranchChange={selectSession}
                                    />
                                );
                            })}

                            {loading && (
                                <div className="flex gap-4 items-center">
                                    <Avatar icon={<RobotOutlined />} className="bg-red-500" />
                                    <div className="bg-white rounded-2xl px-5 py-3 border border-gray-200 shadow-sm">
                                        <Spin size="small" />
                                        <span className="text-gray-400 text-sm ml-2">Đang xử lý...</span>
                                    </div>
                                </div>
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
                                value={inputValue}
                                onChange={e => setInputValue(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder={selectedChatbot ? "Nhập câu hỏi của bạn..." : "Đang tải chatbot..."}
                                autoSize={{ minRows: 1, maxRows: 6 }}
                                className="border-none shadow-none bg-transparent text-[16px] px-3 py-2 focus:ring-0 focus:border-transparent"
                                style={{ resize: 'none' }}
                                disabled={!selectedChatbot}
                                bordered={false}
                                variant="borderless"
                            />
                            <Button
                                type="primary"
                                shape="circle"
                                size="large"
                                icon={<SendOutlined />}
                                onClick={handleSend}
                                disabled={!inputValue.trim() || loading || !selectedChatbot}
                                className={`mb-0.5 mr-0.5 shadow-md flex items-center justify-center ${
                                    inputValue.trim() && !loading && selectedChatbot
                                        ? 'bg-red-600 hover:bg-red-700 border-none text-white'
                                        : 'bg-gray-100 text-gray-400 border-none'
                                }`}
                            />
                        </div>
                        <div className="text-center mt-2">
                            <Text type="secondary" className="text-xs">
                                AIRC Assistant có thể mắc lỗi. Vui lòng kiểm tra lại thông tin quan trọng.
                            </Text>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

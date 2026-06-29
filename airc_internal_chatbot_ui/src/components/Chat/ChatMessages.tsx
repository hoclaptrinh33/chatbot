'use client';

import React, { useRef, useEffect } from 'react';
import { Avatar, Spin, Typography } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import { ChatMessage } from '@/core/entities/Chat';
import dayjs from 'dayjs';
import ChatMessageContent from '@/components/Chat/ChatMessageContent';
import Image from 'next/image';

const { Text } = Typography;

interface ChatMessagesProps {
    messages: ChatMessage[];
    isTyping: boolean;
}

/**
 * ChatMessages Component
 * 
 * Hien thi danh sach tin nhan trong cuoc hoi thoai giua nguoi dung va AI Assistant.
 * 
 * Features:
 * - Hien thi tin nhan voi avatar va bubble chat phan biet user/bot
 * - Tu dong scroll xuong tin nhan moi nhat
 * - Render Markdown cho cau tra loi tu bot (danh sach, in dam, code block)
 * - Hien thi trang thai "dang go..." khi bot dang xu ly
 * 
 * @param messages - Danh sach tin nhan can hien thi
 * @param isTyping - Trang thai bot dang go hay khong
 */
export default function ChatMessages({ messages, isTyping }: ChatMessagesProps) {
    const bottomRef = useRef<HTMLDivElement>(null);

    /**
     * Auto scroll xuong tin nhan moi nhat khi co tin nhan moi hoac bot dang go
     */
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isTyping]);



    return (
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50">
            {messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-gray-400">
                    <div className="mb-4">
                        <Image src="/logo_airc.jpg" alt="AIRC Logo" width={120} height={120} className="rounded-full" />
                    </div>
                    <Text type="secondary" className="text-lg">
                        Bat dau tro chuyen voi AIRC Assistant
                    </Text>
                    <Text type="secondary" className="text-sm">
                        Chon dataset ben trai va dat cau hoi.
                    </Text>
                </div>
            )}

            {messages.map((msg) => (
                <div
                    key={msg.id}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                    <div className={`flex max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} gap-3`}>
                        {/* Avatar */}
                        {msg.role === 'user' ? (
                            <Avatar
                                icon={<UserOutlined />}
                                style={{
                                    backgroundColor: '#1890ff',
                                    flexShrink: 0
                                }}
                            />
                        ) : (
                            <Avatar
                                src="/logo_airc.jpg"
                                style={{
                                    flexShrink: 0,
                                    backgroundColor: 'white'
                                }}
                            />
                        )}

                        {/* Message Bubble */}
                        <div className={`
                            p-4 rounded-lg shadow-sm
                            ${msg.role === 'user'
                                ? 'bg-blue-600 text-white rounded-tr-none'
                                : 'bg-white border border-gray-100 rounded-tl-none text-gray-800'
                            }
                        `}>
                            <div className={`markdown-content ${msg.role === 'user' ? 'text-white' : 'text-gray-800'}`}>
                                {msg.role === 'user' ? (
                                    // User message: Plain text with preserved line breaks
                                    <p className="m-0 whitespace-pre-wrap">{msg.content}</p>
                                ) : (
                                    // Bot message: Render Markdown, LaTeX & Mermaid for rich formatting
                                    <ChatMessageContent content={msg.content} isUser={false} />
                                )}
                            </div>

                            <div className={`text-xs mt-2 opacity-70 ${msg.role === 'user' ? 'text-blue-100' : 'text-gray-400'}`}>
                                {dayjs(msg.timestamp).format('HH:mm')}
                            </div>
                        </div>
                    </div>
                </div>
            ))}

            {isTyping && (
                <div className="flex justify-start">
                    <div className="flex items-start gap-3">
                        <Avatar
                            src="/logo_airc.jpg"
                            style={{ backgroundColor: 'white' }}
                        />
                        <div className="bg-white p-4 rounded-lg rounded-tl-none border border-gray-100 shadow-sm">
                            <Spin size="small" />
                            <span className="ml-2 text-gray-500 text-sm">AI dang suy nghi...</span>
                        </div>
                    </div>
                </div>
            )}

            <div ref={bottomRef} />
        </div>
    );
}

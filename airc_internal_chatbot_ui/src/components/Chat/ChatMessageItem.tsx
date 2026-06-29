'use client';

import React, { useState } from 'react';
import { Avatar, Button, Input, Space, Tooltip, message } from 'antd';
import { 
    UserOutlined, 
    RobotOutlined, 
    EditOutlined, 
    CopyOutlined, 
    ReloadOutlined, 
    CheckOutlined,
    CloseOutlined,
    SendOutlined,
    WarningOutlined
} from '@ant-design/icons';
import { ChatMessage } from '@/core/entities/Chat';
import ChatMessageContent from './ChatMessageContent';
import dayjs from 'dayjs';

interface ChatMessageItemProps {
    message: ChatMessage;
    index: number;
    isLast: boolean;
    loading: boolean;
    onEditAndSubmit: (newContent: string, index: number) => Promise<void>;
    onRegenerate: (index: number) => Promise<void>;
    branches?: string[];
    currentBranchIndex?: number;
    onBranchChange?: (sessionId: string) => void;
}

export default function ChatMessageItem({
    message: msg,
    index,
    isLast,
    loading,
    onEditAndSubmit,
    onRegenerate,
    branches = [],
    currentBranchIndex = -1,
    onBranchChange
}: ChatMessageItemProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState(msg.content);
    const [copied, setCopied] = useState(false);
    const [submitLoading, setSubmitLoading] = useState(false);

    const isUser = msg.role === 'user';
    const isError = !isUser && (
        msg.content.startsWith('Lỗi Server AI') || 
        msg.content.startsWith('Không thể kết nối') || 
        msg.content.startsWith('Thời gian yêu cầu') ||
        msg.content.startsWith('Xin lỗi, hệ thống gặp lỗi')
    );

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(msg.content);
            setCopied(true);
            message.success('Đã sao chép nội dung tin nhắn!');
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy text: ', err);
            message.error('Không thể sao chép tin nhắn');
        }
    };

    const handleEditSubmit = async () => {
        if (!editValue.trim()) {
            message.warning('Nội dung tin nhắn không được để trống');
            return;
        }
        if (editValue === msg.content) {
            setIsEditing(false);
            return;
        }

        setSubmitLoading(true);
        try {
            await onEditAndSubmit(editValue, index);
            setIsEditing(false);
        } catch (err) {
            console.error(err);
        } finally {
            setSubmitLoading(false);
        }
    };

    const handleRegenerate = async () => {
        try {
            await onRegenerate(index);
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} w-full group py-2`}>
            <div className={`flex max-w-[85%] gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} relative`}>
                {/* Avatar */}
                <Avatar
                    icon={isUser ? <UserOutlined /> : <RobotOutlined />}
                    style={{
                        backgroundColor: isUser ? '#87d068' : '#dc2626',
                        flexShrink: 0
                    }}
                />

                {/* Bong bóng chat chính */}
                <div className="flex flex-col gap-1 max-w-full">
                    {/* Bong bóng nội dung */}
                    <div
                        className={`p-3.5 rounded-xl shadow-sm relative transition-all duration-150 ${
                            isUser
                                ? 'bg-red-600 text-white rounded-tr-none'
                                : isError
                                ? 'bg-red-50 border border-red-200 rounded-tl-none text-red-800'
                                : 'bg-white border border-gray-200 rounded-tl-none text-gray-800'
                        }`}
                        style={{ minWidth: isEditing ? '320px' : 'auto' }}
                    >
                        {isEditing ? (
                            <div className="flex flex-col gap-2">
                                <Input.TextArea
                                    value={editValue}
                                    onChange={(e) => setEditValue(e.target.value)}
                                    autoSize={{ minRows: 2, maxRows: 6 }}
                                    className="border-gray-350 focus:border-red-500 focus:shadow-none"
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && !e.shiftKey) {
                                            e.preventDefault();
                                            handleEditSubmit();
                                        }
                                    }}
                                />
                                <div className="flex justify-end gap-2 mt-1">
                                    <Button 
                                        size="small" 
                                        icon={<CloseOutlined />} 
                                        onClick={() => {
                                            setIsEditing(false);
                                            setEditValue(msg.content);
                                        }}
                                        disabled={submitLoading}
                                    >
                                        Hủy
                                    </Button>
                                    <Button 
                                        type="primary" 
                                        size="small" 
                                        icon={<SendOutlined />}
                                        onClick={handleEditSubmit}
                                        loading={submitLoading}
                                    >
                                        Gửi & Tạo nhánh
                                    </Button>
                                </div>
                            </div>
                        ) : (
                            <div className={`prose max-w-none break-words ${isUser ? 'text-white' : isError ? 'text-red-700' : 'text-gray-800'} flex gap-2 items-start`}>
                                {isError && <WarningOutlined className="text-red-500 mt-1 shrink-0" />}
                                <div className="flex-1">
                                    <ChatMessageContent content={msg.content} isUser={isUser} />
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Meta info & Toolbar bên dưới bong bóng của AI */}
                    {!isUser && !isEditing && (
                        <div className="flex items-center justify-between flex-row-reverse px-1 mt-1 select-none">
                            {/* Thời gian gửi */}
                            <span className="text-[10px] text-gray-400">
                                {dayjs(msg.timestamp).format('HH:mm')}
                            </span>
                            
                            {/* Toolbar AI */}
                            <Space size={4} className="opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                                <Tooltip title="Sao chép">
                                    <Button
                                        type="text"
                                        size="small"
                                        icon={copied ? <CheckOutlined className="text-green-500" /> : <CopyOutlined className="text-gray-400 hover:text-gray-600" />}
                                        onClick={handleCopy}
                                        className="flex items-center justify-center p-1 h-6 w-6"
                                    />
                                </Tooltip>
                                {isLast && (
                                    <Tooltip title="Thử lại ">
                                        <Button
                                            type="text"
                                            size="small"
                                            icon={<ReloadOutlined className="text-gray-400 hover:text-red-500" />}
                                            onClick={handleRegenerate}
                                            disabled={loading}
                                            className="flex items-center justify-center p-1 h-6 w-6"
                                        />
                                    </Tooltip>
                                )}
                            </Space>
                        </div>
                    )}

                    {/* Meta info & Toolbar của User */}
                    {isUser && !isEditing && (
                        <div className="flex items-center justify-end gap-3 px-1 mt-1 select-none">
                            {/* Bộ chọn nhánh (phiên bản tin nhắn cũ/mới) */}
                            {branches && branches.length > 1 && currentBranchIndex !== -1 && (
                                <span className="flex items-center gap-1 bg-gray-100 px-2 py-0.5 rounded-full border border-gray-200 text-[11px] text-gray-500 font-medium mr-1 select-none">
                                    <Button
                                        type="text"
                                        size="small"
                                        disabled={currentBranchIndex === 0}
                                        onClick={() => onBranchChange && onBranchChange(branches[currentBranchIndex - 1])}
                                        className="h-4 w-4 p-0 flex items-center justify-center border-none shadow-none text-gray-500 hover:text-red-600 disabled:text-gray-300 font-bold"
                                        style={{ fontSize: '10px', lineHeight: 1 }}
                                    >
                                        &lt;
                                    </Button>
                                    <span className="px-0.5">{currentBranchIndex + 1}/{branches.length}</span>
                                    <Button
                                        type="text"
                                        size="small"
                                        disabled={currentBranchIndex === branches.length - 1}
                                        onClick={() => onBranchChange && onBranchChange(branches[currentBranchIndex + 1])}
                                        className="h-4 w-4 p-0 flex items-center justify-center border-none shadow-none text-gray-500 hover:text-red-600 disabled:text-gray-300 font-bold"
                                        style={{ fontSize: '10px', lineHeight: 1 }}
                                    >
                                        &gt;
                                    </Button>
                                </span>
                            )}

                            {/* Toolbar User */}
                            <Space size={4} className="opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                                <Tooltip title="Chỉnh sửa tin nhắn">
                                    <Button
                                        type="text"
                                        size="small"
                                        icon={<EditOutlined className="text-gray-400 hover:text-red-500" />}
                                        onClick={() => {
                                            setEditValue(msg.content);
                                            setIsEditing(true);
                                        }}
                                        className="flex items-center justify-center p-1 h-6 w-6"
                                    />
                                </Tooltip>
                                <Tooltip title="Sao chép">
                                    <Button
                                        type="text"
                                        size="small"
                                        icon={copied ? <CheckOutlined className="text-green-500" /> : <CopyOutlined className="text-gray-400 hover:text-gray-600" />}
                                        onClick={handleCopy}
                                        className="flex items-center justify-center p-1 h-6 w-6"
                                    />
                                </Tooltip>
                            </Space>

                            {/* Thời gian gửi */}
                            <span className="text-[10px] text-gray-400">
                                {dayjs(msg.timestamp).format('HH:mm')}
                            </span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

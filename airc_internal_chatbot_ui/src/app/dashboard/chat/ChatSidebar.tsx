'use client';

import React, { useEffect, useState } from 'react';
import { Card, Button, Typography, Tabs, Input, Modal, Dropdown, MenuProps, Select } from 'antd';
import {
    PlusOutlined, MessageOutlined, EllipsisOutlined,
    EditOutlined, DeleteOutlined, DatabaseOutlined,
    ClearOutlined, SearchOutlined
} from '@ant-design/icons';
import useChatStore from '@/stores/chatStore';
import useDatasetStore from '@/stores/datasetStore';
import { ChatSession } from '@/services/chatService';

const { Text, Paragraph } = Typography;
const { Option } = Select;

/**
 * Component sidebar quản lý Sessions và Datasets cho Chat
 * Kết hợp cả quản lý phiên chat (Session Management) và cấu hình Dataset
 */
export default function ChatSidebar({ className }: { className?: string }) {
    const {
        sessions, currentSessionId,
        createSession, selectSession, renameSession, deleteSession,
    } = useChatStore();

    const [editingId, setEditingId] = useState<string | null>(null);
    const [editName, setEditName] = useState('');

    // NOTE: loadSessions đã được gọi ở ChatPage - không gọi lại ở đây để tránh duplicate calls

    // Tạo session mới
    const handleCreateSession = async () => {
        await createSession();
    };

    // Đổi tên session
    const handleRename = async (id: string) => {
        if (editName.trim()) {
            await renameSession(id, editName);
        }
        setEditingId(null);
        setEditName('');
    };

    // Bắt đầu edit tên session
    const startEdit = (session: ChatSession) => {
        setEditingId(session.id);
        setEditName(session.name);
    };

    // Xóa session với confirmation
    const handleDelete = (id: string) => {
        Modal.confirm({
            title: 'Xóa đoạn chat này?',
            content: 'Bạn không thể khôi phục sau khi xóa.',
            okText: 'Xóa',
            okType: 'danger',
            cancelText: 'Hủy',
            onOk: () => deleteSession(id)
        });
    };

    // Render từng session item
    const renderSessionItem = (session: ChatSession) => {
        const isActive = session.id === currentSessionId;
        const isEditing = editingId === session.id;

        const menuItems: MenuProps['items'] = [
            {
                key: 'rename',
                label: 'Đổi tên',
                icon: <EditOutlined />,
                onClick: ({ domEvent }) => {
                    domEvent.stopPropagation();
                    startEdit(session);
                }
            },
            {
                key: 'delete',
                label: 'Xóa',
                icon: <DeleteOutlined />,
                danger: true,
                onClick: ({ domEvent }) => {
                    domEvent.stopPropagation();
                    handleDelete(session.id);
                }
            }
        ];

        return (
            <div
                key={session.id}
                className={`
                    group flex items-center justify-between p-3 cursor-pointer rounded-lg mb-1 transition-colors
                    ${isActive ? 'bg-blue-50 border-blue-200 border' : 'hover:bg-gray-50 border border-transparent'}
                `}
                onClick={() => selectSession(session.id)}
            >
                <div className="flex items-center gap-3 overflow-hidden flex-1">
                    <MessageOutlined className={isActive ? 'text-blue-500' : 'text-gray-400'} />

                    {isEditing ? (
                        <Input
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            onBlur={() => handleRename(session.id)}
                            onPressEnter={() => handleRename(session.id)}
                            autoFocus
                            onClick={(e) => e.stopPropagation()}
                            size="small"
                        />
                    ) : (
                        <div className="flex flex-col overflow-hidden">
                            <Text strong={isActive} ellipsis className="block">
                                {session.name}
                            </Text>
                            <Text type="secondary" className="text-xs">
                                {new Date(session.created_at).toLocaleDateString()}
                            </Text>
                        </div>
                    )}
                </div>

                {!isEditing && (
                    <Dropdown menu={{ items: menuItems }} trigger={['click']}>
                        <Button
                            type="text"
                            size="small"
                            icon={<EllipsisOutlined />}
                            className={`opacity-0 group-hover:opacity-100 ${isActive ? 'opacity-100' : ''}`}
                            onClick={(e) => e.stopPropagation()}
                        />
                    </Dropdown>
                )}
            </div>
        );
    };

    const [searchTerm, setSearchTerm] = useState('');

    // Filter sessions
    const filteredSessions = sessions.filter(s =>
        !s.parent_id && s.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div
            className={`flex flex-col h-full ${className}`}
            style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
        >
            {/* Nút tạo chat mới */}
            <div className="p-3 border-b space-y-3">
                <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    block
                    onClick={handleCreateSession}
                    size="large"
                >
                    Chat mới
                </Button>
                <Input
                    prefix={<SearchOutlined className="text-gray-400" />}
                    placeholder="Tìm kiếm đoạn chat..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    allowClear
                />
            </div>

            {/* Danh sách Chat Sessions */}
            <div className="flex-1 overflow-y-auto px-2 pb-2 mt-2">
                {filteredSessions.length === 0 ? (
                    <div className="text-center text-gray-400 mt-10">
                        <MessageOutlined style={{ fontSize: 30, marginBottom: 10 }} />
                        <p>{searchTerm ? 'Không tìm thấy kết quả' : 'Chưa có đoạn chat nào'}</p>
                    </div>
                ) : (
                    <div className="flex flex-col">
                        {filteredSessions.map(renderSessionItem)}
                    </div>
                )}
            </div>

            {/* Footer Actions if needed (like Clear Screen but maybe move to header?) */}
            {/* Keeping it simple as requested "Delete unnecessary things" */}
        </div>
    );
}

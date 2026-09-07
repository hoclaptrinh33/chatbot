'use client';

import React, { useEffect, useState } from 'react';
import { Avatar, Button, Spin, Tooltip } from 'antd';
import { DownloadOutlined, RobotOutlined } from '@ant-design/icons';
import ChatMessageItem from '@/components/Chat/ChatMessageItem';
import RAGDebugPanel, { RAGDebugMetrics } from '@/components/Chat/RAGDebugPanel';
import { ChatMessage } from '@/core/entities/Chat';
import chatService from '@/services/chatService';
import useChatStore from '@/stores/chatStore';

interface ChatTranscriptProps {
    getBranchesAt: (idx: number) => string[];
    emptyHint?: React.ReactNode;
}

function toMarkdown(messages: ChatMessage[]): string {
    const lines = ['# Phiên trò chuyện AIRC', ''];
    for (const msg of messages) {
        const who = msg.role === 'user' ? 'Người dùng' : 'Trợ lý';
        lines.push(`## ${who}`, '', msg.content || '', '');
        const sources = msg.sources || [];
        if (sources.length) {
            lines.push('### Nguồn');
            for (const group of sources) {
                for (const result of group.results || []) {
                    lines.push(`- ${result.file_name || 'Tài liệu'} (${group.dataset_name || ''})`);
                    if (result.text) lines.push(`  > ${result.text.replace(/\s+/g, ' ').slice(0, 240)}`);
                }
            }
            lines.push('');
        }
    }
    return lines.join('\n');
}

export default function ChatTranscript({ getBranchesAt, emptyHint }: ChatTranscriptProps) {
    const {
        messages, loading, lastDebugMetrics, currentSessionId,
        createBranch, regenerateMessage, selectSession, sendMessage,
    } = useChatStore();
    const [suggestions, setSuggestions] = useState<string[]>([]);

    useEffect(() => {
        if (messages.length > 0) return;
        let cancelled = false;
        chatService.getSuggestions().then((items) => {
            if (!cancelled) setSuggestions(items);
        }).catch(() => {
            if (!cancelled) setSuggestions([]);
        });
        return () => {
            cancelled = true;
        };
    }, [messages.length]);

    const exportMarkdown = () => {
        const blob = new Blob([toMarkdown(messages)], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `airc-chat-${currentSessionId || 'session'}.md`;
        link.click();
        URL.revokeObjectURL(url);
    };

    if (messages.length === 0) {
        return (
            <div className="h-full flex flex-col justify-center items-center text-gray-400 gap-4 p-4">
                {emptyHint}
                {suggestions.length > 0 && (
                    <div className="flex flex-wrap justify-center gap-2 max-w-xl">
                        {suggestions.map((item) => (
                            <Button key={item} size="small" onClick={() => sendMessage(item)}>
                                {item}
                            </Button>
                        ))}
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex justify-end">
                <Tooltip title="Xuất Markdown">
                    <Button size="small" icon={<DownloadOutlined />} onClick={exportMarkdown}>
                        Xuất phiên
                    </Button>
                </Tooltip>
            </div>
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
            {loading && messages[messages.length - 1]?.role !== 'assistant' && (
                <div className="flex justify-start">
                    <div className="max-w-[80%] flex gap-3">
                        <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#dc2626' }} />
                        <div className="bg-white border p-3 rounded-lg shadow-sm">
                            <Spin /> <span className="text-gray-400 text-sm ml-2">Đang xử lý...</span>
                        </div>
                    </div>
                </div>
            )}
            {lastDebugMetrics && !loading && (
                <RAGDebugPanel metrics={lastDebugMetrics as RAGDebugMetrics} />
            )}
        </div>
    );
}

'use client';

import React, { useState, KeyboardEvent } from 'react';
import { Input, Button, Tooltip } from 'antd';
import { SendOutlined, AudioOutlined } from '@ant-design/icons';

const { TextArea } = Input;

interface ChatInputProps {
    onSend: (message: string) => void;
    isLoading: boolean;
    disabled?: boolean;
    onOpenLiveVoice?: () => void;
}

/**
 * Component Input Chat
 */
export default function ChatInput({ onSend, isLoading, disabled, onOpenLiveVoice }: ChatInputProps) {
    const [message, setMessage] = useState('');

    const handleSend = () => {
        if (message.trim() && !isLoading && !disabled) {
            onSend(message.trim());
            setMessage('');
        }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="p-4 bg-white border-t border-gray-200">
            <div className="flex gap-2 items-end max-w-4xl mx-auto">
                <TextArea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={disabled
                        ? "Vui lòng chọn ít nhất một dataset để bắt đầu..."
                        : "Đặt câu hỏi cho AI..."
                    }
                    autoSize={{ minRows: 1, maxRows: 4 }}
                    disabled={disabled}
                    className="flex-1 rounded-lg"
                    style={{ resize: 'none' }}
                />
                {onOpenLiveVoice && (
                    <Tooltip title="Bật Live Voice Mode">
                        <Button
                            type="default"
                            shape="circle"
                            icon={<AudioOutlined className="text-red-600" />}
                            onClick={onOpenLiveVoice}
                            disabled={disabled || isLoading}
                            className="h-10 w-10 flex items-center justify-center border-gray-300 hover:border-red-500"
                        />
                    </Tooltip>
                )}
                <Button
                    type="primary"
                    icon={<SendOutlined />}
                    onClick={handleSend}
                    loading={isLoading}
                    disabled={!message.trim() || disabled}
                    className="h-auto py-2 bg-red-700 hover:bg-red-800 border-red-700"
                >
                    Gửi
                </Button>
            </div>
            <div className="text-center text-xs text-gray-400 mt-2">
                AI có thể mắc lỗi. Vui lòng kiểm tra lại thông tin quan trọng.
            </div>
        </div>
    );
}

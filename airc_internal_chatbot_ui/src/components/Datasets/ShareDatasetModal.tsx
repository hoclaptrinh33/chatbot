'use client';

import React, { useState } from 'react';
import { Modal, Radio, message, Space, Typography } from 'antd';
import { AxiosError } from 'axios';
import { ShareAltOutlined } from '@ant-design/icons';
import datasetService from '@/services/datasetService';

const { Text } = Typography;

interface ShareDatasetModalProps {
    datasetId: string;
    open: boolean;
    onClose: () => void;
    onSuccess?: () => void;
}

/**
 * Modal component để chia sẻ Dataset với Students
 * Chỉ Admin và Teacher (owner) được sử dụng
 */
export default function ShareDatasetModal({
    datasetId,
    open,
    onClose,
    onSuccess
}: ShareDatasetModalProps) {
    const [shareMode, setShareMode] = useState<'all' | 'specific'>('all');
    const [sharing, setSharing] = useState(false);

    const handleShare = async () => {
        try {
            setSharing(true);

            if (shareMode === 'all') {
                // Share với tất cả students
                await datasetService.shareDataset(datasetId, { all_students: true });
                message.success('Đã chia sẻ dataset với tất cả sinh viên');
            } else {
                // TODO: Implement specific students selection
                // Cần thêm API để lấy danh sách students từ Auth Service
                message.info('Chức năng chọn sinh viên cụ thể đang được phát triển');
                return;
            }

            onSuccess?.();
            onClose();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            console.error('Share dataset error:', error);
            message.error(
                err.response?.data?.detail || 'Chia sẻ dataset thất bại'
            );
        } finally {
            setSharing(false);
        }
    };

    return (
        <Modal
            title={
                <Space>
                    <ShareAltOutlined />
                    <span>Chia sẻ Dataset</span>
                </Space>
            }
            open={open}
            onCancel={onClose}
            onOk={handleShare}
            confirmLoading={sharing}
            okText="Chia sẻ"
            cancelText="Hủy"
        >
            <Space direction="vertical" style={{ width: '100%' }} size="large">
                <Text>
                    Chia sẻ dataset này với sinh viên để họ có thể sử dụng trong Chat.
                </Text>

                <Radio.Group
                    value={shareMode}
                    onChange={(e) => setShareMode(e.target.value)}
                >
                    <Space direction="vertical">
                        <Radio value="all">Tất cả sinh viên</Radio>
                        <Radio value="specific" disabled>
                            Sinh viên cụ thể (Sắp có)
                        </Radio>
                    </Space>
                </Radio.Group>

                {shareMode === 'all' && (
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                        Dataset sẽ hiển thị trong danh sách datasets của tất cả sinh viên
                    </Text>
                )}
            </Space>
        </Modal>
    );
}

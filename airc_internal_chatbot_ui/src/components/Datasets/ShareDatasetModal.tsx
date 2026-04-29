'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { Modal, Radio, message, Space, Typography, Select, Tag, Empty, Spin } from 'antd';
import { AxiosError } from 'axios';
import { ShareAltOutlined } from '@ant-design/icons';
import datasetService from '@/services/datasetService';
import authService, { User } from '@/services/authService';
import useAuthStore from '@/stores/authStore';

const { Text } = Typography;
const { Option } = Select;

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
    const { token } = useAuthStore();
    const [shareMode, setShareMode] = useState<'all' | 'specific'>('specific');
    const [loadingData, setLoadingData] = useState(false);
    const [sharing, setSharing] = useState(false);
    const [internUsers, setInternUsers] = useState<User[]>([]);
    const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
    const [currentSharedUserIds, setCurrentSharedUserIds] = useState<string[]>([]);

    const userMap = useMemo(() => {
        const entries = internUsers.map((u) => [u.id, u] as const);
        return new Map(entries);
    }, [internUsers]);

    const resetModalState = () => {
        setShareMode('specific');
        setSelectedUserIds([]);
        setCurrentSharedUserIds([]);
    };

    const handleClose = () => {
        resetModalState();
        onClose();
    };

    useEffect(() => {
        const fetchModalData = async () => {
            if (!open || !token || !datasetId) return;

            setLoadingData(true);
            try {
                // Chỉ lấy danh sách intern/guest cho mục đích chia sẻ dataset.
                const users = await authService.getAllUsers(token, 'intern_guest');
                setInternUsers(users);

                const dataset = await datasetService.getDataset(datasetId);
                const sharedIds = dataset.shared_with || [];

                setCurrentSharedUserIds(sharedIds);
                setSelectedUserIds(sharedIds);
            } catch (error: unknown) {
                const err = error as AxiosError<{ detail?: string }>;
                message.error(err.response?.data?.detail || 'Không thể tải dữ liệu chia sẻ');
            } finally {
                setLoadingData(false);
            }
        };

        fetchModalData();
    }, [open, token, datasetId]);

    useEffect(() => {
        if (!open) {
            resetModalState();
        }
    }, [open]);

    const handleShare = async () => {
        if (!token) {
            message.error('Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.');
            return;
        }

        try {
            setSharing(true);

            const userIdsToShare =
                shareMode === 'all'
                    ? internUsers.map((u) => u.id)
                    : selectedUserIds;

            if (shareMode === 'specific' && userIdsToShare.length === 0) {
                message.warning('Vui lòng chọn ít nhất 1 user để chia sẻ dataset');
                return;
            }

            if (shareMode === 'all') {
                await datasetService.shareDataset(datasetId, { user_ids: userIdsToShare });
                message.success(`Đã chia sẻ dataset cho toàn bộ ${userIdsToShare.length} intern/guest`);
            } else {
                await datasetService.shareDataset(datasetId, { user_ids: userIdsToShare });
                message.success(`Đã chia sẻ dataset cho ${userIdsToShare.length} user`);
            }

            setCurrentSharedUserIds(userIdsToShare);

            onSuccess?.();
            handleClose();
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
            onCancel={handleClose}
            onOk={handleShare}
            confirmLoading={sharing || loadingData}
            okText="Chia sẻ"
            cancelText="Hủy"
        >
            <Spin spinning={loadingData}>
                <Space direction="vertical" style={{ width: '100%' }} size="large">
                    <Text>
                        Chia sẻ dataset này cho intern/guest để họ có thể sử dụng trong Chat.
                    </Text>

                    <div>
                        <Text strong>Danh sách đã share hiện tại</Text>
                        <div className="mt-2 min-h-[36px] rounded border border-dashed border-gray-300 p-2">
                            {currentSharedUserIds.length > 0 ? (
                                <Space size={[6, 6]} wrap>
                                    {currentSharedUserIds.map((uid) => {
                                        const user = userMap.get(uid);
                                        return (
                                            <Tag key={uid} color="blue">
                                                {user ? `${user.full_name} (${user.email})` : uid}
                                            </Tag>
                                        );
                                    })}
                                </Space>
                            ) : (
                                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Chưa chia sẻ cho user nào" />
                            )}
                        </div>
                    </div>

                    <Radio.Group
                        value={shareMode}
                        onChange={(e) => setShareMode(e.target.value)}
                    >
                        <Space direction="vertical">
                            <Radio value="specific">Chọn user cụ thể</Radio>
                            <Radio value="all">Tất cả intern/guest</Radio>
                        </Space>
                    </Radio.Group>

                    {shareMode === 'specific' && (
                        <div>
                            <Text strong>Chọn user để chia sẻ</Text>
                            <Select
                                mode="multiple"
                                allowClear
                                className="w-full mt-2"
                                placeholder="Tìm theo tên hoặc email"
                                value={selectedUserIds}
                                onChange={(values) => setSelectedUserIds(values)}
                                showSearch
                                optionFilterProp="label"
                                filterOption={(input, option) =>
                                    String(option?.label || '')
                                        .toLowerCase()
                                        .includes(input.toLowerCase())
                                }
                            >
                                {internUsers.map((user) => (
                                    <Option
                                        key={user.id}
                                        value={user.id}
                                        label={`${user.full_name} ${user.email}`}
                                    >
                                        <div className="flex flex-col leading-tight">
                                            <span>{user.full_name}</span>
                                            <span className="text-xs text-gray-500">{user.email}</span>
                                        </div>
                                    </Option>
                                ))}
                            </Select>
                        </div>
                    )}

                    {shareMode === 'all' && (
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                            Dataset sẽ được chia sẻ cho toàn bộ intern/guest ({internUsers.length} user).
                        </Text>
                    )}
                </Space>
            </Spin>
        </Modal>
    );
}

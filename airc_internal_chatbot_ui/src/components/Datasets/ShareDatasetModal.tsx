'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { Modal, Radio, message, Space, Typography, Select, Spin } from 'antd';
import { AxiosError } from 'axios';
import { ShareAltOutlined } from '@ant-design/icons';
import datasetService from '@/services/datasetService';
import authService, { User } from '@/services/authService';
import useAuthStore from '@/stores/authStore';

const { Text } = Typography;

interface ShareDatasetModalProps {
    datasetId: string;
    open: boolean;
    onClose: () => void;
    onSuccess?: () => void;
    initialSharedWith?: string[];
}

export default function ShareDatasetModal({
    datasetId,
    open,
    onClose,
    onSuccess,
    initialSharedWith = [],
}: ShareDatasetModalProps) {
    const { token } = useAuthStore();
    const isAllInitially = initialSharedWith.includes('*');
    const [shareMode, setShareMode] = useState<'all' | 'specific'>(isAllInitially ? 'all' : 'specific');
    const [sharing, setSharing] = useState(false);
    const [students, setStudents] = useState<User[]>([]);
    const [selectedIds, setSelectedIds] = useState<string[]>(
        initialSharedWith.filter((id) => id && id !== '*')
    );
    const [loadingStudents, setLoadingStudents] = useState(false);

    useEffect(() => {
        if (!open) return;
        const nextAll = initialSharedWith.includes('*');
        setShareMode(nextAll ? 'all' : 'specific');
        setSelectedIds(initialSharedWith.filter((id) => id && id !== '*'));
    }, [open, initialSharedWith]);

    useEffect(() => {
        if (!open || !token) return;
        let cancelled = false;
        const load = async () => {
            setLoadingStudents(true);
            try {
                const data = await authService.getAllUsers(token, 'student');
                if (!cancelled) setStudents(data);
            } catch (error) {
                console.error(error);
                if (!cancelled) {
                    message.error('Không tải được danh sách sinh viên');
                }
            } finally {
                if (!cancelled) setLoadingStudents(false);
            }
        };
        load();
        return () => {
            cancelled = true;
        };
    }, [open, token]);

    const options = useMemo(
        () =>
            students.map((student) => ({
                value: student.id,
                label: `${student.full_name} (${student.email})`,
            })),
        [students]
    );

    const handleShare = async () => {
        try {
            setSharing(true);

            if (shareMode === 'all') {
                await datasetService.shareDataset(datasetId, { all_students: true });
                message.success('Đã chia sẻ dataset với tất cả sinh viên');
            } else {
                if (selectedIds.length === 0) {
                    message.warning('Chọn ít nhất một sinh viên');
                    return;
                }
                await datasetService.shareDataset(datasetId, { student_ids: selectedIds });
                message.success(`Đã chia sẻ với ${selectedIds.length} sinh viên`);
            }

            onSuccess?.();
            onClose();
        } catch (error: unknown) {
            const err = error as AxiosError<{ detail: string }>;
            console.error('Share dataset error:', error);
            message.error(err.response?.data?.detail || 'Chia sẻ dataset thất bại');
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
                        <Radio value="specific">Chọn sinh viên cụ thể</Radio>
                    </Space>
                </Radio.Group>

                {shareMode === 'specific' && (
                    <Spin spinning={loadingStudents}>
                        <Select
                            mode="multiple"
                            allowClear
                            showSearch
                            placeholder="Tìm theo tên hoặc email"
                            style={{ width: '100%' }}
                            value={selectedIds}
                            onChange={setSelectedIds}
                            options={options}
                            optionFilterProp="label"
                            maxTagCount="responsive"
                        />
                    </Spin>
                )}
            </Space>
        </Modal>
    );
}

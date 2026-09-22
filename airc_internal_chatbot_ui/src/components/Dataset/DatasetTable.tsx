'use client';

import React from 'react';
import { Table, Button, Space, Popconfirm, Tooltip } from 'antd';
import { DeleteOutlined, DownloadOutlined, ShareAltOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Dataset } from '@/services/datasetService';
import dayjs from 'dayjs';

interface DatasetTableProps {
    datasets: Dataset[];
    loading: boolean;
    onDelete?: (id: string) => void;
    onShare?: (dataset: Dataset) => void;
    onDownload?: (dataset: Dataset) => void;
}

/**
 * Component bang danh sach Datasets
 */
const DatasetTable: React.FC<DatasetTableProps> = ({
    datasets,
    loading,
    onDelete,
    onShare,
    onDownload
}) => {
    const columns: ColumnsType<Dataset> = [
        {
            title: 'Tên Dataset',
            dataIndex: 'name',
            key: 'name',
            render: (text) => <span className="font-medium text-blue-600">{text}</span>,
            sorter: (a, b) => a.name.localeCompare(b.name),
        },
        {
            title: 'Ngay tao',
            dataIndex: 'created_at',
            key: 'created_at',
            render: (text) => text ? dayjs(text).format('DD/MM/YYYY') : '-',
        },
        {
            title: 'Hanh dong',
            key: 'action',
            render: (_, record) => (
                <Space size="middle">
                    {onDownload && (
                        <Tooltip title="Tải xuống (Chưa hỗ trợ)">
                            <Button
                                type="text"
                                icon={<DownloadOutlined />}
                                disabled
                                className="text-gray-400"
                            />
                        </Tooltip>
                    )}
                    {onShare && (
                        <Tooltip title="Chia sẻ">
                            <Button
                                type="text"
                                icon={<ShareAltOutlined />}
                                onClick={() => onShare(record)}
                                className="text-blue-600 hover:text-blue-800"
                            />
                        </Tooltip>
                    )}
                    {onDelete && (
                        <Tooltip title="Xóa">
                            <Popconfirm
                                title="Xóa dataset này?"
                                description="Bạn có chắc muốn xóa dataset này không?"
                                onConfirm={() => onDelete(record.id)}
                                okText="Xóa"
                                cancelText="Hủy"
                                okButtonProps={{ danger: true }}
                            >
                                <Button
                                    type="text"
                                    danger
                                    icon={<DeleteOutlined />}
                                />
                            </Popconfirm>
                        </Tooltip>
                    )}
                </Space>
            ),
        },
    ];

    return (
        <Table
            columns={columns}
            dataSource={datasets}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
            className="border rounded-lg overflow-hidden shadow-sm bg-white"
        />
    );
};

export default DatasetTable;

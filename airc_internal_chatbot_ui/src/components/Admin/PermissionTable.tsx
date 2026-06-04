'use client';

import React from 'react';
import { Table, Button, Space, Tag, Popconfirm, Tooltip } from 'antd';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Permission } from '@/services/rbacService';

interface PermissionTableProps {
    permissions: Permission[];
    loading: boolean;
    onEdit?: (permission: Permission) => void;
    onDelete?: (id: string) => void;
}

/**
 * Component bang danh sach Permissions
 */
const PermissionTable: React.FC<PermissionTableProps> = ({
    permissions,
    loading,
    onEdit,
    onDelete
}) => {
    // Cau hinh cot cho bang
    const columns: ColumnsType<Permission> = [
        {
            title: 'Tên quyền hạn',
            dataIndex: 'name',
            key: 'name',
            render: (text, record) => (
                <Space>
                    <span className="font-medium">{text}</span>
                    {record.is_system && <Tag color="purple">SYSTEM</Tag>}
                </Space>
            ),
            sorter: (a, b) => a.name.localeCompare(b.name),
        },
        {
            title: 'Code',
            dataIndex: 'code',
            key: 'code',
            render: (text) => <code className="text-xs bg-gray-100 px-1 rounded">{text}</code>,
        },
        {
            title: 'Tài nguyên',
            dataIndex: 'resource',
            key: 'resource',
            render: (text) => <Tag color="cyan">{text.toUpperCase()}</Tag>,
            filters: [
                { text: 'Auth', value: 'auth' },
                { text: 'Người dùng', value: 'users' },
                { text: 'RBAC', value: 'rbac' },
                { text: 'Dataset', value: 'datasets' },
                { text: 'Chatbot', value: 'chatbots' },
            ],
            onFilter: (value, record) => record.resource.includes(value as string),
        },
        {
            title: 'Hành vi',
            dataIndex: 'action',
            key: 'action',
            render: (text) => {
                let color = 'default';
                if (text === 'create') color = 'green';
                if (text === 'view' || text === 'read') color = 'blue';
                if (text === 'update') color = 'orange';
                if (text === 'delete') color = 'red';
                if (text === 'manage') color = 'purple';
                return <Tag color={color}>{text.toUpperCase()}</Tag>;
            },
        },
        {
            title: 'Mô tả',
            dataIndex: 'description',
            key: 'description',
            ellipsis: true,
        },
        {
            title: 'Hành động',
            key: 'action',
            render: (_, record) => (
                <Space size="middle">
                    {onEdit && (
                        <Tooltip title="Sửa">
                            <Button
                                type="text"
                                icon={<EditOutlined />}
                                onClick={() => onEdit(record)}
                                disabled={record.is_system} // System permissions cannot be edited easily
                                className="text-blue-600 hover:text-blue-800"
                            />
                        </Tooltip>
                    )}
                    {onDelete && (
                        <Tooltip title={record.is_system ? "Không thể xóa quyền hạn hệ thống" : "Xóa"}>
                            <Popconfirm
                                title="Xóa permission này?"
                                description="Bạn có chắc muốn xóa permission này không?"
                                onConfirm={() => onDelete(record.id || record._id!)}
                                okText="Xóa"
                                cancelText="Hủy"
                                okButtonProps={{ danger: true }}
                                disabled={record.is_system}
                            >
                                <Button
                                    type="text"
                                    danger
                                    icon={<DeleteOutlined />}
                                    disabled={record.is_system}
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
            dataSource={permissions}
            rowKey={(record) => record.id || record._id || Math.random().toString()}
            loading={loading}
            pagination={{ pageSize: 10 }}
            className="border rounded-lg overflow-hidden shadow-sm bg-white"
        />
    );
};

export default PermissionTable;

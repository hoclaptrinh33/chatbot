'use client';

import React from 'react';
import { Table, Button, Space, Tag, Popconfirm, Tooltip } from 'antd';
import { EditOutlined, DeleteOutlined, SettingOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Role } from '@/services/rbacService';

interface RoleTableProps {
    roles: Role[];
    loading: boolean;
    onEdit?: (role: Role) => void;
    onDelete?: (id: string) => void;
    onAssignPermissions?: (role: Role) => void;
}

/**
 * Component bang danh sach Roles
 */
const RoleTable: React.FC<RoleTableProps> = ({
    roles,
    loading,
    onEdit,
    onDelete,
    onAssignPermissions
}) => {
    const columns: ColumnsType<Role> = [
        {
            title: 'Tên vai trò',
            dataIndex: 'name',
            key: 'name',
            render: (text, record) => (
                <Space>
                    <Tag color={text === 'admin' ? 'red' : text === 'teacher' ? 'blue' : 'green'}>
                        {text.toUpperCase()}
                    </Tag>
                    {record.is_system && <Tag color="purple">HỆ THỐNG</Tag>}
                </Space>
            ),
        },
        {
            title: 'Code',
            dataIndex: 'code',
            key: 'code',
            render: (text) => <code className="text-xs bg-gray-100 px-1 rounded">{text}</code>,
        },
        {
            title: 'Mô tả',
            dataIndex: 'description',
            key: 'description',
        },
        {
            title: 'Quyền hạn',
            dataIndex: 'permission_count',
            key: 'permission_count',
            render: (count) => (
                <span className="text-gray-500">
                    {count !== undefined ? `${count} quyền` : '0 quyền'}
                </span>
            ),
        },
        {
            title: 'Hành động',
            key: 'action',
            render: (_, record) => (
                <Space size="middle">
                    {onAssignPermissions && (
                        <Tooltip title="Gán quyền">
                            <Button
                                type="text"
                                icon={<SettingOutlined />}
                                onClick={() => onAssignPermissions(record)}
                                disabled={false} // Always allowed to change permissions even for system roles? Maybe.
                                className="text-purple-600 hover:text-purple-800"
                            />
                        </Tooltip>
                    )}
                    {onEdit && (
                        <Tooltip title="Sửa">
                            <Button
                                type="text"
                                icon={<EditOutlined />}
                                onClick={() => onEdit(record)}
                                disabled={record.is_system}
                                className="text-blue-600 hover:text-blue-800"
                            />
                        </Tooltip>
                    )}
                    {onDelete && (
                        <Tooltip title={record.is_system ? "Không thể xóa vai trò hệ thống" : "Xóa"}>
                            <Popconfirm
                                title="Xóa vai trò này?"
                                description="Bạn có chắc muốn xóa vai trò này không?"
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
            dataSource={roles}
            rowKey={(record) => record.id || record._id || Math.random().toString()}
            loading={loading}
            pagination={false}
            className="border rounded-lg overflow-hidden shadow-sm bg-white"
        />
    );
};

export default RoleTable;

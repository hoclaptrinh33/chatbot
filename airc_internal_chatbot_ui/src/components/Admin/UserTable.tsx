import React from 'react';
import { Table, Button, Tag, Space, Popconfirm } from 'antd';
import { EditOutlined, DeleteOutlined, SafetyCertificateOutlined } from '@ant-design/icons'; // Added Icons
import { User } from '@/services/authService';

interface UserTableProps {
    users: User[];
    loading: boolean;
    onManageRoles: (user: User) => void;
    onEditUser: (user: User) => void; // New prop
    onDeleteUser: (user: User) => void; // New prop
}

const UserTable: React.FC<UserTableProps> = ({
    users,
    loading,
    onManageRoles,
    onEditUser,
    onDeleteUser
}) => {
    const columns = [
        {
            title: 'Ho va Ten',
            dataIndex: 'full_name',
            key: 'full_name',
            render: (text: string) => <span className="font-medium">{text}</span>
        },
        {
            title: 'Email',
            dataIndex: 'email',
            key: 'email',
        },
        {
            title: 'Base Role',
            dataIndex: 'role',
            key: 'role',
            render: (role: string) => {
                let color = 'geekblue';
                if (role === 'admin') color = 'volcano';
                if (role === 'teacher') color = 'green';
                return (
                    <Tag color={color}>
                        {role.toUpperCase()}
                    </Tag>
                );
            }
        },
        {
            title: 'Trang thai',
            dataIndex: 'is_active',
            key: 'is_active',
            render: (active: boolean) => (
                <Tag color={active ? 'success' : 'error'}>
                    {active ? 'ACTIVE' : 'INACTIVE'}
                </Tag>
            )
        },
        {
            title: 'Hanh dong',
            key: 'action',
            render: (_: unknown, record: User) => (
                <Space size="small">
                    <Button
                        icon={<SafetyCertificateOutlined />}
                        onClick={() => onManageRoles(record)}
                        className="bg-orange-50 text-orange-600 border-orange-200 hover:bg-orange-100"
                    >
                        Roles
                    </Button>
                    <Button
                        icon={<EditOutlined />}
                        onClick={() => onEditUser(record)}
                    >
                        Sua
                    </Button>
                    <Popconfirm
                        title="Ban co chac muon xoa user nay?"
                        onConfirm={() => onDeleteUser(record)}
                        okText="Xoa"
                        cancelText="Huy"
                    >
                        <Button
                            danger
                            icon={<DeleteOutlined />}
                        />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <Table
            columns={columns}
            dataSource={users}
            rowKey="id"
            loading={loading}
        />
    );
};

export default UserTable;

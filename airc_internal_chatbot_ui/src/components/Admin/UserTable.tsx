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
            title: 'Họ và tên',
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
            title: 'Vai trò',
            dataIndex: 'role',
            key: 'role',
            render: (role: string) => {
                let color = 'geekblue';
                if (role === 'admin') color = 'volcano';
                if (role === 'employee') color = 'green';
                if (role === 'intern_guest') color = 'gold';
                return (
                    <Tag color={color}>
                        {role.toUpperCase()}
                    </Tag>
                );
            }
        },
        {
            title: 'Phòng ban/Đơn vị',
            dataIndex: 'department',
            key: 'department',
            render: (department?: string) => department || 'Chưa cập nhật'
        },
        {
            title: 'Trạng thái',
            dataIndex: 'is_active',
            key: 'is_active',
            render: (active: boolean) => (
                <Tag color={active ? 'success' : 'error'}>
                    {active ? 'ĐANG HOẠT ĐỘNG' : 'TẠM KHÓA'}
                </Tag>
            )
        },
        {
            title: 'Hành động',
            key: 'action',
            render: (_: unknown, record: User) => (
                <Space size="small">
                    <Button
                        icon={<SafetyCertificateOutlined />}
                        onClick={() => onManageRoles(record)}
                        className="bg-orange-50 text-orange-600 border-orange-200 hover:bg-orange-100"
                    >
                        Vai trò
                    </Button>
                    <Button
                        icon={<EditOutlined />}
                        onClick={() => onEditUser(record)}
                    >
                        Sửa
                    </Button>
                    <Popconfirm
                        title="Bạn có chắc muốn xóa người dùng này?"
                        onConfirm={() => onDeleteUser(record)}
                        okText="Xóa"
                        cancelText="Hủy"
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

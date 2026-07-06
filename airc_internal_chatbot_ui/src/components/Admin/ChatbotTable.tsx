import React from 'react';
import { Table, Tag, Button, Space, Tooltip, Popconfirm } from 'antd';
import { EditOutlined, DeleteOutlined, RobotOutlined } from '@ant-design/icons';
import { Chatbot } from '@/types/chatbot';
import { ColumnsType } from 'antd/es/table';

interface ChatbotTableProps {
    chatbots: Chatbot[];
    loading: boolean;
    onEdit: (chatbot: Chatbot) => void;
    onDelete: (chatbot: Chatbot) => void;
}

const ChatbotTable: React.FC<ChatbotTableProps> = ({ chatbots, loading, onEdit, onDelete }) => {
    const columns: ColumnsType<Chatbot> = [
        {
            title: 'Tên',
            dataIndex: 'name',
            key: 'name',
            render: (text, record) => (
                <Space>
                    {record.icon ? <div dangerouslySetInnerHTML={{ __html: record.icon }} /> : <RobotOutlined />}
                    <span className="font-medium">{text}</span>
                </Space>
            ),
        },
        {
            title: 'Mô tả',
            dataIndex: 'description',
            key: 'description',
            ellipsis: true,
        },
        {
            title: 'Chế độ hiển thị',
            dataIndex: 'visibility',
            key: 'visibility',
            render: (visibility: string) => {
                let color = 'default';
                let text = visibility.toUpperCase();
                if (visibility === 'public') {
                    color = 'green';
                    text = 'CÔNG KHAI';
                }
                if (visibility === 'private') {
                    color = 'orange';
                    text = 'RIÊNG TƯ';
                }
                return <Tag color={color}>{text}</Tag>;
            },
        },
        {
            title: 'Vai trò được phép',
            dataIndex: 'allowed_roles',
            key: 'allowed_roles',
            render: (roles: string[]) => (
                <>
                    {roles.map((role) => (
                        <Tag key={role} color="geekblue">
                            {role.toUpperCase()}
                        </Tag>
                    ))}
                </>
            ),
        },
        {
            title: 'Bộ dữ liệu',
            dataIndex: 'dataset_ids',
            key: 'dataset_ids',
            render: (ids: string[] | null | undefined) => (
                <Tag>{(ids || []).length} Bộ dữ liệu</Tag>
            ),
        },
        {
            title: 'Trạng thái',
            dataIndex: 'is_active',
            key: 'is_active',
            render: (isActive: boolean) => (
                <Tag color={isActive ? 'success' : 'error'}>
                    {isActive ? 'HOẠT ĐỘNG' : 'TẠM NGƯNG'}
                </Tag>
            )
        },
        {
            title: 'Thao tác',
            key: 'actions',
            render: (_, record) => (
                <Space size="middle">
                    <Tooltip title="Chỉnh sửa Trợ lý ảo">
                        <Button
                            type="text"
                            icon={<EditOutlined className="text-blue-500" />}
                            onClick={() => onEdit(record)}
                        />
                    </Tooltip>
                    <Tooltip title="Xóa Trợ lý ảo">
                        <Popconfirm
                            title="Xóa Trợ lý ảo"
                            description="Bạn có chắc chắn muốn xóa trợ lý ảo này không?"
                            onConfirm={() => onDelete(record)}
                            okText="Đồng ý"
                            cancelText="Hủy"
                            okButtonProps={{ danger: true }}
                        >
                            <Button
                                type="text"
                                icon={<DeleteOutlined className="text-red-500" />}
                            />
                        </Popconfirm>
                    </Tooltip>
                </Space>
            ),
        },
    ];

    return (
        <Table
            columns={columns}
            dataSource={chatbots}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
        />
    );
};

export default ChatbotTable;

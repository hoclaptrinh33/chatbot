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
            title: 'Name',
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
            title: 'Description',
            dataIndex: 'description',
            key: 'description',
            ellipsis: true,
        },
        {
            title: 'Visibility',
            dataIndex: 'visibility',
            key: 'visibility',
            render: (visibility: string) => {
                let color = 'default';
                if (visibility === 'public') color = 'green';
                if (visibility === 'private') color = 'orange';
                return <Tag color={color}>{visibility.toUpperCase()}</Tag>;
            },
        },
        {
            title: 'Allowed Roles',
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
            title: 'Datasets',
            dataIndex: 'dataset_ids',
            key: 'dataset_ids',
            render: (ids: string[] | null | undefined) => (
                <Tag>{(ids || []).length} Datasets</Tag>
            ),
        },
        {
            title: 'Status',
            dataIndex: 'is_active',
            key: 'is_active',
            render: (isActive: boolean) => (
                <Tag color={isActive ? 'success' : 'error'}>
                    {isActive ? 'ACTIVE' : 'INACTIVE'}
                </Tag>
            )
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (_, record) => (
                <Space size="middle">
                    <Tooltip title="Edit Chatbot">
                        <Button
                            type="text"
                            icon={<EditOutlined className="text-blue-500" />}
                            onClick={() => onEdit(record)}
                        />
                    </Tooltip>
                    <Tooltip title="Delete Chatbot">
                        <Popconfirm
                            title="Delete Chatbot"
                            description="Are you sure you want to delete this chatbot?"
                            onConfirm={() => onDelete(record)}
                            okText="Yes"
                            cancelText="No"
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

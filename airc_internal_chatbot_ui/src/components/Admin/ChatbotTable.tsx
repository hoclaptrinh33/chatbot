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
    const renderAccessSummary = (record: Chatbot) => {
        const userCount = (record.allowed_user_ids || []).length;
        const departmentCount = (record.allowed_departments || []).length;

        if (userCount === 0 && departmentCount === 0) {
            return <Tag color="orange">Riêng tư (chỉ quản trị viên)</Tag>;
        }

        return (
            <Space wrap>
                {userCount > 0 && <Tag color="blue">{userCount} người dùng</Tag>}
                {departmentCount > 0 && <Tag color="purple">{departmentCount} phòng ban</Tag>}
            </Space>
        );
    };

    const columns: ColumnsType<Chatbot> = [
        {
            title: 'Tên chatbot',
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
            title: 'Hiển thị',
            dataIndex: 'visibility',
            key: 'visibility',
            render: (visibility: string) => {
                let color = 'default';
                if (visibility === 'public') color = 'green';
                if (visibility === 'private') color = 'orange';
                return <Tag color={color}>{visibility === 'public' ? 'Công khai' : 'Riêng tư'}</Tag>;
            },
        },
        {
            title: 'Phân quyền truy cập',
            key: 'access_scope',
            render: (_, record) => renderAccessSummary(record),
        },
        {
            title: 'Nguồn dữ liệu',
            dataIndex: 'dataset_ids',
            key: 'dataset_ids',
            render: (ids: string[] | null | undefined) => (
                <Tag>{(ids || []).length} dataset</Tag>
            ),
        },
        {
            title: 'Trạng thái',
            dataIndex: 'is_active',
            key: 'is_active',
            render: (isActive: boolean) => (
                <Tag color={isActive ? 'success' : 'error'}>
                    {isActive ? 'Đang hoạt động' : 'Tạm dừng'}
                </Tag>
            )
        },
        {
            title: 'Thao tác',
            key: 'actions',
            render: (_, record) => (
                <Space size="middle">
                    <Tooltip title="Chỉnh sửa chatbot">
                        <Button
                            type="text"
                            icon={<EditOutlined className="text-blue-500" />}
                            onClick={() => onEdit(record)}
                        />
                    </Tooltip>
                    <Tooltip title="Xóa chatbot">
                        <Popconfirm
                            title="Xóa chatbot"
                            description="Bạn có chắc muốn xóa chatbot này không?"
                            onConfirm={() => onDelete(record)}
                            okText="Xóa"
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

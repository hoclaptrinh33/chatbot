'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import datasetService, { Dataset } from '@/services/datasetService';
import { chatbotService } from '@/services/chatbotService';
import { Chatbot } from '@/types/chatbot';
import { Button, Modal, Input, Form, Select, Dropdown, MenuProps, notification } from 'antd';
import { PlusOutlined, MoreOutlined, SearchOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

const DatasetListPage = () => {
    const router = useRouter();
    const [datasets, setDatasets] = useState<Dataset[]>([]);
    const [chatbots, setChatbots] = useState<Chatbot[]>([]);  // ✅ Add chatbots state
    const [loading, setLoading] = useState(false);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [isRenameModalOpen, setIsRenameModalOpen] = useState(false);
    const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
    const [form] = Form.useForm();
    const [renameForm] = Form.useForm();
    const [search, setSearch] = useState('');

    /**
     * Lấy danh sách datasets từ backend
     * Admin: Xem tất cả
     * Teacher: Xem dataset của mình
     * Student: Xem dataset được chia sẻ
     */
    const fetchDatasets = async () => {
        setLoading(true);
        try {
            const data = await datasetService.getDatasets();
            setDatasets(data);
        } catch (error) {
            console.error('Failed to load datasets', error);
            notification.error({ message: 'Không thể tải danh sách bộ dữ liệu' });
        } finally {
            setLoading(false);
        }
    };

    /**
     * Lấy danh sách chatbots để hiển thị trong dropdown
     */
    const fetchChatbots = async () => {
        try {
            const data = await chatbotService.getChatbots();
            setChatbots(data);
        } catch (error) {
            console.error('Failed to load chatbots', error);
        }
    };

    useEffect(() => {
        fetchDatasets();
        fetchChatbots();  // ✅ Load chatbots for selection
    }, []);

    /**
     * Tạo dataset mới và tự động gán vào chatbots đã chọn
     * Dataset chỉ là container chứa files, không có config
     * Config (embedding, chunking) thuộc về Chatbot
     */
    const handleCreateWrapper = async () => {
        try {
            const values = await form.validateFields();
            // ✅ Pass chatbot_ids to backend
            await datasetService.createDataset({
                name: values.name,
                chatbot_ids: values.chatbot_ids || []  // Send selected chatbot IDs
            });
            notification.success({ message: 'Tạo bộ dữ liệu thành công' });
            setIsCreateModalOpen(false);
            form.resetFields();
            fetchDatasets();
        } catch (error) {
            console.error('Create dataset failed', error);
            notification.error({ message: 'Tạo bộ dữ liệu thất bại' });
        }
    };

    /**
     * Đổi tên dataset - chỉ cập nhật name
     */
    const handleRenameWrapper = async () => {
        if (!selectedDataset) return;
        try {
            const values = await renameForm.validateFields();
            await datasetService.updateDataset(selectedDataset.id, {
                name: values.name
            });
            notification.success({ message: 'Đổi tên bộ dữ liệu thành công' });
            setIsRenameModalOpen(false);
            fetchDatasets();
        } catch {
            notification.error({ message: 'Đổi tên bộ dữ liệu thất bại' });
        }
    };

    /**
     * Xóa dataset và dọn dẹp dữ liệu liên quan
     * - Xóa dataset_files
     * - Xóa chunks
     * - Xóa vector index
     */
    const handleDeleteWrapper = async (id: string) => {
        Modal.confirm({
            title: 'Xóa bộ dữ liệu',
            content: 'Bạn có chắc chắn muốn xóa bộ dữ liệu này? Hành động này không thể hoàn tác.',
            okText: 'Xóa',
            okType: 'danger',
            cancelText: 'Hủy',
            onOk: async () => {
                try {
                    await datasetService.deleteDataset(id);
                    notification.success({ message: 'Đã xóa bộ dữ liệu' });
                    fetchDatasets();
                } catch {
                    notification.error({ message: 'Xóa bộ dữ liệu thất bại' });
                }
            }
        });
    };

    const getMenuProps = (dataset: Dataset): MenuProps => ({
        items: [
            {
                key: 'rename',
                label: 'Đổi tên',
                onClick: () => {
                    setSelectedDataset(dataset);
                    renameForm.setFieldsValue({ name: dataset.name });
                    setIsRenameModalOpen(true);
                }
            },
            {
                key: 'delete',
                label: 'Xóa',
                danger: true,
                onClick: () => handleDeleteWrapper(dataset.id)
            }
        ]
    });

    const filteredDatasets = useMemo(() => {
        if (!search.trim()) return datasets;
        return datasets.filter(d => d.name.toLowerCase().includes(search.toLowerCase()));
    }, [datasets, search]);

    return (
        <div className="p-6">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-2xl font-bold">Bộ dữ liệu (Knowledge Base)</h1>
                <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => setIsCreateModalOpen(true)}
                    className="bg-[#0b1220] hover:bg-gray-800"
                >
                    Tạo bộ dữ liệu
                </Button>
            </div>

            <div className="mb-6">
                <Input
                    placeholder="Tìm kiếm bộ dữ liệu..."
                    prefix={<SearchOutlined />}
                    className="max-w-md"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            {loading ? (
                <div>Đang tải...</div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredDatasets.map((dataset) => (
                        <div
                            key={dataset.id}
                            className="relative bg-white border border-gray-200 rounded-xl p-4 hover:shadow-md transition group cursor-pointer"
                            onClick={() => router.push(`/dashboard/datasets/${dataset.id}`)}
                        >
                            <div className="flex items-center gap-4">
                                <div className="h-12 w-12 rounded-lg bg-green-500/10 grid place-items-center text-green-600 font-bold text-xl">
                                    {dataset.name.charAt(0).toUpperCase()}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h3 className="font-semibold text-gray-900 truncate">{dataset.name}</h3>
                                    <p className="text-xs text-gray-500 mt-1">
                                        {dayjs(dataset.created_at).format('DD/MM/YYYY HH:mm')}
                                    </p>
                                </div>
                                <div onClick={(e) => e.stopPropagation()}>
                                    <Dropdown menu={getMenuProps(dataset)} trigger={['click']}>
                                        <Button
                                            type="text"
                                            icon={<MoreOutlined />}
                                            className="text-gray-400 hover:text-gray-600"
                                        />
                                    </Dropdown>
                                </div>
                            </div>
                        </div>
                    ))}
                    {filteredDatasets.length === 0 && !loading && (
                        <div className="col-span-full text-center py-12 text-gray-500">
                            Không tìm thấy bộ dữ liệu nào. Hãy tạo mới để bắt đầu.
                        </div>
                    )}
                </div>
            )}

            {/* Create Dataset Modal - Simple form with Name + Chatbot selection only */}
            <Modal
                title="Tạo bộ dữ liệu"
                open={isCreateModalOpen}
                onCancel={() => setIsCreateModalOpen(false)}
                onOk={handleCreateWrapper}
                okText="Tạo"
                cancelText="Hủy"
                width={500}
            >
                <Form
                    form={form}
                    layout="vertical"
                    initialValues={{ chatbot_ids: [] }}
                >
                    <Form.Item
                        name="name"
                        label="Tên bộ dữ liệu"
                        rules={[
                            { required: true, message: 'Vui lòng nhập tên bộ dữ liệu' },
                            { min: 3, message: 'Tên phải dài ít nhất 3 ký tự' }
                        ]}
                    >
                        <Input
                            placeholder="Ví dụ: Bộ dữ liệu Ngữ pháp Tiếng Anh"
                            maxLength={200}
                        />
                    </Form.Item>

                    <Form.Item
                        name="chatbot_ids"
                        label="Gán cho Trợ lý ảo (Tùy chọn)"
                        tooltip="Chọn các trợ lý ảo sẽ sử dụng bộ dữ liệu này. Cấu hình phân mảnh (chunking) và nhúng vector (embedding) sẽ được quản lý tại cài đặt của từng Trợ lý ảo."
                    >
                        <Select
                            mode="multiple"
                            placeholder="Chọn trợ lý ảo sử dụng bộ dữ liệu này"
                            allowClear
                            showSearch
                            filterOption={(input, option) =>
                                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                            }
                            options={chatbots.map(bot => ({
                                label: bot.name,
                                value: bot.id
                            }))}
                        />
                    </Form.Item>

                    <div className="text-sm text-gray-500 mt-2 p-3 bg-blue-50 rounded-md">
                        <strong>Lưu ý:</strong> Dataset là nơi chứa các file tài liệu.
                        Cấu hình embedding và chunking được quản lý tại <strong>Cài đặt Chatbot</strong>.
                    </div>
                </Form>
            </Modal>

            {/* Rename Modal */}
            <Modal
                title="Đổi tên bộ dữ liệu"
                open={isRenameModalOpen}
                onCancel={() => setIsRenameModalOpen(false)}
                onOk={handleRenameWrapper}
                okText="Lưu"
                cancelText="Hủy"
            >
                <Form form={renameForm} layout="vertical">
                    <Form.Item 
                        name="name" 
                        label="Tên bộ dữ liệu" 
                        rules={[{ required: true, message: 'Vui lòng nhập tên bộ dữ liệu' }]}
                    >
                        <Input />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default DatasetListPage;

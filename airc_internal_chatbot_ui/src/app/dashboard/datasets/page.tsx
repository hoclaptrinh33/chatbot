'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import datasetService, { Dataset } from '@/services/datasetService';
import { chatbotService } from '@/services/chatbotService';
import { Chatbot } from '@/types/chatbot';
import { Button, Modal, Input, Form, Select, Dropdown, MenuProps, notification } from 'antd';
import { PlusOutlined, MoreOutlined, SearchOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import ShareDatasetModal from '@/components/Datasets/ShareDatasetModal';
import useAuthStore from '@/stores/authStore';

const DatasetListPage = () => {
    const router = useRouter();
    const [datasets, setDatasets] = useState<Dataset[]>([]);
    const [chatbots, setChatbots] = useState<Chatbot[]>([]);  // ✅ Add chatbots state
    const [loading, setLoading] = useState(false);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [isRenameModalOpen, setIsRenameModalOpen] = useState(false);
    const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
    const [isShareModalOpen, setIsShareModalOpen] = useState(false);
    const [shareDatasetId, setShareDatasetId] = useState<string | null>(null);
    const [form] = Form.useForm();
    const [renameForm] = Form.useForm();
    const [search, setSearch] = useState('');
    const { user } = useAuthStore();

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
            notification.error({ message: 'Không thể tải dataset' });
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
            notification.success({ message: 'Đã tạo dataset thành công' });
            setIsCreateModalOpen(false);
            form.resetFields();
            fetchDatasets();
        } catch (error) {
            console.error('Create dataset failed', error);
            notification.error({ message: 'Không thể tạo dataset' });
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
            notification.success({ message: 'Đã đổi tên dataset thành công' });
            setIsRenameModalOpen(false);
            fetchDatasets();
        } catch {
            notification.error({ message: 'Không thể đổi tên dataset' });
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
            title: 'Xóa dataset',
            content: 'Bạn có chắc muốn xóa dataset này không? Hành động này không thể hoàn tác.',
            okText: 'Xóa',
            okType: 'danger',
            cancelText: 'Hủy',
            onOk: async () => {
                try {
                    await datasetService.deleteDataset(id);
                    notification.success({ message: 'Đã xóa dataset' });
                    fetchDatasets();
                } catch {
                    notification.error({ message: 'Không thể xóa dataset' });
                }
            }
        });
    };

    const getMenuProps = (dataset: Dataset): MenuProps => ({
        items: [
            ...(user?.role === 'admin' || user?.role === 'employee'
                ? [
                    {
                        key: 'share',
                        label: 'Chia sẻ',
                        onClick: () => {
                            setShareDatasetId(dataset.id);
                            setIsShareModalOpen(true);
                        }
                    }
                ]
                : []),
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
                <h1 className="text-2xl font-bold">Cơ sở tri thức</h1>
                <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => setIsCreateModalOpen(true)}
                    className="bg-[#0b1220] hover:bg-gray-800"
                >
                    Tạo dataset
                </Button>
            </div>

            <div className="mb-6">
                <Input
                    placeholder="Tìm dataset..."
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
                            Không tìm thấy dataset nào. Hãy tạo một dataset để bắt đầu.
                        </div>
                    )}
                </div>
            )}

            {/* Create Dataset Modal - Simple form with Name + Chatbot selection only */}
            <Modal
                title="Tạo dataset"
                open={isCreateModalOpen}
                onCancel={() => setIsCreateModalOpen(false)}
                onOk={handleCreateWrapper}
                okText="Tạo"
                width={500}
            >
                <Form
                    form={form}
                    layout="vertical"
                    initialValues={{ chatbot_ids: [] }}
                >
                    <Form.Item
                        name="name"
                        label="Tên dataset"
                        rules={[
                            { required: true, message: 'Vui lòng nhập tên dataset' },
                            { min: 3, message: 'Tên phải có ít nhất 3 ký tự' }
                        ]}
                    >
                        <Input
                            placeholder="Ví dụ: Dataset ngữ pháp tiếng Anh"
                            maxLength={200}
                        />
                    </Form.Item>

                    <Form.Item
                        name="chatbot_ids"
                        label="Gán cho chatbot (tùy chọn)"
                        tooltip="Chọn chatbot sẽ sử dụng dataset này. Cấu hình embedding và chunking được quản lý trong cài đặt chatbot."
                    >
                        <Select
                            mode="multiple"
                            placeholder="Chọn chatbot sẽ dùng dataset này"
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
                        Cấu hình embedding và chunking được quản lý tại <strong>Cài đặt chatbot</strong>.
                    </div>
                </Form>
            </Modal>

            {/* Rename Modal */}
            <Modal
                title="Đổi tên dataset"
                open={isRenameModalOpen}
                onCancel={() => setIsRenameModalOpen(false)}
                onOk={handleRenameWrapper}
                okText="Lưu"
            >
                <Form form={renameForm} layout="vertical">
                    <Form.Item name="name" label="Tên" rules={[{ required: true }]}>
                        <Input />
                    </Form.Item>
                </Form>
            </Modal>

            {shareDatasetId && (
                <ShareDatasetModal
                    datasetId={shareDatasetId}
                    open={isShareModalOpen}
                    onClose={() => {
                        setIsShareModalOpen(false);
                        setShareDatasetId(null);
                    }}
                    onSuccess={fetchDatasets}
                />
            )}
        </div>
    );
};

export default DatasetListPage;

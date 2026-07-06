'use client';

import React, { useState, useMemo, useRef } from 'react';
import { Table, Button, Input, Switch, Tooltip, Modal, Tag, notification } from 'antd';
import { EyeOutlined, DeleteOutlined, SearchOutlined, PlusOutlined, LoadingOutlined, DownloadOutlined } from '@ant-design/icons';
import { DatasetFile } from '@/core/entities/Dataset';
import datasetService from '@/services/datasetService';
import fileService from '@/services/fileService';
import dayjs from 'dayjs';

interface KnowledgeBaseTabProps {
    datasetId: string;
    files: DatasetFile[];
    fetchFiles: () => void;
}

interface ChunkItem {
    id: string;
    text: string;
    chunk_index: number;
}

const KnowledgeBaseTab: React.FC<KnowledgeBaseTabProps> = ({ datasetId, files, fetchFiles }) => {
    const [search, setSearch] = useState('');
    const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
    const [isAddFileModalOpen, setIsAddFileModalOpen] = useState(false);
    const [availableFiles, setAvailableFiles] = useState<any[]>([]); // Tất cả các file có sẵn trong thư viện
    const [selectedFilesToAdd, setSelectedFilesToAdd] = useState<string[]>([]);
    const [uploading, setUploading] = useState(false);

    // File Input Ref
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Xem trước Chunks
    const [chunkPreviewVisible, setChunkPreviewVisible] = useState(false);
    const [chunkItems, setChunkItems] = useState<ChunkItem[]>([]);
    const [previewTitle, setPreviewTitle] = useState('');

    const filteredFiles = useMemo(() => {
        if (!search) return files;
        return files.filter(f => (f.file_name || '').toLowerCase().includes(search.toLowerCase()));
    }, [files, search]);

    const handleToggle = async (file: DatasetFile, checked: boolean) => {
        console.log(`[KnowledgeBase] Toggling file ${file.id} to ${checked}`);
        try {
            await datasetService.toggleDatasetFile(datasetId, file.id, checked);
            console.log('[KnowledgeBase] Toggle success, refreshing...');
            fetchFiles();
            notification.success({ 
                message: `Đã ${checked ? 'kích hoạt' : 'vô hiệu hóa'} tài liệu thành công` 
            });
        } catch (error) {
            console.error('[KnowledgeBase] Toggle failed:', error);
            notification.error({ 
                message: 'Thay đổi trạng thái tài liệu thất bại. Vui lòng kiểm tra console.' 
            });
        }
    };

    const handleDelete = async (fileId: string) => {
        Modal.confirm({
            title: 'Xóa tài liệu',
            content: 'Bạn có chắc chắn muốn xóa tài liệu này khỏi cơ sở tri thức?',
            okText: 'Xóa',
            cancelText: 'Hủy',
            okType: 'danger',
            onOk: async () => {
                try {
                    await datasetService.removeFileFromDataset(datasetId, fileId);
                    fetchFiles();
                    notification.success({ message: 'Đã xóa tài liệu khỏi cơ sở tri thức' });
                } catch (error) {
                    console.error('Delete failed', error);
                    notification.error({ message: 'Xóa tài liệu thất bại' });
                }
            }
        });
    };

    const handleBulkDelete = () => {
        if (selectedRowKeys.length === 0) return;

        Modal.confirm({
            title: 'Xóa các tài liệu đã chọn',
            content: `Bạn có chắc chắn muốn xóa ${selectedRowKeys.length} tài liệu đã chọn khỏi cơ sở tri thức?`,
            okText: 'Xóa',
            cancelText: 'Hủy',
            okType: 'danger',
            onOk: async () => {
                try {
                    await Promise.all(
                        selectedRowKeys.map(key => datasetService.removeFileFromDataset(datasetId, key as string))
                    );
                    setSelectedRowKeys([]);
                    fetchFiles();
                    notification.success({ message: 'Đã xóa các tài liệu thành công' });
                } catch (error) {
                    console.error('Bulk delete failed', error);
                    notification.error({ message: 'Xóa một số tài liệu thất bại' });
                }
            }
        });
    };

    const handleAddFilesOpen = async () => {
        setIsAddFileModalOpen(true);
        try {
            const allFiles = await fileService.getFiles();
            console.log('[KnowledgeBase] All files from API:', allFiles);

            const existingIds = new Set(files.map(f => f.file_id));
            console.log('[KnowledgeBase] Existing file IDs in dataset:', Array.from(existingIds));

            const available = allFiles.filter((f: any) => !existingIds.has(f.id));
            console.log('[KnowledgeBase] Available files after filter:', available);

            setAvailableFiles(available);
        } catch (error) {
            console.error('Failed to load available files', error);
        }
    };

    const handleAddFilesSubmit = async () => {
        try {
            await datasetService.addFilesToDataset(datasetId, selectedFilesToAdd);
            setIsAddFileModalOpen(false);
            setSelectedFilesToAdd([]);
            fetchFiles();
            notification.success({ message: 'Đã thêm tài liệu vào cơ sở tri thức thành công' });
        } catch (error) {
            console.error('Add files failed', error);
            notification.error({ message: 'Thêm tài liệu thất bại' });
        }
    };

    const handleUploadClick = () => {
        if (fileInputRef.current) {
            fileInputRef.current.click();
        }
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFiles = e.target.files;
        if (!selectedFiles || selectedFiles.length === 0) return;

        setUploading(true);
        const uploadedFiles: any[] = [];
        const failedFiles: string[] = [];

        // Upload song song các file được chọn lên thư viện
        const uploadPromises = Array.from(selectedFiles).map(async (file) => {
            try {
                const uploaded = await fileService.uploadFile(file);
                uploadedFiles.push(uploaded);
            } catch (err) {
                console.error(`Upload failed for ${file.name}`, err);
                failedFiles.push(file.name);
            }
        });

        await Promise.all(uploadPromises);

        if (uploadedFiles.length > 0) {
            notification.success({ 
                message: `Tải lên thành công ${uploadedFiles.length} tệp tin`,
                description: `Tệp đã tải: ${uploadedFiles.map(f => f.name).join(', ')}`
            });
        }
        if (failedFiles.length > 0) {
            notification.error({ 
                message: `Tải lên thất bại ${failedFiles.length} tệp tin`,
                description: `Chi tiết tệp lỗi: ${failedFiles.join(', ')}`
            });
        }
        
        if (uploadedFiles.length === 0) {
            setUploading(false);
            e.target.value = '';
            return;
        }

        try {
            // Cập nhật lại danh sách files sẵn có để chọn thêm vào dataset
            const allFiles = await fileService.getFiles();
            console.log('[KnowledgeBase] Files after upload refresh:', allFiles);

            const existingIds = new Set(files.map(f => f.file_id || ''));
            const available = (allFiles || []).filter((f: any) => f && f.id && !existingIds.has(f.id));

            setAvailableFiles(available);

            // Tự động chọn (tick chọn) các file vừa tải lên thành công để người dùng chỉ cần nhấn Add Selected
            const newIds = uploadedFiles.filter(f => f && f.id).map(f => f.id);
            if (newIds.length > 0) {
                setSelectedFilesToAdd(prev => {
                    const uniqueSet = new Set([...prev, ...newIds]);
                    return Array.from(uniqueSet);
                });
            }
        } catch (err) {
            console.error('Refresh list failed', err);
            notification.warning({ message: 'Tải lên hoàn tất nhưng không thể làm mới danh sách tệp tin' });
        } finally {
            setUploading(false);
            e.target.value = ''; // Reset input để có thể chọn lại cùng file đó nếu cần
        }
    };

    const handleViewChunks = async (file: DatasetFile) => {
        try {
            console.log('[KnowledgeBase] Fetching chunks for file:', file.id);
            const chunks = await datasetService.getChunks(datasetId, file.id);
            console.log('[KnowledgeBase] Chunks received:', chunks.length);
            setChunkItems(chunks as any[]);
            setPreviewTitle(`Danh sách phân mảnh (Chunks) - ${file.file_name || 'Tài liệu'}`);
            setChunkPreviewVisible(true);
        } catch (error) {
            console.error('Get chunks failed', error);
            notification.error({ message: 'Tải danh sách phân mảnh thất bại' });
        }
    };

    const handlePreviewFile = (file: DatasetFile | { id: string }) => {
        const fileId = 'file_id' in file ? file.file_id : file.id;
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
        const previewUrl = `${baseUrl}/files/${fileId}/view`;
        window.open(previewUrl, '_blank');
    };

    const columns = [
        {
            title: 'Tên tài liệu',
            dataIndex: 'file_name',
            key: 'file_name',
            render: (text: string) => <span className="font-medium">{text || 'Không rõ'}</span>
        },
        {
            title: 'Ngày tải lên',
            dataIndex: 'created_at',
            key: 'created_at',
            render: (val: string) => dayjs(val).format('DD/MM/YYYY HH:mm')
        },
        {
            title: 'Kích thước',
            dataIndex: 'file_size',
            key: 'file_size',
            render: (size: number) => ((size || 0) / 1024).toFixed(2) + ' KB'
        },
        {
            title: 'Số Chunks',
            dataIndex: 'chunk_count',
            key: 'chunk_count',
        },
        {
            title: 'Kích hoạt',
            key: 'enable',
            render: (_: any, record: DatasetFile) => (
                <Switch
                    checked={!!record.is_enabled}
                    onChange={(checked) => handleToggle(record, checked)}
                    size="small"
                />
            )
        },
        {
            title: 'Trạng thái',
            dataIndex: 'status',
            key: 'status',
            render: (status: string) => {
                let color = 'orange';
                let text = 'ĐANG XỬ LÝ';
                if (status === 'done' || status === 'Ready') {
                    color = 'blue';
                    text = 'SẴN SÀNG';
                } else if (status === 'error') {
                    color = 'red';
                    text = 'LỖI';
                } else if (status === 'chunking') {
                    text = 'ĐANG PHÂN MẢNH';
                } else if (status === 'embedding') {
                    text = 'ĐANG NHÚNG VECTOR';
                }
                return (
                    <Tag color={color}>
                        {text}
                    </Tag>
                );
            }
        },
        {
            title: 'Hành động',
            key: 'action',
            render: (_: any, record: DatasetFile) => (
                <div className="flex gap-2">
                    <Tooltip title="Xem các phân mảnh">
                        <Button icon={<EyeOutlined />} size="small" onClick={() => handleViewChunks(record)} />
                    </Tooltip>
                    <Tooltip title="Xem trước/Tải xuống">
                        <Button
                            icon={<DownloadOutlined />}
                            size="small"
                            type="primary"
                            onClick={() => handlePreviewFile(record)}
                        />
                    </Tooltip>
                    <Tooltip title="Xóa">
                        <Button icon={<DeleteOutlined />} danger size="small" onClick={() => handleDelete(record.id)} />
                    </Tooltip>
                </div>
            )
        }
    ];

    const rowSelection = {
        selectedRowKeys,
        onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
    };

    return (
        <div className="flex-1 p-6 h-full flex flex-col">
            <div className="flex-1 bg-white rounded-lg shadow-sm p-6 flex flex-col overflow-hidden" style={{ maxHeight: 'calc(100vh - 200px)' }}>
                <div className="mb-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 flex-shrink-0">
                    <Input
                        placeholder="Tìm kiếm tài liệu..."
                        prefix={<SearchOutlined />}
                        className="max-w-xs"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                    <div className="flex gap-2">
                        {selectedRowKeys.length > 0 && (
                            <Button danger onClick={handleBulkDelete}>Xóa mục đã chọn ({selectedRowKeys.length})</Button>
                        )}
                        <Button type="primary" icon={<PlusOutlined />} onClick={handleAddFilesOpen} className="bg-black text-white">
                            Thêm tài liệu
                        </Button>
                    </div>
                </div>

                <div className="flex-1 overflow-auto">
                    <Table
                        dataSource={filteredFiles}
                        columns={columns}
                        rowKey="id"
                        rowSelection={rowSelection}
                        pagination={false}
                        scroll={{ y: 'calc(100vh - 400px)', x: 'max-content' }}
                        size="small"
                        className="border rounded-lg"
                    />
                </div>
            </div>

            {/* Modal Thêm tài liệu */}
            <Modal
                title="Chọn tài liệu muốn thêm vào Dataset"
                open={isAddFileModalOpen}
                onCancel={() => setIsAddFileModalOpen(false)}
                onOk={handleAddFilesSubmit}
                width={800}
                okText="Thêm tài liệu đã chọn"
                cancelText="Hủy"
                okButtonProps={{ disabled: selectedFilesToAdd.length === 0, className: 'bg-black' }}
            >
                <div className="flex justify-between items-center mb-4">
                    <p className="text-gray-500">Chọn tài liệu sẵn có trong thư viện hoặc tải lên tệp mới từ máy tính.</p>
                    <div>
                        <input
                            type="file"
                            ref={fileInputRef}
                            style={{ display: 'none' }}
                            onChange={handleFileChange}
                            multiple
                        />
                        <Button
                            icon={uploading ? <LoadingOutlined /> : <PlusOutlined />}
                            onClick={handleUploadClick}
                            disabled={uploading}
                            className="bg-black text-white hover:bg-gray-800"
                        >
                            {uploading ? 'Đang tải lên...' : 'Tải lên tệp mới'}
                        </Button>
                    </div>
                </div>

                <div className="max-h-[400px] overflow-y-auto">
                    <Table
                        dataSource={availableFiles}
                        rowKey="id"
                        pagination={false}
                        size="small"
                        rowSelection={{
                            selectedRowKeys: selectedFilesToAdd,
                            onChange: (keys) => setSelectedFilesToAdd(keys as string[])
                        }}
                        columns={[
                            {
                                title: 'Tên tệp',
                                dataIndex: 'name',
                                key: 'name'
                            },
                            {
                                title: 'Kích thước',
                                dataIndex: 'size',
                                key: 'size',
                                render: (s: number) => s ? ((s / 1024).toFixed(2) + ' KB') : 'Không rõ'
                            },
                            {
                                title: 'Ngày tải lên',
                                dataIndex: 'uploaded_at',
                                key: 'uploaded_at',
                                render: (d: string) => d ? dayjs(d).format('DD/MM/YYYY') : 'Không rõ'
                            },
                            {
                                title: 'Trạng thái',
                                dataIndex: 'status',
                                key: 'status',
                                render: (s: string) => {
                                    let text = s || 'Không rõ';
                                    if (s === 'done' || s === 'Ready') text = 'SẴN SÀNG';
                                    else if (s === 'error') text = 'LỖI';
                                    return <Tag>{text}</Tag>;
                                }
                            },
                            {
                                title: 'Hành động',
                                key: 'action',
                                width: 80,
                                render: (_, record: any) => (
                                    <Button
                                        type="text"
                                        icon={<EyeOutlined />}
                                        onClick={(e) => {
                                            e.stopPropagation(); // Ngăn chọn dòng
                                            handlePreviewFile(record);
                                        }}
                                        title="Xem trước tài liệu"
                                    />
                                )
                            }
                        ]}
                    />
                </div>
            </Modal>

            {/* Modal Xem trước phân mảnh (Chunks) */}
            <Modal
                title={previewTitle}
                open={chunkPreviewVisible}
                onCancel={() => setChunkPreviewVisible(false)}
                footer={null}
                width={700}
            >
                <div className="space-y-4 max-h-[60vh] overflow-y-auto">
                    {chunkItems.map((item, idx) => (
                        <div key={idx} className="border p-4 rounded bg-gray-50">
                            <p className="text-gray-800 text-sm whitespace-pre-wrap">{item.text}</p>
                            <div className="mt-2 text-xs text-gray-500">Phân mảnh số {item.chunk_index}</div>
                        </div>
                    ))}
                    {chunkItems.length === 0 && <p className="text-gray-500">Không tìm thấy phân mảnh nào.</p>}
                </div>
            </Modal>
        </div>
    );
};

export default KnowledgeBaseTab;

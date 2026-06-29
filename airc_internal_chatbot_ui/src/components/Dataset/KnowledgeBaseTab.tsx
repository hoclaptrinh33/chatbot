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
    const [availableFiles, setAvailableFiles] = useState<any[]>([]); // All files for selection
    const [selectedFilesToAdd, setSelectedFilesToAdd] = useState<string[]>([]);
    const [uploading, setUploading] = useState(false);

    // File Input Ref
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Chunk Preview
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

            // Optimistic update should be done via refetch or parent update if local state not available
            // Since we receive 'files' as props, we trigger fetchFiles()
            // But to make it instant, we might want to update a local copy if we had one.
            // For now, rely on fetchFiles but log success.
            console.log('[KnowledgeBase] Toggle success, refreshing...');
            fetchFiles();
            notification.success({ message: `File ${checked ? 'enabled' : 'disabled'}` });
        } catch (error) {
            console.error('[KnowledgeBase] Toggle failed:', error);
            notification.error({ message: 'Toggle failed. Check console.' });
        }
    };

    const handleDelete = async (fileId: string) => {
        Modal.confirm({
            title: 'Remove File',
            content: 'Are you sure you want to remove this file from the dataset?',
            okType: 'danger',
            onOk: async () => {
                try {
                    await datasetService.removeFileFromDataset(datasetId, fileId);
                    fetchFiles();
                } catch (error) {
                    console.error('Delete failed', error);
                }
            }
        });
    };

    const handleBulkDelete = () => {
        if (selectedRowKeys.length === 0) return;

        Modal.confirm({
            title: 'Remove Selected Files',
            content: `Are you sure you want to remove ${selectedRowKeys.length} files from the dataset?`,
            okType: 'danger',
            onOk: async () => {
                try {
                    await Promise.all(
                        selectedRowKeys.map(key => datasetService.removeFileFromDataset(datasetId, key as string))
                    );
                    setSelectedRowKeys([]);
                    fetchFiles();
                    notification.success({ message: 'Files removed successfully' });
                } catch (error) {
                    console.error('Bulk delete failed', error);
                    notification.error({ message: 'Failed to remove some files' });
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
        } catch (error) {
            console.error('Add files failed', error);
        }
    };

    const handleUploadClick = () => {
        if (fileInputRef.current) {
            fileInputRef.current.click();
        }
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploading(true);
        let uploaded = null;

        try {
            // 1. Upload file
            uploaded = await fileService.uploadFile(file);
            notification.success({ message: 'File uploaded successfully' });
        } catch (err) {
            console.error('Upload failed', err);
            notification.error({ message: 'Upload failed' });
            setUploading(false);
            e.target.value = '';
            return;
        }

        try {
            // 2. Refresh list and auto-select
            const allFiles = await fileService.getFiles();
            console.log('[KnowledgeBase] Files after upload refresh:', allFiles);
            console.log('[KnowledgeBase] Uploaded file:', uploaded);

            // Safe filter
            const existingIds = new Set(files.map(f => f.file_id || ''));
            console.log('[KnowledgeBase] Existing IDs after upload:', Array.from(existingIds));

            const available = (allFiles || []).filter((f: any) => f && f.id && !existingIds.has(f.id));
            console.log('[KnowledgeBase] Available files after upload filter:', available);

            setAvailableFiles(available);

            // Auto select the new file
            if (uploaded && uploaded.id) {
                console.log('[KnowledgeBase] Auto-selecting uploaded file:', uploaded.id);
                setSelectedFilesToAdd(prev => [...prev, uploaded!.id]);
            }
        } catch (err) {
            console.error('Refresh list failed', err);
            // Non-critical error
            notification.warning({ message: 'File uploaded but list refresh failed' });
        } finally {
            setUploading(false);
            e.target.value = ''; // Reset input
        }
    };

    const handleViewChunks = async (file: DatasetFile) => {
        try {
            console.log('[KnowledgeBase] Fetching chunks for file:', file.id);
            const chunks = await datasetService.getChunks(datasetId, file.id);
            console.log('[KnowledgeBase] Chunks received:', chunks.length);
            setChunkItems(chunks as any[]);
            setPreviewTitle(`Chunks - ${file.file_name || 'File'}`);
            setChunkPreviewVisible(true);
            console.log('[KnowledgeBase] Chunk modal should now be visible');
        } catch (error) {
            console.error('Get chunks failed', error);
            notification.error({ message: 'Failed to load chunks' });
        }
    };

    const handlePreviewFile = (file: DatasetFile | { id: string }) => {
        // Open file preview in new tab using API URL
        // Support both DatasetFile (file_id) and File (id) objects
        const fileId = 'file_id' in file ? file.file_id : file.id;
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
        const previewUrl = `${baseUrl}/files/${fileId}/view`;
        window.open(previewUrl, '_blank');
    };

    const columns = [
        {
            title: 'Name',
            dataIndex: 'file_name',
            key: 'file_name',
            render: (text: string) => <span className="font-medium">{text || 'Unknown'}</span>
        },
        {
            title: 'Upload Date',
            dataIndex: 'created_at',
            key: 'created_at',
            render: (val: string) => dayjs(val).format('DD/MM/YYYY HH:mm')
        },
        {
            title: 'Size',
            dataIndex: 'file_size',
            key: 'file_size',
            render: (size: number) => ((size || 0) / 1024).toFixed(2) + ' KB'
        },
        {
            title: 'Chunks',
            dataIndex: 'chunk_count',
            key: 'chunk_count',
        },
        {
            title: 'Enable',
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
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            render: (status: string) => (
                <Tag color={status === 'done' || status === 'Ready' ? 'blue' : status === 'error' ? 'red' : 'orange'}>
                    {status ? status.toUpperCase() : 'UNKNOWN'}
                </Tag>
            )
        },
        {
            title: 'Action',
            key: 'action',
            render: (_: any, record: DatasetFile) => (
                <div className="flex gap-2">
                    <Tooltip title="View Chunks">
                        <Button icon={<EyeOutlined />} size="small" onClick={() => handleViewChunks(record)} />
                    </Tooltip>
                    <Tooltip title="Preview/Download File">
                        <Button
                            icon={<DownloadOutlined />}
                            size="small"
                            type="primary"
                            onClick={() => handlePreviewFile(record)}
                        />
                    </Tooltip>
                    <Tooltip title="Delete">
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
                        placeholder="Search files..."
                        prefix={<SearchOutlined />}
                        className="max-w-xs"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                    <div className="flex gap-2">
                        {selectedRowKeys.length > 0 && (
                            <Button danger onClick={handleBulkDelete}>Delete Selected ({selectedRowKeys.length})</Button>
                        )}
                        <Button type="primary" icon={<PlusOutlined />} onClick={handleAddFilesOpen} className="bg-black text-white">
                            Add File
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

            {/* Add File Modal */}
            <Modal
                title="Select Files to Add"
                open={isAddFileModalOpen}
                onCancel={() => setIsAddFileModalOpen(false)}
                onOk={handleAddFilesSubmit}
                width={800}
                okText="Add Selected"
                okButtonProps={{ disabled: selectedFilesToAdd.length === 0, className: 'bg-black' }}
            >
                <div className="flex justify-between items-center mb-4">
                    <p className="text-gray-500">Select files from the library or upload new ones.</p>
                    <div>
                        <input
                            type="file"
                            ref={fileInputRef}
                            style={{ display: 'none' }}
                            onChange={handleFileChange}
                        />
                        <Button
                            icon={uploading ? <LoadingOutlined /> : <PlusOutlined />}
                            onClick={handleUploadClick}
                            disabled={uploading}
                            className="bg-black text-white hover:bg-gray-800"
                        >
                            {uploading ? 'Uploading...' : 'Upload New File'}
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
                                title: 'Name',
                                dataIndex: 'name',
                                key: 'name'
                            },
                            {
                                title: 'Size',
                                dataIndex: 'size',
                                key: 'size',
                                render: (s: number) => s ? ((s / 1024).toFixed(2) + ' KB') : 'N/A'
                            },
                            {
                                title: 'Date',
                                dataIndex: 'uploaded_at',
                                key: 'uploaded_at',
                                render: (d: string) => d ? dayjs(d).format('DD/MM/YYYY') : 'N/A'
                            },
                            {
                                title: 'Status',
                                dataIndex: 'status',
                                key: 'status',
                                render: (s: string) => <Tag>{s || 'Unknown'}</Tag>
                            },
                            {
                                title: 'Action',
                                key: 'action',
                                width: 80,
                                render: (_, record: any) => (
                                    <Button
                                        type="text"
                                        icon={<EyeOutlined />}
                                        onClick={(e) => {
                                            e.stopPropagation(); // Prevent row selection
                                            handlePreviewFile(record);
                                        }}
                                        title="Preview File"
                                    />
                                )
                            }
                        ]}
                    />
                </div>
            </Modal>

            {/* Chunk Preview Modal */}
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
                            <div className="mt-2 text-xs text-gray-500">Chunk {item.chunk_index}</div>
                        </div>
                    ))}
                    {chunkItems.length === 0 && <p>No chunks found.</p>}
                </div>
            </Modal>
        </div>
    );
};

export default KnowledgeBaseTab;

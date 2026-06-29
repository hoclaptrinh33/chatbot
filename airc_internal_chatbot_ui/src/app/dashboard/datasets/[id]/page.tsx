'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import datasetService, { Dataset, DatasetFile } from '@/services/datasetService';
import DatasetSidebar from '@/components/Dataset/DatasetSidebar';
import KnowledgeBaseTab from '@/components/Dataset/KnowledgeBaseTab';
import { notification, Button } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';

const DatasetDetailPage = () => {
    const params = useParams();
    const router = useRouter();
    const id = params?.id as string;

    const [dataset, setDataset] = useState<Dataset | null>(null);
    const [files, setFiles] = useState<DatasetFile[]>([]);
    const [activeTab, setActiveTab] = useState<'dataset' | 'configuration'>('dataset');
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        if (!id) return;
        try {
            const [ds, fs] = await Promise.all([
                datasetService.getDataset(id),
                datasetService.getDatasetFiles(id)
            ]);
            setDataset(ds);
            setFiles(fs);
        } catch (error) {
            console.error('Fetch detail failed', error);
            notification.error({ message: 'Failed to load dataset details' });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();

        // Poll if any file is processing
        const pollInterval = setInterval(async () => {
            try {
                const fs = await datasetService.getDatasetFiles(id);
                // Only update if there are files still processing or status changed
                const hasProcessing = fs.some(f => f.status !== 'done' && f.status !== 'error');
                if (hasProcessing || fs.length !== files.length) {
                    setFiles(fs);
                }
            } catch (error) {
                console.error('Poll failed:', error);
            }
        }, 3000);

        return () => clearInterval(pollInterval);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [id]); // Only re-run when ID changes

    const handleUpdateDataset = (updated: Dataset) => {
        setDataset(updated);
    };

    const formatBytes = (bytes = 0) => {
        if (bytes === 0) return "0 B";
        const k = 1024;
        const sizes = ["B", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
    };

    if (loading) return <div className="p-10">Loading...</div>;
    if (!dataset) return <div className="p-10">Dataset not found</div>;

    const totalSize = formatBytes(files.reduce((acc, f) => acc + (f.file_size || 0), 0));
    const totalChunks = files.reduce((acc, f) => acc + (f.chunk_count || 0), 0);

    return (
        <div className="h-[calc(100vh-64px)] overflow-hidden flex flex-col">
            {/* Minimal Header for Back button */}
            <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center">
                <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => router.push('/dashboard/datasets')}>
                    Back to Datasets
                </Button>
            </div>

            <div className="flex-1 flex overflow-hidden">
                <DatasetSidebar
                    dataset={dataset}
                    activeTab={activeTab}
                    setActiveTab={setActiveTab}
                    fileCount={files.length}
                    chunkCount={totalChunks}
                    totalSize={totalSize}
                />

                <div className="flex-1 bg-gray-50 overflow-hidden flex flex-col">
                    <KnowledgeBaseTab
                        datasetId={id}
                        files={files}
                        fetchFiles={fetchData}
                    />
                </div>
            </div>
        </div>
    );
};

export default DatasetDetailPage;

'use client';

import React from 'react';
import { Dataset } from '@/services/datasetService';
import { DatabaseOutlined } from '@ant-design/icons';

interface DatasetSidebarProps {
    dataset: Dataset;
    activeTab: 'dataset' | 'configuration';
    setActiveTab: (tab: 'dataset' | 'configuration') => void;
    fileCount: number;
    chunkCount: number;
    totalSize: string;
}

const DatasetSidebar: React.FC<DatasetSidebarProps> = ({
    dataset,
    activeTab,
    setActiveTab,
    fileCount,
    chunkCount,
    totalSize
}) => {
    return (
        <div className="w-64 flex-shrink-0 bg-white border-r border-gray-200 p-6 h-full">
            <div className="mb-8">
                <div className="flex items-start mb-4">
                    <div className="w-12 h-12 bg-green-500/10 rounded-lg flex items-center justify-center text-green-600 font-bold text-lg leading-none shrink-0 border border-green-200">
                        {dataset.name.charAt(0).toUpperCase()}
                    </div>
                    <h2 className="ml-3 text-lg font-semibold text-gray-900 leading-snug break-words flex-1">
                        {dataset.name}
                    </h2>
                </div>
                <div className="space-y-2 text-sm text-gray-500 pl-1">
                    <div>{fileCount} files</div>
                    <div>{chunkCount} chunks</div>
                    <div>{totalSize}</div>
                </div>
            </div>

            <div className="space-y-1">
                <button
                    onClick={() => setActiveTab('dataset')}
                    className={`w-full text-left px-4 py-3 rounded-lg text-sm font-medium transition-colors flex items-center gap-3 ${activeTab === 'dataset' ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50'
                        }`}
                >
                    <DatabaseOutlined />
                    Knowledge base
                </button>
            </div>
        </div>
    );
};

export default DatasetSidebar;

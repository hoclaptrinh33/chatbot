'use client';

import React, { useState } from 'react';
import { Card, List, Checkbox, Spin, Input } from 'antd';
import { DatabaseOutlined, SearchOutlined } from '@ant-design/icons';
import useDatasetStore from '@/stores/datasetStore';
import useChatStore from '@/stores/chatStore';

interface ChatSidebarProps {
    className?: string;
}

/**
 * Component Sidebar chon Datasets
 */
export default function ChatSidebar({ className }: ChatSidebarProps) {
    const { datasets, loading } = useDatasetStore();
    const { datasetIds, selectDatasets } = useChatStore();
    const [searchTerm, setSearchTerm] = useState('');

    const handleCheckboxChange = (datasetId: string, checked: boolean) => {
        const newSelected = checked
            ? [...datasetIds, datasetId]
            : datasetIds.filter(id => id !== datasetId);
        selectDatasets(newSelected);
    };

    const filteredDatasets = datasets.filter(ds =>
        ds.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <Card
            title={
                <div className="flex items-center gap-2">
                    <DatabaseOutlined className="text-red-700" />
                    <span>Chon Datasets</span>
                </div>
            }
            className={`border-0 shadow-none bg-transparent ${className || ''}`}
            bodyStyle={{ padding: '12px 0' }}
            headStyle={{ borderBottom: '1px solid #f0f0f0', padding: '0 12px' }}
        >
            <div className="px-3 mb-4">
                <Input
                    placeholder="Tim datasets..."
                    prefix={<SearchOutlined className="text-gray-400" />}
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                    size="small"
                />
            </div>

            {loading ? (
                <div className="flex justify-center py-4">
                    <Spin size="small" />
                </div>
            ) : (
                <div className="overflow-y-auto max-h-[calc(100vh-250px)] px-2">
                    <List
                        dataSource={filteredDatasets}
                        renderItem={item => (
                            <List.Item className="!py-2 !px-2 hover:bg-gray-50 rounded cursor-pointer">
                                <Checkbox
                                    checked={datasetIds.includes(item.id)}
                                    onChange={e => handleCheckboxChange(item.id, e.target.checked)}
                                    className="w-full flex items-center"
                                >
                                    <div className="ml-2 overflow-hidden">
                                        <div className="font-medium truncate text-sm" title={item.name}>
                                            {item.name}
                                        </div>
                                        <div className="text-xs text-gray-400 truncate">
                                            {item.description || 'No description'}
                                        </div>
                                    </div>
                                </Checkbox>
                            </List.Item>
                        )}
                        locale={{ emptyText: 'Khong co datasets' }}
                    />
                </div>
            )}
        </Card>
    );
}

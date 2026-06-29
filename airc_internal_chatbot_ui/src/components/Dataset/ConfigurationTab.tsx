'use client';

import React, { useEffect } from 'react';
import { Form, Input, Select, Button, notification } from 'antd';
import { Dataset } from '@/services/datasetService';
import datasetService from '@/services/datasetService';

interface ConfigurationTabProps {
    dataset: Dataset;
    onUpdate: (updatedDataset: Dataset) => void;
}

const ConfigurationTab: React.FC<ConfigurationTabProps> = ({ dataset, onUpdate }) => {
    const [form] = Form.useForm();

    useEffect(() => {
        // Dataset configuration has been moved to system-level defaults
        // This form is now legacy and doesn't modify anything meaningful
        form.setFieldsValue({
            chunk_size: 512,
            chunk_overlap: 50,
            embedding_model: 'vietnamese-sbert',
            reranker: 'semantic'
        });
    }, [form]);

    const handleSave = async (values: any) => {
        try {
            // Note: Dataset configuration has been moved to system-level defaults
            // This component is legacy and the config settings no longer apply per-dataset
            const updated = await datasetService.updateDataset(dataset.id, {
                name: dataset.name,
                visibility: 'private'
            });

            onUpdate(updated);
            notification.success({ message: 'Dataset updated (config is now system-level)' });
        } catch (error) {
            console.error('Save config failed', error);
            notification.error({ message: 'Failed to update dataset' });
        }
    };

    return (
        <div className="flex-1 p-6 overflow-y-auto">
            <h1 className="text-2xl font-bold text-gray-900 mb-6">Configuration</h1>
            <div className="bg-white rounded-lg border border-gray-200 p-6 max-w-2xl">
                <Form form={form} layout="vertical" onFinish={handleSave}>
                    <div className="grid grid-cols-2 gap-6">
                        <Form.Item name="chunk_size" label="Chunk Size">
                            <Input type="number" />
                        </Form.Item>
                        <Form.Item name="chunk_overlap" label="Chunk Overlap">
                            <Input type="number" />
                        </Form.Item>
                    </div>

                    <Form.Item name="embedding_model" label="Embedding Model">
                        <Select>
                            <Select.Option value="vietnamese-sbert">Vietnamese SBERT</Select.Option>
                            <Select.Option value="multilingual-e5">Multilingual E5</Select.Option>
                            <Select.Option value="bert-base">BERT Base</Select.Option>
                        </Select>
                    </Form.Item>

                    <Form.Item name="reranker" label="Reranker">
                        <Select>
                            <Select.Option value="fixed">Fixed Size</Select.Option>
                            <Select.Option value="semantic">Semantic</Select.Option>
                            <Select.Option value="hybrid">Hybrid</Select.Option>
                        </Select>
                    </Form.Item>

                    <Form.Item>
                        <div className="flex justify-end">
                            <Button type="primary" htmlType="submit" className="bg-[#0b1220]">
                                Save Changes
                            </Button>
                        </div>
                    </Form.Item>
                </Form>
            </div>
        </div>
    );
};

export default ConfigurationTab;

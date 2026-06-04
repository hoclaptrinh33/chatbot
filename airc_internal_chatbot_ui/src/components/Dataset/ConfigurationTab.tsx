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
        // Cấu hình dataset đã được chuyển sang mặc định cấp hệ thống
        // Form này là thành phần cũ và không còn thay đổi giá trị có ý nghĩa
        form.setFieldsValue({
            chunk_size: 512,
            chunk_overlap: 50,
            embedding_model: 'vietnamese-sbert',
            reranker: 'semantic'
        });
    }, [form]);

    const handleSave = async (values: any) => {
        try {
            // Lưu ý: cấu hình dataset đã được chuyển sang mặc định cấp hệ thống
            // Component này là cũ và cấu hình không còn áp dụng theo từng dataset
            const updated = await datasetService.updateDataset(dataset.id, {
                name: dataset.name,
                visibility: 'private'
            });

            onUpdate(updated);
            notification.success({ message: 'Đã cập nhật dataset (cấu hình hiện ở cấp hệ thống)' });
        } catch (error) {
            console.error('Save config failed', error);
            notification.error({ message: 'Không thể cập nhật dataset' });
        }
    };

    return (
        <div className="flex-1 p-6 overflow-y-auto">
            <h1 className="text-2xl font-bold text-gray-900 mb-6">Cấu hình</h1>
            <div className="bg-white rounded-lg border border-gray-200 p-6 max-w-2xl">
                <Form form={form} layout="vertical" onFinish={handleSave}>
                    <div className="grid grid-cols-2 gap-6">
                        <Form.Item name="chunk_size" label="Kích thước chunk">
                            <Input type="number" />
                        </Form.Item>
                        <Form.Item name="chunk_overlap" label="Độ chồng lấn chunk">
                            <Input type="number" />
                        </Form.Item>
                    </div>

                    <Form.Item name="embedding_model" label="Mô hình embedding">
                        <Select>
                            <Select.Option value="vietnamese-sbert">Vietnamese SBERT</Select.Option>
                            <Select.Option value="multilingual-e5">Multilingual E5</Select.Option>
                            <Select.Option value="bert-base">BERT Base</Select.Option>
                        </Select>
                    </Form.Item>

                    <Form.Item name="reranker" label="Reranker">
                        <Select>
                            <Select.Option value="fixed">Kích thước cố định</Select.Option>
                            <Select.Option value="semantic">Ngữ nghĩa</Select.Option>
                            <Select.Option value="hybrid">Kết hợp</Select.Option>
                        </Select>
                    </Form.Item>

                    <Form.Item>
                        <div className="flex justify-end">
                            <Button type="primary" htmlType="submit" className="bg-[#0b1220]">
                                Lưu thay đổi
                            </Button>
                        </div>
                    </Form.Item>
                </Form>
            </div>
        </div>
    );
};

export default ConfigurationTab;

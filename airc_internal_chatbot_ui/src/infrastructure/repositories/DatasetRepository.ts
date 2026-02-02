import { IDatasetRepository } from '@/core/repositories/IDatasetRepository';
import { Dataset, DatasetFile } from '@/core/entities/Dataset';
import { coreClient } from '@/infrastructure/http/core.client';

export const datasetRepository: IDatasetRepository = {
    async getDatasets(): Promise<Dataset[]> {
        const response = await coreClient.get<Dataset[]>('/datasets');
        return response.data;
    },

    async getDataset(id: string): Promise<Dataset> {
        const response = await coreClient.get<Dataset>(`/datasets/${id}`);
        return response.data;
    },

    async createDataset(name: string, chatbot_ids?: string[]): Promise<Dataset> {
        const payload: any = { name };
        if (chatbot_ids && chatbot_ids.length > 0) {
            payload.chatbot_ids = chatbot_ids;  // ✅ Include chatbot_ids if provided
        }
        const response = await coreClient.post<Dataset>('/datasets', payload);
        return response.data;
    },

    async updateDataset(id: string, payload: { name: string; visibility?: string }): Promise<Dataset> {
        const response = await coreClient.patch<Dataset>(`/datasets/${id}`, payload);
        return response.data;
    },

    async deleteDataset(id: string): Promise<void> {
        await coreClient.delete(`/datasets/${id}`);
    },

    async shareDataset(id: string, payload: { all_students?: boolean; student_ids?: string[] }): Promise<Record<string, unknown>> {
        const response = await coreClient.post(`/datasets/${id}/share`, payload);
        return response.data;
    },

    async addFilesToDataset(datasetId: string, fileIds: string[]): Promise<Record<string, unknown>> {
        const response = await coreClient.post(`/datasets/${datasetId}/files`, { file_ids: fileIds });
        return response.data;
    },

    async getDatasetFiles(datasetId: string): Promise<DatasetFile[]> {
        const response = await coreClient.get<DatasetFile[]>(`/datasets/${datasetId}/files`);
        return response.data;
    },

    async deleteDatasetFile(datasetId: string, fileId: string): Promise<void> {
        await coreClient.delete(`/datasets/${datasetId}/files/${fileId}`);
    },

    async toggleDatasetFile(datasetId: string, fileId: string, isEnabled: boolean): Promise<boolean> {
        await coreClient.put(`/datasets/${datasetId}/files/${fileId}/toggle`, { enabled: isEnabled });
        return true;
    },

    async getChunks(datasetId: string, datasetFileId: string): Promise<any[]> {
        const response = await coreClient.get(`/datasets/${datasetId}/files/${datasetFileId}/chunks`);
        return response.data;
    },
};

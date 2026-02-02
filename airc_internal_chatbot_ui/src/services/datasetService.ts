import { datasetRepository } from '@/infrastructure/repositories/DatasetRepository';
import { Dataset, DatasetFile } from '@/core/entities/Dataset';

// DatasetConfig removed

export type { Dataset, DatasetFile };

export interface DatasetCreatePayload {
    name: string;
    description?: string;
    visibility?: 'private' | 'shared' | 'public';
    chatbot_ids?: string[];  // ✅ Add chatbot_ids field
}

const datasetService = {
    /**
     * Get list of datasets
     */
    getDatasets: async (): Promise<Dataset[]> => {
        return await datasetRepository.getDatasets();
    },

    /**
     * Get dataset details
     */
    getDataset: async (id: string): Promise<Dataset> => {
        return await datasetRepository.getDataset(id);
    },

    /**
     * Create new dataset
     */
    createDataset: async (payload: DatasetCreatePayload): Promise<Dataset> => {
        // ✅ Pass chatbot_ids as optional second parameter
        return await datasetRepository.createDataset(payload.name, payload.chatbot_ids);
    },

    /**
     * Update dataset (name only)
     */
    updateDataset: async (id: string, payload: { name: string; visibility?: string }): Promise<Dataset> => {
        return await datasetRepository.updateDataset(id, payload);
    },

    /**
     * Delete dataset
     */
    deleteDataset: async (id: string): Promise<boolean> => {
        await datasetRepository.deleteDataset(id);
        return true;
    },

    /**
     * Get dataset files
     */
    getDatasetFiles: async (datasetId: string): Promise<DatasetFile[]> => {
        return await datasetRepository.getDatasetFiles(datasetId);
    },

    /**
     * Add files to dataset
     */
    addFilesToDataset: async (datasetId: string, fileIds: string[]): Promise<Record<string, unknown>> => {
        return await datasetRepository.addFilesToDataset(datasetId, fileIds);
    },

    /**
     * Remove file from dataset
     */
    removeFileFromDataset: async (datasetId: string, datasetFileId: string): Promise<boolean> => {
        await datasetRepository.deleteDatasetFile(datasetId, datasetFileId);
        return true;
    },

    /**
     * Toggle file enable/disable status
     */
    toggleDatasetFile: async (datasetId: string, datasetFileId: string, isEnabled: boolean): Promise<boolean> => {
        return await datasetRepository.toggleDatasetFile(datasetId, datasetFileId, isEnabled);
    },

    /**
     * Share dataset with students
     */
    shareDataset: async (datasetId: string, payload: { all_students?: boolean; student_ids?: string[] }): Promise<Record<string, unknown>> => {
        return await datasetRepository.shareDataset(datasetId, payload);
    },

    /**
     * Get chunks of dataset file
     */
    getChunks: async (datasetId: string, datasetFileId: string): Promise<Record<string, unknown>[]> => {
        return await datasetRepository.getChunks(datasetId, datasetFileId);
    }
};

export default datasetService;

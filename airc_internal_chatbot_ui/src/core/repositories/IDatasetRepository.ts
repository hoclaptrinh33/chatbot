import { Dataset, DatasetFile } from '@/core/entities/Dataset';

export interface IDatasetRepository {
    getDatasets(): Promise<Dataset[]>;
    getDataset(id: string): Promise<Dataset>;
    createDataset(name: string, chatbot_ids?: string[]): Promise<Dataset>;
    updateDataset(id: string, payload: { name: string; visibility?: string }): Promise<Dataset>;
    deleteDataset(id: string): Promise<void>;
    shareDataset(id: string, payload: { all_students?: boolean; student_ids?: string[] }): Promise<Record<string, unknown>>;

    // Files
    addFilesToDataset(datasetId: string, fileIds: string[]): Promise<Record<string, unknown>>;
    getDatasetFiles(datasetId: string): Promise<DatasetFile[]>;
    deleteDatasetFile(datasetId: string, fileId: string): Promise<void>;
    toggleDatasetFile(datasetId: string, fileId: string, isEnabled: boolean): Promise<boolean>;
    getChunks(datasetId: string, datasetFileId: string): Promise<any[]>;
}

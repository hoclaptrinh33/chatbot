import { IFileRepository } from '@/core/repositories/IFileRepository';
import { FileUploadResponse, FileInfo } from '@/services/fileService';
import { coreClient } from '@/infrastructure/http/core.client';

export const fileRepository: IFileRepository = {
    async uploadFile(file: File): Promise<FileUploadResponse> {
        const formData = new FormData();
        formData.append('file', file);

        const response = await coreClient.post<FileUploadResponse>('/files/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    async getFiles(): Promise<FileInfo[]> {
        const response = await coreClient.get<FileInfo[]>('/files/');
        return response.data;
    },

    async getFile(id: string): Promise<FileInfo> {
        const response = await coreClient.get<FileInfo>(`/files/${id}`);
        return response.data;
    },
};

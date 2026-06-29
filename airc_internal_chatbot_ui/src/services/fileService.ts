import { fileRepository } from '@/infrastructure/repositories/FileRepository';

// URL API Backend (Core Service) - NEXT_PUBLIC_API_URL = /api/v1
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface FileUploadResponse {
    id: string;
    name: string;
    size: number;
    mime_type: string;
    status: string;
    uploaded_at: string;
}

export interface FileInfo {
    id: string;
    name: string;
    size: number;
    mime_type: string;
    status: string;
    uploaded_at: string;
    processed_at?: string;
    error?: string;
}

/**
 * Service xử lý File Upload và Management
 */
const fileService = {
    /**
     * Upload file lên server
     */
    uploadFile: async (file: File): Promise<FileUploadResponse> => {
        return await fileRepository.uploadFile(file);
    },

    /**
     * Lấy danh sách files
     */
    getFiles: async (): Promise<FileInfo[]> => {
        try {
            const response = await fileRepository.getFiles();
            return Array.isArray(response) ? response : [];
        } catch (error) {
            console.error('getFiles error:', error);
            return [];
        }
    },

    /**
     * Lấy thông tin file
     */
    getFile: async (id: string): Promise<FileInfo> => {
        return await fileRepository.getFile(id);
    },

    /**
     * Get View File URL
     */
    viewFileUrl: (id: string): string => {
        return `${API_URL}/api/v1/files/${id}/view`;
    }
};

export default fileService;

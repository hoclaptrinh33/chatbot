import { FileUploadResponse, FileInfo } from '@/services/fileService';

export interface IFileRepository {
    uploadFile(file: File): Promise<FileUploadResponse>;
    getFiles(): Promise<FileInfo[]>;
    getFile(id: string): Promise<FileInfo>;
}

/**
 * Dataset Entity - Domain Model
 * Align with Backend DatasetResponse
 */

export interface Dataset {
    id: string;
    name: string;
    description?: string;
    created_at: string;
    visibility?: string; // private, shared, etc.
    status?: string;
}

// Enum for Dataset File Status (aligned with Backend)
export enum DatasetFileStatus {
    PENDING = 'pending',
    CHUNKING = 'chunking',
    EMBEDDING = 'embedding',
    DONE = 'done',
    ERROR = 'error'
}

export interface DatasetFile {
    id: string;
    dataset_id: string;
    file_id: string;
    status: DatasetFileStatus | string;
    chunk_count: number;
    created_at: string;
    file_name?: string; // Often joined from File entity
    file_size?: number;
    is_enabled?: boolean;
}

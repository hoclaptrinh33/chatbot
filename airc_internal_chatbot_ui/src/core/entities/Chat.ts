/**
 * Chat Entity - Domain Model
 * Align with Backend ChatResponse
 */

export interface ChatMessage {
    id?: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp?: number | string;
    created_at?: string; // From backend
    session_id?: string;
}

export interface SearchResult {
    vector_id: number;
    score: number;
    text: string;
    file_id: string;
    dataset_file_id: string;
    chunk_index: number;
    cite: string;
}

export interface DatasetSearchResult {
    dataset_id: string;
    dataset_name?: string;
    results: SearchResult[];
}

export interface ChatResponse {
    status: string;
    question: string;
    answer: string;
    sources: DatasetSearchResult[];
    errors?: ChatError[];
    debug?: {
        total_time_ms: number;
        embedding_time_ms: number;
        retrieval_time_ms: number;
        rerank_time_ms: number;
        llm_time_ms: number;
        cache_hit: boolean;
        chunks_found: number;
        chunks_after_rerank: number;
        avg_similarity_score: number;
        top_similarity_score: number;
        datasets_searched: number;
        model_used: string | null;
        reranker_used: string | null;
        no_context: boolean;
    };
}

export interface ChatError {
    code?: string;
    message: string;
    details?: string;
}

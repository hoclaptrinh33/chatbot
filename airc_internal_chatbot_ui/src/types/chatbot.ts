/**
 * Chatbot Configuration - RAG Pipeline Settings
 * Pipeline: Query → Embedding → Retrieval → Reranking → Generation
 * 
 * NOTE: All fields optional with defaults in backend ChatbotConfigModel
 */
export interface ChatbotConfig {
    // ═══════════════════════════════════════════════════════════════
    // 📊 EMBEDDING SETTINGS (fixed: vietnamese-sbert)
    // ═══════════════════════════════════════════════════════════════
    embedding_model?: string;

    // ═══════════════════════════════════════════════════════════════
    // 🔍 RETRIEVAL SETTINGS
    // ═══════════════════════════════════════════════════════════════
    search_mode?: 'hybrid' | 'vector' | 'keyword';
    top_k?: number;
    similarity_threshold?: number;

    // ═══════════════════════════════════════════════════════════════
    // 📈 RERANKING SETTINGS
    // ═══════════════════════════════════════════════════════════════
    reranker?: string;
    rerank_top_n?: number;

    // ═══════════════════════════════════════════════════════════════
    // 🤖 LLM GENERATION SETTINGS
    // ═══════════════════════════════════════════════════════════════
    model?: string;
    api_key?: string;
    temperature?: number;
    max_tokens?: number;

    // ═══════════════════════════════════════════════════════════════
    // 📝 PROMPT SETTINGS
    // ═══════════════════════════════════════════════════════════════
    system_prompt?: string;

    // ═══════════════════════════════════════════════════════════════
    // ⚠️ NO CONTEXT BEHAVIOR
    // ═══════════════════════════════════════════════════════════════
    no_context_behavior?: 'reject' | 'fallback_llm' | 'custom_message';
    no_context_message?: string;
}

export interface Chatbot {
    id: string;
    name: string;
    description?: string;
    icon?: string;
    config: ChatbotConfig;
    dataset_ids: string[];
    allowed_roles: string[];
    visibility: 'public' | 'private';
    owner_id: string;
    is_active: boolean;
    created_at: string;
    updated_at?: string;
}

export interface ChatbotCreate {
    name: string;
    description?: string;
    icon?: string;
    config?: Partial<ChatbotConfig>;
    dataset_ids?: string[];
    allowed_roles?: string[];
    visibility?: 'public' | 'private';
}

export interface ChatbotUpdate {
    name?: string;
    description?: string;
    icon?: string;
    config?: Partial<ChatbotConfig>;
    dataset_ids?: string[];
    allowed_roles?: string[];
    visibility?: 'public' | 'private';
    is_active?: boolean;
}

export interface ChatbotAssignDatasetsRequest {
    dataset_ids: string[];
}

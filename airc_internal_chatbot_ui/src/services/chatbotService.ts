import { coreClient } from '../infrastructure/http/core.client';
import {
    Chatbot,
    ChatbotCreate,
    ChatbotUpdate,
    ChatbotAssignDatasetsRequest
} from '../types/chatbot';

class ChatbotService {
    /**
     * Lấy danh sách chatbots (có hỗ trợ lọc theo role)
     */
    async getChatbots(): Promise<Chatbot[]> {
        const response = await coreClient.get<Chatbot[]>('/chatbots');
        return response.data;
    }

    /**
     * Lấy thông tin chi tiết một chatbot
     */
    async getChatbot(id: string): Promise<Chatbot> {
        const response = await coreClient.get<Chatbot>(`/chatbots/${id}`);
        return response.data;
    }

    /**
     * Tạo chatbot mới (Admin only)
     */
    async createChatbot(data: ChatbotCreate): Promise<Chatbot> {
        const response = await coreClient.post<Chatbot>('/chatbots', data);
        return response.data;
    }

    /**
     * Cập nhật thông tin chatbot
     */
    async updateChatbot(id: string, data: ChatbotUpdate): Promise<Chatbot> {
        const response = await coreClient.patch<Chatbot>(`/chatbots/${id}`, data);
        return response.data;
    }

    /**
     * Xóa chatbot
     */
    async deleteChatbot(id: string): Promise<void> {
        await coreClient.delete(`/chatbots/${id}`);
    }

    /**
     * Gán datasets cho chatbot
     */
    async assignDatasets(chatbotId: string, datasetIds: string[]): Promise<Chatbot> {
        const payload: ChatbotAssignDatasetsRequest = { dataset_ids: datasetIds };
        const response = await coreClient.post<Chatbot>(`/chatbots/${chatbotId}/datasets`, payload);
        return response.data;
    }

    /**
     * Lấy danh sách roles đã được assign chatbot
     * Dùng để disable trong form create/edit (mỗi role trừ admin chỉ được 1 chatbot)
     */
    async getRolesWithChatbot(excludeChatbotId?: string): Promise<string[]> {
        const params = excludeChatbotId ? { exclude_chatbot_id: excludeChatbotId } : {};
        const response = await coreClient.get<string[]>('/chatbots/meta/roles-with-chatbot', { params });
        return response.data;
    }

    /**
     * Lấy danh sách các LLM model khả dụng từ backend
     */
    async getLLMModels(): Promise<{ models: string[]; default_model: string }> {
        const response = await coreClient.get<{ models: string[]; default_model: string }>('/chatbots/meta/llm-models');
        return response.data;
    }
}

export const chatbotService = new ChatbotService();

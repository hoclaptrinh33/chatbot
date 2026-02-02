import { IChatRepository, AskRequest } from '@/core/repositories/IChatRepository';
import { ChatResponse } from '@/core/entities/Chat';
import { coreClient } from '@/infrastructure/http/core.client';

export const chatRepository: IChatRepository = {
    /**
     * Hỏi chatbot
     * @param request - Câu hỏi và context
     */
    async ask(request: AskRequest): Promise<ChatResponse> {
        const response = await coreClient.post<ChatResponse>('/chat/ask', request);
        return response.data;
    }
};

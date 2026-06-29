import { coreClient } from '../infrastructure/http/core.client';
import { ChatMessage, ChatResponse } from '@/core/entities/Chat';

export interface ChatSession {
    id: string;
    name: string;
    user_id: string;
    created_at: string;
    updated_at: string;
    parent_id?: string;
    branch_message_index?: number;
}

export interface AskRequest {
    question: string;
    dataset_ids?: string[];
    history?: ChatMessage[];
    session_id?: string;
    chatbot_id?: string; // Add chatbot_id
}

class ChatService {
    private baseUrl = '/sessions';

    // === Session Management ===

    async getSessions(): Promise<ChatSession[]> {
        const response = await coreClient.get<ChatSession[]>(`${this.baseUrl}/`);
        return response.data;
    }

    async createSession(name: string, parent_id?: string, branch_message_index?: number): Promise<ChatSession> {
        const response = await coreClient.post<ChatSession>(`${this.baseUrl}/`, {
            name,
            parent_id,
            branch_message_index
        });
        return response.data;
    }

    async getMessages(sessionId: string): Promise<ChatMessage[]> {
        const response = await coreClient.get<ChatMessage[]>(`${this.baseUrl}/${sessionId}/messages`);
        // Sort by created_at to ensure correct order
        const messages = response.data;
        return messages.sort((a, b) => {
            const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
            const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
            return timeA - timeB;
        });
    }

    async renameSession(sessionId: string, name: string): Promise<ChatSession> {
        const response = await coreClient.patch<ChatSession>(`${this.baseUrl}/${sessionId}`, { name });
        return response.data;
    }

    async deleteSession(sessionId: string): Promise<void> {
        await coreClient.delete(`${this.baseUrl}/${sessionId}`);
    }

    async addMessage(sessionId: string, role: 'user' | 'assistant', content: string): Promise<ChatMessage> {
        const response = await coreClient.post<ChatMessage>(`${this.baseUrl}/${sessionId}/messages`, {
            session_id: sessionId,
            role,
            content
        });
        return response.data;
    }

    // === RAG / AI ===

    async askQuestion(payload: AskRequest): Promise<ChatResponse> {
        // Sanitize history to only include role and content (backend strictness)
        const sanitizedHistory = payload.history?.map(msg => ({
            role: msg.role,
            content: msg.content
        }));

        const response = await coreClient.post<ChatResponse>('/chat/ask', {
            ...payload,
            history: sanitizedHistory
        });
        return response.data;
    }
}

export default new ChatService();

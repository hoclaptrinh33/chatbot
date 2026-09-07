import { coreClient } from '../infrastructure/http/core.client';
import { ChatMessage, ChatResponse, DatasetSearchResult } from '@/core/entities/Chat';
import { getAuthToken } from '@/stores/authStore';

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

    async askQuestionStream(
        payload: AskRequest,
        handlers: {
            onToken: (text: string) => void;
            onDone: (result: ChatResponse) => void;
            onError: (detail: string) => void;
        }
    ): Promise<void> {
        const sanitizedHistory = payload.history?.map(msg => ({
            role: msg.role,
            content: msg.content
        }));
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        const token = getAuthToken();
        const response = await fetch(`${baseUrl}/chat/ask/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({
                ...payload,
                history: sanitizedHistory,
            }),
        });

        if (!response.ok || !response.body) {
            let detail = 'Không thể kết nối luồng trả lời';
            try {
                const err = await response.json();
                detail = err.detail || detail;
            } catch {
                // ignore
            }
            handlers.onError(detail);
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        const consumeEvent = (raw: string) => {
            const dataLine = raw
                .split('\n')
                .filter((line) => line.startsWith('data:'))
                .map((line) => line.slice(5).trim())
                .join('');
            if (!dataLine) return;
            let parsed: {
                type?: string;
                text?: string;
                detail?: string;
                question?: string;
                answer?: string;
                sources?: DatasetSearchResult[];
                errors?: ChatResponse['errors'];
                debug?: ChatResponse['debug'];
                message_id?: string;
            };
            try {
                parsed = JSON.parse(dataLine);
            } catch {
                return;
            }
            if (parsed.type === 'token' && parsed.text) {
                handlers.onToken(parsed.text);
            } else if (parsed.type === 'done') {
                handlers.onDone({
                    status: 'success',
                    question: parsed.question || payload.question,
                    answer: parsed.answer || '',
                    sources: parsed.sources || [],
                    errors: parsed.errors,
                    debug: parsed.debug,
                    message_id: parsed.message_id,
                });
            } else if (parsed.type === 'error') {
                handlers.onError(parsed.detail || 'Lỗi khi sinh câu trả lời');
            }
        };

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n\n');
            buffer = parts.pop() || '';
            for (const part of parts) {
                consumeEvent(part);
            }
        }
        if (buffer.trim()) {
            consumeEvent(buffer);
        }
    }

    async submitFeedback(payload: {
        message_id: string;
        session_id?: string;
        rating: 'up' | 'down';
        comment?: string;
    }): Promise<void> {
        await coreClient.post('/chat/feedback', payload);
    }

    async getSuggestions(): Promise<string[]> {
        const response = await coreClient.get<{ suggestions: string[] }>('/chat/suggestions');
        return response.data.suggestions || [];
    }
}

export default new ChatService();

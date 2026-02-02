import { ChatResponse, ChatMessage } from '@/core/entities/Chat';

export interface AskRequest {
    question: string;
    dataset_ids: string[];
    history?: ChatMessage[];
}

export interface IChatRepository {
    ask(request: AskRequest): Promise<ChatResponse>;
}

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { AxiosError } from 'axios';
import chatService, { ChatSession } from '../services/chatService';
import { ChatMessage } from '@/core/entities/Chat';
import { RAGDebugMetrics } from '@/components/Chat/RAGDebugPanel';

interface ChatState {
    // Session state
    sessions: ChatSession[];
    currentSessionId: string | null;

    // Current conversation state
    messages: ChatMessage[];
    datasetIds: string[];
    chatbotId: string | null;
    loading: boolean;
    error: string | null;

    // Debug metrics for last response
    lastDebugMetrics: RAGDebugMetrics | null;

    // Actions
    loadSessions: () => Promise<void>;
    createSession: (name?: string) => Promise<string>;
    selectSession: (sessionId: string) => Promise<void>;
    renameSession: (sessionId: string, name: string) => Promise<void>;
    deleteSession: (sessionId: string) => Promise<void>;

    sendMessage: (question: string) => Promise<void>;
    selectDatasets: (ids: string[]) => void;
    selectChatbot: (id: string | null, datasetIds?: string[]) => void;
    clearHistory: () => void;
    resetStore: () => void; // NEW: Reset entire store (for logout/user change)
}

const useChatStore = create<ChatState>()(
    persist(
        (set, get) => ({
            sessions: [],
            currentSessionId: null,
            messages: [],
            datasetIds: [],
            chatbotId: null, // Initial state
            loading: false,
            lastDebugMetrics: null,
            error: null,

            loadSessions: async () => {
                try {
                    const sessions = await chatService.getSessions();
                    set({ sessions });
                } catch (error) {
                    console.error('Failed to load sessions:', error);
                }
            },

            createSession: async (name: string = 'New Chat') => {
                set({ loading: true });
                try {
                    const session = await chatService.createSession(name);
                    const sessions = await chatService.getSessions();
                    set({
                        sessions,
                        currentSessionId: session.id,
                        messages: [],
                        loading: false
                    });
                    return session.id;
                } catch (error) {
                    console.error('Create session failed:', error);
                    set({ loading: false, error: 'Failed to create session' });
                    return '';
                }
            },

            selectSession: async (sessionId: string) => {
                set({ loading: true, currentSessionId: sessionId });
                try {
                    const messages = await chatService.getMessages(sessionId);
                    set({ messages, loading: false });
                } catch (error) {
                    console.error(error);
                    set({ loading: false, error: 'Failed to load messages' });
                }
            },

            renameSession: async (sessionId: string, name: string) => {
                try {
                    await chatService.renameSession(sessionId, name);
                    const sessions = await chatService.getSessions();
                    set({ sessions });
                } catch (error) {
                    console.error('Failed to rename session:', error);
                }
            },

            deleteSession: async (sessionId: string) => {
                try {
                    await chatService.deleteSession(sessionId);
                    const { currentSessionId } = get();
                    const sessions = await chatService.getSessions();

                    if (currentSessionId === sessionId) {
                        set({ sessions, currentSessionId: null, messages: [] });
                    } else {
                        set({ sessions });
                    }
                } catch (error) {
                    console.error('Failed to delete session:', error);
                }
            },

            sendMessage: async (question: string) => {
                console.log('🚀 [ChatStore] sendMessage started:', { question, timestamp: new Date().toISOString() });
                const { messages, datasetIds, chatbotId, currentSessionId, createSession } = get();
                console.log('📊 [ChatStore] Current state:', {
                    messageCount: messages.length,
                    datasetIds,
                    chatbotId,
                    currentSessionId
                });

                // Auto-create session if none exists
                let sessionId = currentSessionId;
                if (!sessionId) {
                    console.log('🆕 [ChatStore] No active session, creating new one...');
                    // Use question as title (truncated)
                    const title = question.length > 30 ? question.substring(0, 30) + '...' : question;
                    sessionId = await createSession(title);
                    if (!sessionId) {
                        console.error('❌ [ChatStore] Failed to create session');
                        return; // Error handled in createSession
                    }
                    console.log('✅ [ChatStore] Session created:', sessionId);
                }

                // Add user message locally
                console.log('💬 [ChatStore] Adding user message to UI...');
                const userMsgId = Date.now().toString();
                const newMessages: ChatMessage[] = [
                    ...messages,
                    {
                        role: 'user',
                        content: question,
                        id: userMsgId,
                        timestamp: new Date().toISOString()
                    }
                ];
                set({ messages: newMessages, loading: true, error: null });
                console.log('✅ [ChatStore] User message added, state updated. Loading=true');

                try {
                    // NOTE: Backend chat_service already saves user & assistant messages
                    // Do NOT call addMessage here to avoid duplicates!

                    // Use only last 10 messages for context
                    const historyContext = newMessages.slice(-10);
                    console.log('📚 [ChatStore] History context:', historyContext.length, 'messages');

                    // Call RAG API (backend will save both user and bot messages)
                    console.log('🤖 [ChatStore] Calling askQuestion API...', {
                        question: question.substring(0, 50) + '...',
                        datasetIds: datasetIds.length,
                        chatbotId: chatbotId,
                        historyLength: historyContext.length
                    });

                    const response = await chatService.askQuestion({
                        question,
                        dataset_ids: datasetIds.length > 0 ? datasetIds : undefined,
                        chatbot_id: chatbotId || undefined,
                        history: historyContext,
                        session_id: sessionId
                    });
                    console.log('✅ [ChatStore] Got response from API:', response.answer.substring(0, 100) + '...');
                    console.log('📊 [ChatStore] Debug metrics:', response.debug);

                    // Add assistant response to UI
                    set((state) => ({
                        messages: [
                            ...state.messages,
                            {
                                role: 'assistant',
                                content: response.answer,
                                id: Date.now().toString(),
                                timestamp: new Date().toISOString()
                            }
                        ],
                        loading: false,
                        lastDebugMetrics: response.debug || null
                    }));
                } catch (error: unknown) {
                    const err = error as AxiosError<{ detail: string }>;
                    console.error('Chat error:', err);
                    set({
                        loading: false,
                        error: err.response?.data?.detail || 'Co loi xay ra khi tra loi'
                    });

                    set((state) => ({
                        messages: [
                            ...state.messages,
                            {
                                role: 'assistant',
                                content: err.response?.data?.detail || 'Xin loi, toi da gap su co khi xu ly yeu cau cua ban.',
                                id: (Date.now() + 2).toString(),
                                timestamp: new Date().toISOString()
                            }
                        ]
                    }));
                }
            },

            selectDatasets: (ids: string[]) => set({ datasetIds: ids }),

            selectChatbot: (id: string | null, datasetIds: string[] = []) => {
                console.log('🤖 [ChatStore] Chatbot selected:', id, 'Datasets:', datasetIds.length);
                // CRITICAL FIX: Reset session when switching chatbots to prevent context leakage
                set({
                    chatbotId: id,
                    datasetIds: datasetIds, // Auto-sync datasets
                    currentSessionId: null, // Reset session
                    messages: [], // Clear UI messages
                    error: null
                });
            },

            clearHistory: () => set({ messages: [], error: null, lastDebugMetrics: null }),

            // Reset entire store - call on logout or user change
            resetStore: () => {
                console.log('🔄 [ChatStore] Resetting store for new user');
                set({
                    sessions: [],
                    currentSessionId: null,
                    messages: [],
                    datasetIds: [],
                    chatbotId: null,
                    loading: false,
                    error: null,
                    lastDebugMetrics: null,
                });
            },
        }),
        {
            name: 'chat-storage',
            skipHydration: true,
            partialize: () => ({
                // DO NOT persist anything user-specific
                // Sessions, chatbots, datasets are all user-specific from API
                // Persisting chatbotId caused data leakage between users
            }),
        }
    )
);

export default useChatStore;

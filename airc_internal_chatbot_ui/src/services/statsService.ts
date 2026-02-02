import { coreClient } from '../infrastructure/http/core.client';

export interface DashboardStats {
    chatbot_count: number;
    dataset_count: number;
    conversation_count: number;
    user_count: number;
    avg_response_time: number;
    accuracy_rate: number;
    cache_hit_rate: number;
    total_chunks_indexed: number;
    conversations_today: number;
    datasets_processing: number;
}

export interface RecentActivity {
    type: 'chatbot' | 'dataset' | 'conversation';
    title: string;
    description: string;
    timestamp: string;
}

/**
 * Get dashboard statistics
 */
export const getDashboardStats = async (): Promise<DashboardStats> => {
    const response = await coreClient.get<DashboardStats>('/stats/dashboard');
    return response.data;
};

/**
 * Get recent activity
 */
export const getRecentActivity = async (limit: number = 5): Promise<RecentActivity[]> => {
    const response = await coreClient.get<RecentActivity[]>('/stats/recent-activity', {
        params: { limit }
    });
    return response.data;
};

const statsService = {
    getDashboardStats,
    getRecentActivity
};

export default statsService;

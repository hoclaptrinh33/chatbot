import { coreClient } from '../infrastructure/http/core.client';

export interface SystemLLMSettings {
    llm_api_base_url: string;
    llm_api_key_set: boolean;
    llm_api_key_masked?: string | null;
    llm_model_name: string;
    tts_voice?: string;
    source: 'database' | 'env' | string;
    updated_at?: string | null;
    updated_by?: string | null;
}

export interface SystemLLMSettingsUpdate {
    llm_api_base_url?: string;
    llm_api_key?: string;
    llm_model_name?: string;
    tts_voice?: string;
}

export interface LLMConnectionTestResult {
    ok: boolean;
    models: string[];
    error?: string | null;
}

class SettingsService {
    async getSettings(): Promise<SystemLLMSettings> {
        const response = await coreClient.get<SystemLLMSettings>('/settings');
        return response.data;
    }

    async updateSettings(payload: SystemLLMSettingsUpdate): Promise<SystemLLMSettings> {
        const response = await coreClient.put<SystemLLMSettings>('/settings', payload);
        return response.data;
    }

    async testConnection(payload: {
        llm_api_base_url: string;
        llm_api_key?: string;
    }): Promise<LLMConnectionTestResult> {
        const response = await coreClient.post<LLMConnectionTestResult>('/settings/test', payload);
        return response.data;
    }
}

export const settingsService = new SettingsService();

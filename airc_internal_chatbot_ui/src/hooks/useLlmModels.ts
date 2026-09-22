'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { chatbotService } from '@/services/chatbotService';
import { settingsService } from '@/services/settingsService';

const HTTP_URL = /^https?:\/\/.+/i;

export interface UseLlmModelsOptions {
    /** Per-bot or settings form endpoint. Empty = system provider. */
    apiBaseUrl?: string | null;
    apiKey?: string | null;
    /** Masked key from GET /settings — omit it so the server reuses the stored key. */
    maskedKey?: string | null;
    enabled?: boolean;
    debounceMs?: number;
}

export interface UseLlmModelsResult {
    models: string[];
    defaultModel: string;
    loading: boolean;
    error: string | null;
    reload: () => Promise<{ ok: boolean; models: string[]; error: string | null }>;
}

function effectiveKey(apiKey?: string | null, maskedKey?: string | null): string | undefined {
    const key = (apiKey || '').trim();
    if (!key || key === maskedKey) {
        return undefined;
    }
    return key;
}

export function useLlmModels(options: UseLlmModelsOptions = {}): UseLlmModelsResult {
    const {
        apiBaseUrl,
        apiKey,
        maskedKey,
        enabled = true,
        debounceMs = 500,
    } = options;

    const [models, setModels] = useState<string[]>([]);
    const [defaultModel, setDefaultModel] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const requestId = useRef(0);

    const fetchModels = useCallback(async () => {
        const url = (apiBaseUrl || '').trim();
        if (url && !HTTP_URL.test(url)) {
            return { ok: false, models: [] as string[], error: 'Endpoint chưa hợp lệ' };
        }

        const id = ++requestId.current;
        setLoading(true);
        setError(null);
        try {
            if (!url) {
                const data = await chatbotService.getLLMModels();
                if (id !== requestId.current) {
                    return { ok: true, models: data.models || [], error: null };
                }
                setModels(data.models || []);
                setDefaultModel(data.default_model || '');
                return { ok: true, models: data.models || [], error: null };
            }

            const result = await settingsService.testConnection({
                llm_api_base_url: url,
                llm_api_key: effectiveKey(apiKey, maskedKey),
            });
            if (id !== requestId.current) {
                return {
                    ok: result.ok,
                    models: result.models || [],
                    error: result.ok ? null : (result.error || 'Không lấy được danh sách model từ endpoint'),
                };
            }
            if (!result.ok) {
                const err = result.error || 'Không lấy được danh sách model từ endpoint';
                setModels([]);
                setDefaultModel('');
                setError(err);
                return { ok: false, models: [], error: err };
            }
            setModels(result.models || []);
            setDefaultModel('');
            return { ok: true, models: result.models || [], error: null };
        } catch {
            const err = 'Không lấy được danh sách model từ endpoint';
            if (id !== requestId.current) {
                return { ok: false, models: [] as string[], error: err };
            }
            setModels([]);
            setDefaultModel('');
            setError(err);
            return { ok: false, models: [], error: err };
        } finally {
            if (id === requestId.current) {
                setLoading(false);
            }
        }
    }, [apiBaseUrl, apiKey, maskedKey]);

    useEffect(() => {
        if (!enabled) return;
        const url = (apiBaseUrl || '').trim();
        if (url && !HTTP_URL.test(url)) return;

        const timer = window.setTimeout(() => {
            void fetchModels();
        }, debounceMs);
        return () => window.clearTimeout(timer);
    }, [enabled, apiBaseUrl, apiKey, maskedKey, debounceMs, fetchModels]);

    return { models, defaultModel, loading, error, reload: fetchModels };
}

export function llmModelsHint(loading: boolean, error: string | null, count: number): string {
    if (loading) return 'Đang tải danh sách model từ endpoint…';
    if (error) return error;
    if (count > 0) return `${count} model lấy từ endpoint — có thể chọn hoặc tự nhập`;
    return 'Có thể tự nhập tên model nếu provider không trả danh sách';
}

/** Keep the current value unless the provider changed and it is not in the new list. */
export function pickModelForProvider(
    models: string[],
    current: string | undefined,
    defaultModel?: string,
    providerChanged = false,
): string | undefined {
    if (!models.length) return current;
    if (current && models.includes(current)) return current;
    if (current && !providerChanged) return current;
    if (defaultModel && models.includes(defaultModel)) return defaultModel;
    return models[0];
}

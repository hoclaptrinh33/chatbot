import { coreClient } from '../infrastructure/http/core.client';

export const DEFAULT_TTS_VOICE = 'vi-VN-HoaiMyNeural';

export interface TTSRequest {
    text: string;
    voice?: string;
}

export interface VoiceOption {
    id: string;
    label: string;
    locale: string;
}

export interface VoiceConfig {
    tts_voice: string;
    voices: VoiceOption[];
}

class VoiceService {
    /**
     * Calls authenticated backend endpoint /api/v1/voice/tts via coreClient to retrieve MP3 audio blob.
     * Uses responseType: 'blob' and passes AbortSignal for immediate request cancellation.
     */
    async generateTTSBlob(text: string, voice: string = DEFAULT_TTS_VOICE, signal?: AbortSignal): Promise<Blob> {
        const response = await coreClient.post<Blob>(
            '/voice/tts',
            { text, voice },
            {
                responseType: 'blob',
                signal,
            }
        );
        return response.data;
    }

    async getConfig(): Promise<VoiceConfig> {
        const response = await coreClient.get<VoiceConfig>('/voice/config');
        return response.data;
    }
}

const voiceService = new VoiceService();
export default voiceService;

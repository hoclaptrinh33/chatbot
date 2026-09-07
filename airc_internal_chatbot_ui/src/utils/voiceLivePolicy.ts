export const LIVE_VOICE_SILENCE_MS = 1600;
export const MIC_LEVEL_EMIT_INTERVAL_MS = 100;
export const STT_NETWORK_ERROR_LIMIT = 3;

export function buildSpeechToSubmit(accumulated: string, interim: string): string {
    return `${accumulated} ${interim}`.replace(/\s+/g, ' ').trim();
}

export function shouldRestartRecognitionAfterTurn(isMuted: boolean): boolean {
    return !isMuted;
}

export function isSpeechMicPermissionError(error: string): boolean {
    return error === 'not-allowed' || error === 'service-not-allowed' || error === 'audio-capture';
}

export function sttNetworkRetryDelayMs(consecutiveFailures: number): number | null {
    if (consecutiveFailures < 1) return 0;
    if (consecutiveFailures >= STT_NETWORK_ERROR_LIMIT) return null;
    return 500 * 2 ** (consecutiveFailures - 1);
}

export function isChatSendNoOp(
    baselineCount: number,
    messages: ReadonlyArray<{ role: string }>
): boolean {
    const appended = messages.slice(baselineCount);
    return !appended.some((message) => message.role === 'user' || message.role === 'assistant');
}

export interface PauseGate {
    readonly isPaused: boolean;
    pause: () => void;
    resume: () => void;
    wait: () => Promise<void>;
    reset: () => void;
}

export function createPauseGate(): PauseGate {
    let paused = false;
    let waiters: Array<() => void> = [];

    const flush = () => {
        const pending = waiters;
        waiters = [];
        for (const resolve of pending) {
            resolve();
        }
    };

    return {
        get isPaused() {
            return paused;
        },
        pause() {
            paused = true;
        },
        resume() {
            if (!paused) return;
            paused = false;
            flush();
        },
        wait() {
            if (!paused) return Promise.resolve();
            return new Promise<void>((resolve) => {
                waiters.push(resolve);
            });
        },
        reset() {
            paused = false;
            flush();
        },
    };
}

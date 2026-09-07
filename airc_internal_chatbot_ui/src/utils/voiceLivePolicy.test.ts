import { describe, it, expect } from 'vitest';
import {
    buildSpeechToSubmit,
    shouldRestartRecognitionAfterTurn,
    isSpeechMicPermissionError,
    sttNetworkRetryDelayMs,
    isChatSendNoOp,
    createPauseGate,
    STT_NETWORK_ERROR_LIMIT,
} from './voiceLivePolicy';

describe('voiceLivePolicy', () => {
    describe('buildSpeechToSubmit', () => {
        it('keeps trailing interim words with finals', () => {
            expect(buildSpeechToSubmit('cho tôi biết học phí', 'kỳ này')).toBe(
                'cho tôi biết học phí kỳ này'
            );
        });

        it('returns interim only when nothing is finalized yet', () => {
            expect(buildSpeechToSubmit('', 'xin chào')).toBe('xin chào');
        });

        it('returns empty string when both parts are blank', () => {
            expect(buildSpeechToSubmit('  ', '')).toBe('');
        });
    });

    describe('shouldRestartRecognitionAfterTurn', () => {
        it('does not restart recognition while muted', () => {
            expect(shouldRestartRecognitionAfterTurn(true)).toBe(false);
        });

        it('restarts recognition when unmuted', () => {
            expect(shouldRestartRecognitionAfterTurn(false)).toBe(true);
        });
    });

    describe('isSpeechMicPermissionError', () => {
        it('treats permission and capture errors as mic denial', () => {
            expect(isSpeechMicPermissionError('not-allowed')).toBe(true);
            expect(isSpeechMicPermissionError('service-not-allowed')).toBe(true);
            expect(isSpeechMicPermissionError('audio-capture')).toBe(true);
        });

        it('ignores transient recognition errors', () => {
            expect(isSpeechMicPermissionError('network')).toBe(false);
            expect(isSpeechMicPermissionError('no-speech')).toBe(false);
            expect(isSpeechMicPermissionError('aborted')).toBe(false);
        });
    });

    describe('sttNetworkRetryDelayMs', () => {
        it('backs off then stops after the limit', () => {
            expect(sttNetworkRetryDelayMs(1)).toBe(500);
            expect(sttNetworkRetryDelayMs(2)).toBe(1000);
            expect(sttNetworkRetryDelayMs(STT_NETWORK_ERROR_LIMIT)).toBeNull();
            expect(sttNetworkRetryDelayMs(STT_NETWORK_ERROR_LIMIT + 1)).toBeNull();
        });
    });

    describe('isChatSendNoOp', () => {
        it('detects a send that added neither user nor assistant text', () => {
            const messages = [{ role: 'user' }, { role: 'assistant' }];
            expect(isChatSendNoOp(2, messages)).toBe(true);
        });

        it('is not a no-op when a user message was appended', () => {
            const messages = [{ role: 'assistant' }, { role: 'user' }];
            expect(isChatSendNoOp(1, messages)).toBe(false);
        });
    });

    describe('createPauseGate', () => {
        it('resolves wait immediately when not paused', async () => {
            const gate = createPauseGate();
            await expect(gate.wait()).resolves.toBeUndefined();
        });

        it('blocks wait until resume', async () => {
            const gate = createPauseGate();
            gate.pause();
            expect(gate.isPaused).toBe(true);

            let released = false;
            const pending = gate.wait().then(() => {
                released = true;
            });

            await Promise.resolve();
            expect(released).toBe(false);

            gate.resume();
            await pending;
            expect(released).toBe(true);
            expect(gate.isPaused).toBe(false);
        });

        it('unblocks waiters on reset without staying paused', async () => {
            const gate = createPauseGate();
            gate.pause();
            const pending = gate.wait();
            gate.reset();
            await pending;
            expect(gate.isPaused).toBe(false);
        });
    });
});

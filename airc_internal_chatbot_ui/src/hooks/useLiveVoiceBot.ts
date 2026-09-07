import { useState, useRef, useEffect, useCallback } from 'react';
import useChatStore from '@/stores/chatStore';
import { useSpeechSynthesis } from './useSpeechSynthesis';
import {
    LIVE_VOICE_SILENCE_MS,
    MIC_LEVEL_EMIT_INTERVAL_MS,
    buildSpeechToSubmit,
    isChatSendNoOp,
    isSpeechMicPermissionError,
    shouldRestartRecognitionAfterTurn,
    sttNetworkRetryDelayMs,
} from '@/utils/voiceLivePolicy';

interface SpeechRecognitionEvent extends Event {
    readonly resultIndex: number;
    readonly results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
    readonly error: string;
    readonly message: string;
}

interface SpeechRecognitionInstance extends EventTarget {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    start: () => void;
    stop: () => void;
    abort: () => void;
    onresult: ((this: SpeechRecognitionInstance, ev: SpeechRecognitionEvent) => void) | null;
    onerror: ((this: SpeechRecognitionInstance, ev: SpeechRecognitionErrorEvent) => void) | null;
    onend: ((this: SpeechRecognitionInstance, ev: Event) => void) | null;
    onstart: ((this: SpeechRecognitionInstance, ev: Event) => void) | null;
}

interface SpeechRecognitionConstructor {
    new (): SpeechRecognitionInstance;
}

declare global {
    interface Window {
        SpeechRecognition?: SpeechRecognitionConstructor;
        webkitSpeechRecognition?: SpeechRecognitionConstructor;
    }
}

export type VoiceModeState =
    | 'IDLE'
    | 'UNSUPPORTED_BROWSER'
    | 'MICROPHONE_DENIED'
    | 'LISTENING'
    | 'PROCESSING'
    | 'SPEAKING'
    | 'PAUSED';

interface UseLiveVoiceBotReturn {
    modeState: VoiceModeState;
    transcript: string;
    aiSubtitle: string;
    isMuted: boolean;
    stopLiveMode: () => void;
    toggleMute: () => void;
    togglePause: () => void;
    micAudioLevel: number;
    microphoneDenied: boolean;
    lastError: string | null;
}

export function useLiveVoiceBot(): UseLiveVoiceBotReturn {
    const isSupported = typeof window !== 'undefined' && !!(window.SpeechRecognition || window.webkitSpeechRecognition);

    const [modeState, setModeState] = useState<VoiceModeState>(isSupported ? 'LISTENING' : 'UNSUPPORTED_BROWSER');
    const [transcript, setTranscript] = useState('');
    const [isMuted, setIsMuted] = useState(false);
    const [micAudioLevel, setMicAudioLevel] = useState(0);
    const [microphoneDenied, setMicrophoneDenied] = useState(false);
    const [lastError, setLastError] = useState<string | null>(null);

    const mountedRef = useRef(true);
    const modeRef = useRef<VoiceModeState>(isSupported ? 'LISTENING' : 'UNSUPPORTED_BROWSER');
    const isMutedRef = useRef(false);
    const accumulatedTextRef = useRef('');

    const { sendMessage } = useChatStore();

    const {
        speak,
        stop: ttsStop,
        pause: ttsPause,
        resume: ttsResume,
        currentSentence: aiSubtitle,
    } = useSpeechSynthesis();

    const turnIdRef = useRef(0);
    const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
    const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const networkRetryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const networkErrorCountRef = useRef(0);
    const mediaStreamRef = useRef<MediaStream | null>(null);
    const audioCtxRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const animFrameRef = useRef<number | null>(null);
    const smoothedMicLevelRef = useRef(0);
    const lastMicLevelEmitRef = useRef(0);

    const startRecognitionRef = useRef<() => void>(() => {});

    const invalidateTurn = useCallback(() => {
        turnIdRef.current++;
    }, []);

    const isTurnValid = useCallback((turnId: number) => mountedRef.current && turnId === turnIdRef.current, []);

    const updateMode = useCallback((newMode: VoiceModeState) => {
        modeRef.current = newMode;
        if (mountedRef.current) {
            setModeState(newMode);
        }
    }, []);

    const clearSilenceTimer = useCallback(() => {
        if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = null;
        }
    }, []);

    const clearNetworkRetryTimer = useCallback(() => {
        if (networkRetryTimerRef.current) {
            clearTimeout(networkRetryTimerRef.current);
            networkRetryTimerRef.current = null;
        }
    }, []);

    const cleanupMicrophone = useCallback(() => {
        if (animFrameRef.current) {
            cancelAnimationFrame(animFrameRef.current);
            animFrameRef.current = null;
        }
        if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach((track) => track.stop());
            mediaStreamRef.current = null;
        }
        if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
            audioCtxRef.current.close().catch(() => {});
            audioCtxRef.current = null;
        }
        analyserRef.current = null;
        smoothedMicLevelRef.current = 0;
        if (mountedRef.current) {
            setMicAudioLevel(0);
        }
    }, []);

    const stopRecognition = useCallback(() => {
        if (recognitionRef.current) {
            try {
                recognitionRef.current.onresult = null;
                recognitionRef.current.onerror = null;
                recognitionRef.current.onend = null;
                recognitionRef.current.stop();
            } catch {
                // Ignore error if recognition is already stopped
            }
            recognitionRef.current = null;
        }
    }, []);

    const resumeListening = useCallback(() => {
        updateMode('LISTENING');
        accumulatedTextRef.current = '';
        if (mountedRef.current) {
            setTranscript('');
        }
        if (shouldRestartRecognitionAfterTurn(isMutedRef.current)) {
            startRecognitionRef.current();
        }
    }, [updateMode]);

    const stopLiveMode = useCallback(() => {
        invalidateTurn();
        clearSilenceTimer();
        clearNetworkRetryTimer();
        stopRecognition();
        ttsStop();
        cleanupMicrophone();
        updateMode('IDLE');
        accumulatedTextRef.current = '';
        networkErrorCountRef.current = 0;
        isMutedRef.current = false;
        if (mountedRef.current) {
            setTranscript('');
            setIsMuted(false);
            setLastError(null);
        }
    }, [invalidateTurn, clearSilenceTimer, clearNetworkRetryTimer, stopRecognition, ttsStop, cleanupMicrophone, updateMode]);

    const handleSendUserSpeech = useCallback(
        async (spokenText: string) => {
            const trimmed = spokenText.trim();
            if (!trimmed || !mountedRef.current) return;

            invalidateTurn();
            const currentTurn = turnIdRef.current;
            clearSilenceTimer();
            stopRecognition();
            updateMode('PROCESSING');

            if (!useChatStore.getState().chatbotId) {
                if (mountedRef.current) {
                    setLastError('Chưa chọn chatbot. Không thể gửi câu hỏi.');
                }
                if (isTurnValid(currentTurn)) {
                    resumeListening();
                }
                return;
            }

            if (mountedRef.current) {
                setLastError(null);
            }

            const baselineCount = useChatStore.getState().messages.length;

            try {
                await sendMessage(trimmed);

                if (!isTurnValid(currentTurn)) return;

                const latestMessages = useChatStore.getState().messages;
                if (isChatSendNoOp(baselineCount, latestMessages)) {
                    if (mountedRef.current) {
                        setLastError('Không gửi được câu hỏi. Vui lòng thử lại.');
                    }
                    resumeListening();
                    return;
                }

                const newAssistantMessage = latestMessages
                    .slice(baselineCount)
                    .find((message) => message.role === 'assistant');

                if (!newAssistantMessage || !newAssistantMessage.content) {
                    if (isTurnValid(currentTurn)) {
                        resumeListening();
                    }
                    return;
                }

                if (!isTurnValid(currentTurn)) return;

                updateMode('SPEAKING');
                await speak(newAssistantMessage.content, currentTurn, isTurnValid);

                if (isTurnValid(currentTurn)) {
                    resumeListening();
                }
            } catch (err) {
                console.error('[useLiveVoiceBot] Error in voice turn:', err);
                if (isTurnValid(currentTurn)) {
                    if (mountedRef.current) {
                        setLastError('Có lỗi khi xử lý câu hỏi. Vui lòng thử lại.');
                    }
                    resumeListening();
                }
            }
        },
        [invalidateTurn, clearSilenceTimer, stopRecognition, updateMode, sendMessage, isTurnValid, speak, resumeListening]
    );

    const startRecognition = useCallback(() => {
        if (typeof window === 'undefined' || !mountedRef.current) return;

        const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognitionClass) {
            updateMode('UNSUPPORTED_BROWSER');
            return;
        }

        clearNetworkRetryTimer();
        stopRecognition();

        const recognition = new SpeechRecognitionClass();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'vi-VN';

        recognition.onresult = (event: SpeechRecognitionEvent) => {
            if (!mountedRef.current || modeRef.current !== 'LISTENING') return;

            networkErrorCountRef.current = 0;
            setLastError(null);

            let newFinal = '';
            let interim = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                const res = event.results[i];
                if (res.isFinal) {
                    newFinal += res[0].transcript;
                } else {
                    interim += res[0].transcript;
                }
            }

            if (newFinal) {
                accumulatedTextRef.current = (accumulatedTextRef.current + ' ' + newFinal).trim();
            }

            const currentSpeech = buildSpeechToSubmit(accumulatedTextRef.current, interim);
            setTranscript(currentSpeech);

            clearSilenceTimer();
            if (currentSpeech.length > 0) {
                silenceTimerRef.current = setTimeout(() => {
                    if (mountedRef.current && modeRef.current === 'LISTENING') {
                        handleSendUserSpeech(currentSpeech);
                    }
                }, LIVE_VOICE_SILENCE_MS);
            }
        };

        recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
            console.warn('[useLiveVoiceBot] Speech recognition error:', event.error);
            if (!mountedRef.current) return;
            if (isSpeechMicPermissionError(event.error)) {
                setMicrophoneDenied(true);
                updateMode('MICROPHONE_DENIED');
                return;
            }
            if (event.error === 'network') {
                networkErrorCountRef.current += 1;
                const delay = sttNetworkRetryDelayMs(networkErrorCountRef.current);
                if (delay === null) {
                    setLastError('Mất kết nối nhận dạng giọng nói. Kiểm tra mạng rồi thử lại.');
                    stopRecognition();
                }
            }
        };

        recognition.onend = () => {
            if (!mountedRef.current || modeRef.current !== 'LISTENING' || isMutedRef.current) {
                return;
            }

            const retryDelay = sttNetworkRetryDelayMs(networkErrorCountRef.current);
            if (networkErrorCountRef.current > 0 && retryDelay === null) {
                return;
            }

            const restart = () => {
                if (!mountedRef.current || modeRef.current !== 'LISTENING' || isMutedRef.current) {
                    return;
                }
                try {
                    recognition.start();
                } catch {
                    startRecognitionRef.current();
                }
            };

            if (retryDelay && retryDelay > 0) {
                clearNetworkRetryTimer();
                networkRetryTimerRef.current = setTimeout(restart, retryDelay);
                return;
            }

            restart();
        };

        try {
            recognition.start();
            recognitionRef.current = recognition;
        } catch (err) {
            console.error('[useLiveVoiceBot] Speech recognition start error:', err);
        }
    }, [stopRecognition, updateMode, clearSilenceTimer, clearNetworkRetryTimer, handleSendUserSpeech]);

    useEffect(() => {
        startRecognitionRef.current = startRecognition;
    }, [startRecognition]);

    const initMicrophoneAudio = useCallback(async () => {
        try {
            if (typeof window === 'undefined' || !navigator.mediaDevices) return;

            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });

            if (!mountedRef.current) {
                stream.getTracks().forEach((track) => track.stop());
                return;
            }

            mediaStreamRef.current = stream;
            setMicrophoneDenied(false);

            const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
            const audioCtx = new AudioContextClass();
            audioCtxRef.current = audioCtx;

            if (audioCtx.state === 'suspended') {
                await audioCtx.resume();
            }

            if (!mountedRef.current) {
                stream.getTracks().forEach((track) => track.stop());
                if (audioCtx.state !== 'closed') {
                    audioCtx.close().catch(() => {});
                }
                if (mediaStreamRef.current === stream) {
                    mediaStreamRef.current = null;
                }
                if (audioCtxRef.current === audioCtx) {
                    audioCtxRef.current = null;
                }
                return;
            }

            const source = audioCtx.createMediaStreamSource(stream);
            const analyser = audioCtx.createAnalyser();
            analyser.fftSize = 256;
            analyser.smoothingTimeConstant = 0.72;
            source.connect(analyser);
            analyserRef.current = analyser;

            const dataArray = new Uint8Array(analyser.fftSize);

            const analyzeFrame = () => {
                if (!mountedRef.current || !analyserRef.current) return;
                analyser.getByteTimeDomainData(dataArray);

                let sumSquares = 0;
                for (let i = 0; i < dataArray.length; i++) {
                    const sample = (dataArray[i] - 128) / 128;
                    sumSquares += sample * sample;
                }
                const rms = Math.sqrt(sumSquares / dataArray.length);
                const normalizedLevel = Math.min(100, Math.max(0, (rms - 0.006) * 950));
                const smoothedLevel = smoothedMicLevelRef.current * 0.72 + normalizedLevel * 0.28;
                smoothedMicLevelRef.current = smoothedLevel;

                const now = typeof performance !== 'undefined' ? performance.now() : Date.now();
                if (now - lastMicLevelEmitRef.current >= MIC_LEVEL_EMIT_INTERVAL_MS) {
                    lastMicLevelEmitRef.current = now;
                    setMicAudioLevel(smoothedLevel);
                }

                if (mountedRef.current) {
                    animFrameRef.current = requestAnimationFrame(analyzeFrame);
                }
            };

            analyzeFrame();
        } catch (err) {
            console.error('[useLiveVoiceBot] Failed to access microphone:', err);
            if (!mountedRef.current || !(err instanceof DOMException)) return;
            if (err.name === 'NotAllowedError') {
                setMicrophoneDenied(true);
                updateMode('MICROPHONE_DENIED');
            } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
                setLastError('Không tìm thấy microphone.');
            } else if (err.name === 'NotReadableError') {
                setLastError('Không đọc được microphone. Hãy đóng ứng dụng khác đang dùng mic.');
            }
        }
    }, [updateMode]);

    const toggleMute = useCallback(() => {
        setIsMuted((prev) => {
            const next = !prev;
            isMutedRef.current = next;
            if (next) {
                stopRecognition();
                clearSilenceTimer();
                clearNetworkRetryTimer();
            } else if (modeRef.current === 'LISTENING') {
                networkErrorCountRef.current = 0;
                setLastError(null);
                startRecognitionRef.current();
            }
            return next;
        });
    }, [stopRecognition, clearSilenceTimer, clearNetworkRetryTimer]);

    const togglePause = useCallback(() => {
        if (modeRef.current === 'SPEAKING') {
            ttsPause();
            updateMode('PAUSED');
        } else if (modeRef.current === 'PAUSED') {
            ttsResume();
            updateMode('SPEAKING');
        }
    }, [ttsPause, ttsResume, updateMode]);

    useEffect(() => {
        mountedRef.current = true;
        isMutedRef.current = false;
        accumulatedTextRef.current = '';
        networkErrorCountRef.current = 0;
        let recognitionStartTimer: ReturnType<typeof setTimeout> | null = null;
        let microphoneInitTimer: ReturnType<typeof setTimeout> | null = null;

        if (isSupported) {
            microphoneInitTimer = setTimeout(() => {
                void initMicrophoneAudio();
            }, 0);
            recognitionStartTimer = setTimeout(() => {
                if (mountedRef.current) {
                    startRecognition();
                }
            }, 0);
        }

        return () => {
            mountedRef.current = false;
            if (recognitionStartTimer) {
                clearTimeout(recognitionStartTimer);
            }
            if (microphoneInitTimer) {
                clearTimeout(microphoneInitTimer);
            }
            invalidateTurn();
            clearSilenceTimer();
            clearNetworkRetryTimer();
            stopRecognition();
            ttsStop();
            cleanupMicrophone();
        };
    }, [isSupported, initMicrophoneAudio, startRecognition, invalidateTurn, clearSilenceTimer, clearNetworkRetryTimer, stopRecognition, ttsStop, cleanupMicrophone]);

    return {
        modeState,
        transcript,
        aiSubtitle,
        isMuted,
        stopLiveMode,
        toggleMute,
        togglePause,
        micAudioLevel,
        microphoneDenied,
        lastError,
    };
}

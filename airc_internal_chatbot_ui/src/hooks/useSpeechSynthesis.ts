import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import voiceService, { DEFAULT_TTS_VOICE } from '@/services/voiceService';
import { chunkTextForTTS } from '@/utils/voiceUtils';
import { createPauseGate } from '@/utils/voiceLivePolicy';
import {
    GaplessScheduler,
    decodeAudioBlob,
    getAudioContext,
} from '@/utils/voicePlayback';

interface UseSpeechSynthesisReturn {
    isPlaying: boolean;
    currentSentence: string;
    speak: (text: string, turnId: number, isTurnValid: (turnId: number) => boolean) => Promise<void>;
    stop: () => void;
    pause: () => void;
    resume: () => void;
}

type PreparedClip = {
    sentence: string;
    buffer: AudioBuffer | null;
};

function pickVietnameseBrowserVoice(preferredId: string): SpeechSynthesisVoice | undefined {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
        return undefined;
    }
    const voices = window.speechSynthesis.getVoices();
    const vi = voices.filter((voice) => voice.lang.toLowerCase().startsWith('vi'));
    if (!vi.length) {
        return undefined;
    }
    const wantFemale = preferredId.includes('HoaiMy');
    const gendered = vi.find((voice) =>
        wantFemale
            ? /female|hoài|hoai|my|nữ/i.test(voice.name)
            : /male|nam|minh/i.test(voice.name)
    );
    return gendered || vi[0];
}

export function useSpeechSynthesis(): UseSpeechSynthesisReturn {
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentSentence, setCurrentSentence] = useState('');

    const abortControllerRef = useRef<AbortController | null>(null);
    const queueRef = useRef<string[]>([]);
    const pauseGateRef = useRef(createPauseGate());
    const voiceRef = useRef(DEFAULT_TTS_VOICE);
    const schedulerRef = useRef<GaplessScheduler | null>(null);
    const pendingSpeakRef = useRef<((value?: void) => void) | null>(null);

    const getScheduler = useCallback(() => {
        if (!schedulerRef.current) {
            schedulerRef.current = new GaplessScheduler(getAudioContext());
        }
        return schedulerRef.current;
    }, []);

    const cleanupAudio = useCallback(() => {
        if (pendingSpeakRef.current) {
            const settle = pendingSpeakRef.current;
            pendingSpeakRef.current = null;
            settle();
        }
        schedulerRef.current?.stop();
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }
        if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
    }, []);

    const stop = useCallback(() => {
        queueRef.current = [];
        pauseGateRef.current.reset();
        cleanupAudio();
        setIsPlaying(false);
        setCurrentSentence('');
    }, [cleanupAudio]);

    const pause = useCallback(() => {
        pauseGateRef.current.pause();
        void schedulerRef.current?.pause();
        if (typeof window !== 'undefined' && 'speechSynthesis' in window && window.speechSynthesis.speaking) {
            window.speechSynthesis.pause();
        }
        setIsPlaying(false);
    }, []);

    const resume = useCallback(() => {
        if (!pauseGateRef.current.isPaused) return;
        pauseGateRef.current.resume();
        void schedulerRef.current?.resume();
        if (typeof window !== 'undefined' && 'speechSynthesis' in window && window.speechSynthesis.paused) {
            window.speechSynthesis.resume();
        }
        setIsPlaying(true);
    }, []);

    const speakWithBrowser = useCallback(async (sentence: string) => {
        if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
            return;
        }
        await new Promise<void>((resolve) => {
            pendingSpeakRef.current = resolve;
            const utterance = new SpeechSynthesisUtterance(sentence);
            utterance.lang = 'vi-VN';
            const matched = pickVietnameseBrowserVoice(voiceRef.current);
            if (matched) {
                utterance.voice = matched;
            }
            utterance.onend = () => {
                pendingSpeakRef.current = null;
                resolve();
            };
            utterance.onerror = () => {
                pendingSpeakRef.current = null;
                resolve();
            };
            window.speechSynthesis.speak(utterance);
        });
    }, []);

    const speak = useCallback(
        async (fullText: string, turnId: number, isTurnValid: (turnId: number) => boolean) => {
            stop();

            if (!isTurnValid(turnId)) {
                return;
            }

            const sentences = chunkTextForTTS(fullText);
            if (sentences.length === 0) return;

            queueRef.current = [...sentences];
            setIsPlaying(true);

            const waitIfPaused = async () => {
                await pauseGateRef.current.wait();
                return isTurnValid(turnId);
            };

            const abortController = new AbortController();
            abortControllerRef.current = abortController;
            const voice = voiceRef.current;
            const scheduler = getScheduler();
            await scheduler.ensureRunning();

            const loadClip = async (sentence: string): Promise<PreparedClip> => {
                try {
                    let blob = await voiceService.generateTTSBlob(
                        sentence,
                        voice,
                        abortController.signal
                    );
                    try {
                        const buffer = await decodeAudioBlob(scheduler.context, blob);
                        return { sentence, buffer };
                    } catch {
                        return { sentence, buffer: null };
                    }
                } catch (err) {
                    if (!isTurnValid(turnId) || abortController.signal.aborted) {
                        return { sentence, buffer: null };
                    }
                    console.warn('[useSpeechSynthesis] Edge-TTS failed, retrying once:', err);
                    try {
                        const blob = await voiceService.generateTTSBlob(
                            sentence,
                            voice,
                            abortController.signal
                        );
                        const buffer = await decodeAudioBlob(scheduler.context, blob);
                        return { sentence, buffer };
                    } catch {
                        return { sentence, buffer: null };
                    }
                }
            };

            const processQueue = async () => {
                const chunks = [...queueRef.current];
                queueRef.current = [];
                if (chunks.length === 0) return;

                let nextIndex = 0;
                const inflight: Promise<PreparedClip>[] = [];
                const pump = () => {
                    while (inflight.length < 3 && nextIndex < chunks.length) {
                        inflight.push(loadClip(chunks[nextIndex]));
                        nextIndex += 1;
                    }
                };
                pump();

                const timeline: Array<{ sentence: string; startAt: number; endAt: number }> = [];
                let lastEndAt = scheduler.context.currentTime;

                while (inflight.length > 0) {
                    if (!(await waitIfPaused())) {
                        return;
                    }
                    const clip = await inflight.shift();
                    pump();
                    if (!clip || !isTurnValid(turnId)) {
                        return;
                    }

                    try {
                        if (clip.buffer) {
                            await scheduler.ensureRunning();
                            const { startAt, endAt } = scheduler.schedule(clip.buffer);
                            timeline.push({ sentence: clip.sentence, startAt, endAt });
                            lastEndAt = endAt;
                            if (timeline.length === 1) {
                                setCurrentSentence(clip.sentence);
                            }
                        } else {
                            const caughtUp = await scheduler.waitUntil(
                                lastEndAt,
                                () => isTurnValid(turnId)
                            );
                            if (!caughtUp) return;
                            setCurrentSentence(clip.sentence);
                            await speakWithBrowser(clip.sentence);
                            lastEndAt = scheduler.context.currentTime;
                        }
                    } catch {
                        if (!isTurnValid(turnId)) {
                            return;
                        }
                        setCurrentSentence(clip.sentence);
                        await speakWithBrowser(clip.sentence);
                        lastEndAt = scheduler.context.currentTime;
                    }
                }

                await scheduler.waitUntil(
                    lastEndAt,
                    () => isTurnValid(turnId),
                    (now) => {
                        const active = [...timeline].reverse().find(
                            (item) => now >= item.startAt && now < item.endAt
                        );
                        if (active) {
                            setCurrentSentence(active.sentence);
                        }
                    }
                );

                if (isTurnValid(turnId)) {
                    setIsPlaying(false);
                    setCurrentSentence('');
                }
            };

            await processQueue();
        },
        [stop, getScheduler, speakWithBrowser]
    );

    useEffect(() => {
        let cancelled = false;
        voiceService
            .getConfig()
            .then((config) => {
                if (!cancelled && config.tts_voice) {
                    voiceRef.current = config.tts_voice;
                }
            })
            .catch(() => {});
        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        return () => {
            stop();
            void schedulerRef.current?.context.close();
            schedulerRef.current = null;
        };
    }, [stop]);

    return useMemo(
        () => ({
            isPlaying,
            currentSentence,
            speak,
            stop,
            pause,
            resume,
        }),
        [isPlaying, currentSentence, speak, stop, pause, resume]
    );
}

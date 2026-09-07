/**
 * Gapless playback helpers for live TTS using Web Audio API.
 */

const SILENCE_THRESHOLD = 0.01;
const EXTRA_TRIM_SEC = 0.03;

export function getAudioContext(): AudioContext {
    const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    return new Ctor();
}

/** Leading/trailing near-silence in seconds. */
export function measureSilenceTrim(buffer: AudioBuffer): { offset: number; duration: number } {
    const data = buffer.getChannelData(0);
    const sampleRate = buffer.sampleRate;
    let start = 0;
    let end = data.length - 1;
    while (start < end && Math.abs(data[start]) < SILENCE_THRESHOLD) {
        start += 1;
    }
    while (end > start && Math.abs(data[end]) < SILENCE_THRESHOLD) {
        end -= 1;
    }
    const extra = Math.floor(EXTRA_TRIM_SEC * sampleRate);
    start = Math.min(end, start + extra);
    end = Math.max(start, end - extra);
    const offset = start / sampleRate;
    const duration = Math.max(0.04, (end - start) / sampleRate);
    return { offset, duration };
}

export async function decodeAudioBlob(ctx: AudioContext, blob: Blob): Promise<AudioBuffer> {
    const raw = await blob.arrayBuffer();
    return ctx.decodeAudioData(raw.slice(0));
}

export class GaplessScheduler {
    private ctx: AudioContext;
    private nextStart = 0;
    private sources: AudioBufferSourceNode[] = [];

    constructor(ctx: AudioContext) {
        this.ctx = ctx;
    }

    get context(): AudioContext {
        return this.ctx;
    }

    async ensureRunning(): Promise<void> {
        if (this.ctx.state === 'suspended') {
            await this.ctx.resume();
        }
    }

    schedule(buffer: AudioBuffer): { startAt: number; endAt: number } {
        const trim = measureSilenceTrim(buffer);
        const source = this.ctx.createBufferSource();
        source.buffer = buffer;
        source.connect(this.ctx.destination);

        const now = this.ctx.currentTime;
        if (this.nextStart < now) {
            this.nextStart = now;
        }
        const startAt = this.nextStart;
        source.start(startAt, trim.offset, trim.duration);
        this.nextStart = startAt + trim.duration;
        this.sources.push(source);
        source.onended = () => {
            this.sources = this.sources.filter((item) => item !== source);
        };
        return { startAt, endAt: this.nextStart };
    }

    async pause(): Promise<void> {
        if (this.ctx.state === 'running') {
            await this.ctx.suspend();
        }
    }

    async resume(): Promise<void> {
        if (this.ctx.state === 'suspended') {
            await this.ctx.resume();
        }
    }

    stop(): void {
        for (const source of this.sources) {
            try {
                source.stop();
            } catch {
                // already stopped
            }
            try {
                source.disconnect();
            } catch {
                // already disconnected
            }
        }
        this.sources = [];
        this.nextStart = this.ctx.currentTime;
    }

    async waitUntil(
        endAt: number,
        isAlive: () => boolean,
        onTick?: (currentTime: number) => void,
    ): Promise<boolean> {
        while (isAlive() && this.ctx.currentTime < endAt - 0.012) {
            onTick?.(this.ctx.currentTime);
            const remainingMs = Math.max(8, (endAt - this.ctx.currentTime) * 1000);
            await new Promise((resolve) => window.setTimeout(resolve, Math.min(50, remainingMs)));
        }
        return isAlive();
    }
}

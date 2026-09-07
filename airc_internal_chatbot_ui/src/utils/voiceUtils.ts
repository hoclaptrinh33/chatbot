/**
 * Utility functions for processing text for Speech Synthesis / TTS
 */

/**
 * Cleans text by stripping markdown symbols, HTML tags, code snippets, and emojis
 * so that Text-to-Speech engines pronounce natural words instead of punctuation syntax.
 */
export function cleanTextForTTS(text: string): string {
    if (!text) return '';

    let cleaned = text;

    // 1. Remove code blocks ```...```
    cleaned = cleaned.replace(/```[\s\S]*?```/g, ' Đoạn mã đã được bỏ qua. ');

    // 2. Remove inline code `code`
    cleaned = cleaned.replace(/`([^`]+)`/g, '$1');

    // 3. Remove images ![alt](url)
    cleaned = cleaned.replace(/!\[([^\]]*)\]\([^)]+\)/g, '');

    // 4. Remove links [text](url) -> text
    cleaned = cleaned.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');

    // 5. Remove headers (# Header)
    cleaned = cleaned.replace(/^#{1,6}\s+/gm, '');

    // 6. Remove bold/italic formatting (**bold**, *italic*, __bold__, _italic_)
    cleaned = cleaned.replace(/(\*\*|__|\*|_)(.*?)\1/g, '$2');

    // 7. Remove bullet points (- item, * item, 1. item)
    cleaned = cleaned.replace(/^[\s\t]*[-*+]\s+/gm, '');
    cleaned = cleaned.replace(/^[\s\t]*\d+\.\s+/gm, '');

    // 8. Remove blockquotes (> quote)
    cleaned = cleaned.replace(/^>\s+/gm, '');

    // 9. Remove HTML tags
    cleaned = cleaned.replace(/<[^>]*>/g, '');

    // 10. Remove emojis
    cleaned = cleaned.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '');

    // 11. Normalize excessive newlines and spaces
    cleaned = cleaned.replace(/\s+/g, ' ').trim();

    return cleaned;
}

const MIN_WORDS = 5;
const FIRST_CHUNK_MAX = 280;
const NEXT_CHUNK_MAX = 320;
const HARD_MAX = 400;

function wordCount(text: string): number {
    return text.split(/\s+/).filter(Boolean).length;
}

function splitOversized(text: string, maxLen: number): string[] {
    const parts: string[] = [];
    let remaining = text;
    while (remaining.length > maxLen) {
        const window = remaining.slice(0, maxLen + 1);
        const boundary = Math.max(
            window.lastIndexOf('. '),
            window.lastIndexOf('? '),
            window.lastIndexOf('! '),
            window.lastIndexOf('; '),
            window.lastIndexOf(', '),
            window.lastIndexOf(' ')
        );
        const splitAt = boundary >= Math.min(80, maxLen / 2) ? boundary + 1 : maxLen;
        parts.push(remaining.slice(0, splitAt).trim());
        remaining = remaining.slice(splitAt).trim();
    }
    if (remaining) {
        parts.push(remaining);
    }
    return parts;
}

/**
 * Splits cleaned text on sentence terminators.
 */
export function splitIntoSentences(text: string): string[] {
    const cleaned = cleanTextForTTS(text);
    if (!cleaned) return [];
    const rawSentences = cleaned.split(/(?<=[.!?])\s+/);
    const sentences = rawSentences.map((item) => item.trim()).filter(Boolean);
    return sentences.length > 0 ? sentences : [cleaned];
}

/**
 * Packs sentences into TTS requests: first chunk is shorter so audio
 * starts sooner; later chunks are longer to cut padding and keep intonation.
 */
export function chunkTextForTTS(text: string): string[] {
    const sentences = splitIntoSentences(text);
    if (sentences.length === 0) return [];

    const merged: string[] = [];
    for (const sentence of sentences) {
        const previous = merged[merged.length - 1];
        if (
            previous &&
            (wordCount(sentence) < MIN_WORDS || wordCount(previous) < MIN_WORDS) &&
            previous.length + 1 + sentence.length <= HARD_MAX
        ) {
            merged[merged.length - 1] = `${previous} ${sentence}`;
        } else {
            merged.push(sentence);
        }
    }

    const packed: string[] = [];
    let buffer = '';
    let limit = FIRST_CHUNK_MAX;
    for (const sentence of merged) {
        if (!buffer) {
            if (sentence.length > limit) {
                const pieces = splitOversized(sentence, limit);
                packed.push(...pieces);
                limit = NEXT_CHUNK_MAX;
                continue;
            }
            buffer = sentence;
            continue;
        }
        if (buffer.length + 1 + sentence.length <= limit) {
            buffer = `${buffer} ${sentence}`;
        } else {
            packed.push(buffer);
            buffer = sentence;
            limit = NEXT_CHUNK_MAX;
        }
    }
    if (buffer) {
        packed.push(buffer);
    }
    return packed;
}

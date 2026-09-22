import { describe, it, expect } from 'vitest';
import { chunkTextForTTS, cleanTextForTTS, splitIntoSentences } from './voiceUtils';

describe('voiceUtils', () => {
    describe('cleanTextForTTS', () => {
        it('should strip markdown bold, italic, and headers', () => {
            const input = '# Tiêu đề\n\nĐây là **văn bản đậm** và *in nghiêng*.';
            const output = cleanTextForTTS(input);
            expect(output).toBe('Tiêu đề Đây là văn bản đậm và in nghiêng.');
        });

        it('should strip code blocks and inline code', () => {
            const input = 'Dưới đây là mã:\n```python\nprint("Hello")\n```\nVà biến `x`.';
            const output = cleanTextForTTS(input);
            expect(output).toBe('Dưới đây là mã: Đoạn mã đã được bỏ qua. Và biến x.');
        });

        it('should convert markdown links to plain text', () => {
            const input = 'Truy cập [Trang chủ AIRC](https://airc.edu.vn) để biết chi tiết.';
            const output = cleanTextForTTS(input);
            expect(output).toBe('Truy cập Trang chủ AIRC để biết chi tiết.');
        });

        it('should strip emojis', () => {
            const input = 'Xin chào các bạn! 👋😊';
            const output = cleanTextForTTS(input);
            expect(output).toBe('Xin chào các bạn!');
        });
    });

    describe('splitIntoSentences', () => {
        it('should split text into multiple sentences based on punctuation', () => {
            const input = 'Xin chào bạn! Tôi là trợ lý AI. Bạn cần giúp gì không?';
            const sentences = splitIntoSentences(input);
            expect(sentences).toEqual([
                'Xin chào bạn!',
                'Tôi là trợ lý AI.',
                'Bạn cần giúp gì không?'
            ]);
        });

        it('should return empty array for empty input', () => {
            expect(splitIntoSentences('')).toEqual([]);
        });
    });

    describe('chunkTextForTTS', () => {
        it('should merge short opening sentences so the first clip has enough words', () => {
            const input = 'Xin chào bạn! Tôi là trợ lý AI. Bạn cần giúp gì không?';
            const chunks = chunkTextForTTS(input);
            expect(chunks.length).toBeLessThanOrEqual(2);
            expect(chunks[0].startsWith('Xin chào bạn!')).toBe(true);
            expect(chunks.join(' ')).toContain('Bạn cần giúp gì không?');
        });

        it('should pack many sentences into fewer TTS clips', () => {
            const sentences = Array.from({ length: 8 }, (_, index) => `Đây là câu trả lời số ${index + 1} với nội dung đủ dài để ghép nhóm.`);
            const chunks = chunkTextForTTS(sentences.join(' '));
            expect(chunks.length).toBeGreaterThan(1);
            expect(chunks.length).toBeLessThan(sentences.length);
            expect(chunks[0].length).toBeLessThanOrEqual(280);
        });
    });
});

'use client';

import React, { useEffect, useRef } from 'react';
import { VoiceModeState } from '@/hooks/useLiveVoiceBot';

interface AudioVisualizerProps {
    modeState: VoiceModeState;
    micAudioLevel: number;
    size?: number;
}

export default function AudioVisualizer({
    modeState,
    micAudioLevel,
    size = 240,
}: AudioVisualizerProps) {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const animFrameRef = useRef<number | null>(null);
    const phaseRef = useRef(0);
    const micAudioLevelRef = useRef(micAudioLevel);

    useEffect(() => {
        micAudioLevelRef.current = micAudioLevel;
    }, [micAudioLevel]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let active = true;

        const render = () => {
            if (!active) return;

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;
            const baseRadius = size * 0.28;

            phaseRef.current += 0.04;
            const phase = phaseRef.current;
            const currentMicLevel = micAudioLevelRef.current;
            const signalStrength = Math.min(1, currentMicLevel / 55);
            const hasVoiceSignal = currentMicLevel >= 8;

            // Compute dynamic expansion based on mic input level or state pulse
            let pulse = 0;
            if (modeState === 'LISTENING') {
                pulse = signalStrength * (size * 0.18);
            } else if (modeState === 'PROCESSING') {
                pulse = Math.sin(phase * 2) * 8 + 4;
            } else if (modeState === 'SPEAKING') {
                pulse = Math.sin(phase * 3) * 12 + (currentMicLevel / 100) * 10;
            }

            const currentRadius = Math.max(10, baseRadius + pulse);

            // Outer glowing aura rings
            const gradientAura = ctx.createRadialGradient(
                centerX,
                centerY,
                currentRadius * 0.5,
                centerX,
                centerY,
                currentRadius * 1.8
            );

            if (modeState === 'PROCESSING') {
                gradientAura.addColorStop(0, 'rgba(234, 179, 8, 0.6)'); // Yellow pulse for thinking
                gradientAura.addColorStop(0.6, 'rgba(245, 158, 11, 0.2)');
                gradientAura.addColorStop(1, 'rgba(0, 0, 0, 0)');
            } else if (modeState === 'SPEAKING') {
                gradientAura.addColorStop(0, 'rgba(220, 38, 38, 0.8)'); // Vibrant AIRC Red for speaking
                gradientAura.addColorStop(0.6, 'rgba(185, 28, 28, 0.3)');
                gradientAura.addColorStop(1, 'rgba(0, 0, 0, 0)');
            } else if (modeState === 'UNSUPPORTED_BROWSER') {
                gradientAura.addColorStop(0, 'rgba(107, 114, 128, 0.5)'); // Gray
                gradientAura.addColorStop(1, 'rgba(0, 0, 0, 0)');
            } else if (modeState === 'LISTENING' && hasVoiceSignal) {
                gradientAura.addColorStop(0, `rgba(16, 185, 129, ${0.35 + signalStrength * 0.45})`);
                gradientAura.addColorStop(0.6, `rgba(52, 211, 153, ${0.08 + signalStrength * 0.2})`);
                gradientAura.addColorStop(1, 'rgba(0, 0, 0, 0)');
            } else {
                gradientAura.addColorStop(0, 'rgba(239, 68, 68, 0.5)'); // Soft Red
                gradientAura.addColorStop(0.7, 'rgba(220, 38, 38, 0.15)');
                gradientAura.addColorStop(1, 'rgba(0, 0, 0, 0)');
            }

            ctx.fillStyle = gradientAura;
            ctx.beginPath();
            ctx.arc(centerX, centerY, currentRadius * 1.8, 0, Math.PI * 2);
            ctx.fill();

            // Inner core orb with organic wave deformation
            ctx.beginPath();
            const points = 64;
            for (let i = 0; i <= points; i++) {
                const angle = (i / points) * Math.PI * 2;
                const waveAmplitude = modeState === 'LISTENING' ? 2 + signalStrength * 9 : 4;
                const wave =
                    Math.sin(angle * 4 + phase) * waveAmplitude +
                    Math.cos(angle * 6 - phase) * waveAmplitude * 0.7;
                const r = currentRadius + wave;
                const x = centerX + Math.cos(angle) * r;
                const y = centerY + Math.sin(angle) * r;

                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            }
            ctx.closePath();

            const coreGradient = ctx.createLinearGradient(
                centerX - currentRadius,
                centerY - currentRadius,
                centerX + currentRadius,
                centerY + currentRadius
            );
            if (modeState === 'PROCESSING') {
                coreGradient.addColorStop(0, '#fef08a');
                coreGradient.addColorStop(1, '#eab308');
            } else if (modeState === 'SPEAKING') {
                coreGradient.addColorStop(0, '#fca5a5');
                coreGradient.addColorStop(1, '#dc2626');
            } else if (modeState === 'LISTENING' && hasVoiceSignal) {
                coreGradient.addColorStop(0, '#a7f3d0');
                coreGradient.addColorStop(1, '#059669');
            } else {
                coreGradient.addColorStop(0, '#f87171');
                coreGradient.addColorStop(1, '#b91c1c');
            }

            ctx.fillStyle = coreGradient;
            ctx.shadowColor = modeState === 'LISTENING' && hasVoiceSignal
                ? `rgba(16, 185, 129, ${0.35 + signalStrength * 0.45})`
                : 'rgba(220, 38, 38, 0.6)';
            ctx.shadowBlur = 20 + signalStrength * 14;
            ctx.fill();
            ctx.shadowBlur = 0;

            animFrameRef.current = requestAnimationFrame(render);
        };

        render();

        return () => {
            active = false;
            if (animFrameRef.current) {
                cancelAnimationFrame(animFrameRef.current);
            }
        };
    }, [modeState, size]);

    return (
        <canvas
            ref={canvasRef}
            width={size}
            height={size}
            className="mx-auto block"
        />
    );
}

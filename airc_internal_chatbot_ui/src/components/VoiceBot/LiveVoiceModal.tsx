'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Button, Tooltip } from 'antd';
import {
    AudioOutlined,
    AudioMutedOutlined,
    PauseOutlined,
    CaretRightOutlined,
    CloseOutlined,
    EyeOutlined,
    EyeInvisibleOutlined,
    WarningOutlined,
} from '@ant-design/icons';

import { useLiveVoiceBot } from '@/hooks/useLiveVoiceBot';
import AudioVisualizer from './AudioVisualizer';

interface LiveVoiceModalProps {
    onClose: () => void;
}

export default function LiveVoiceModal({ onClose }: LiveVoiceModalProps) {
    const [showSubtitles, setShowSubtitles] = useState(true);
    const rootRef = useRef<HTMLDivElement>(null);

    const {
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
    } = useLiveVoiceBot();

    const isMicrophoneDenied = modeState === 'MICROPHONE_DENIED' || microphoneDenied;

    const handleClose = () => {
        stopLiveMode();
        onClose();
    };

    useEffect(() => {
        rootRef.current?.focus();
    }, []);

    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                stopLiveMode();
                onClose();
            }
        };
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, [stopLiveMode, onClose]);

    const getStatusText = () => {
        switch (modeState) {
            case 'IDLE':
                return 'Đang khởi tạo Voice Mode...';
            case 'UNSUPPORTED_BROWSER':
                return 'Trình duyệt không hỗ trợ Web Speech API';
            case 'MICROPHONE_DENIED':
                return 'Chưa được cấp quyền sử dụng microphone';
            case 'LISTENING':
                return isMuted ? 'Microphone đã tắt (Tạm dừng nghe)' : 'Đang lắng nghe bạn...';
            case 'PROCESSING':
                return 'AIRC Assistant đang suy nghĩ...';
            case 'SPEAKING':
                return 'AIRC Assistant đang trả lời...';
            case 'PAUSED':
                return 'Đang tạm dừng phát âm thanh';
            default:
                return '';
        }
    };

    return (
        <div
            ref={rootRef}
            tabIndex={-1}
            className="fixed inset-0 z-50 flex flex-col justify-between bg-slate-950/90 text-white backdrop-blur-xl transition-all duration-300 p-6 sm:p-10 outline-none"
        >
            {/* Top Header Bar */}
            <div className="flex items-center justify-between w-full max-w-4xl mx-auto">
                <div className="flex items-center gap-3">
                    <span className="relative flex h-3 w-3">
                        {modeState === 'LISTENING' && !isMuted && (
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                        )}
                        <span
                            className={`relative inline-flex rounded-full h-3 w-3 ${
                                modeState === 'SPEAKING'
                                    ? 'bg-red-500'
                                    : modeState === 'PROCESSING'
                                    ? 'bg-yellow-400'
                                    : modeState === 'LISTENING' && !isMuted
                                    ? 'bg-emerald-500'
                                    : 'bg-gray-500'
                            }`}
                        ></span>
                    </span>
                    <span className="text-lg font-semibold tracking-wide text-red-500">
                        AIRC Live Mode
                    </span>
                </div>

                <div className="flex items-center gap-3">
                    <Tooltip title={showSubtitles ? 'Ẩn phụ đề' : 'Hiện phụ đề'}>
                        <Button
                            type="text"
                            shape="circle"
                            size="large"
                            icon={showSubtitles ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                            onClick={() => setShowSubtitles((prev) => !prev)}
                            className="text-gray-300 hover:text-white hover:bg-white/10"
                        />
                    </Tooltip>
                    <Tooltip title="Thoát Live Mode">
                        <Button
                            type="text"
                            shape="circle"
                            size="large"
                            icon={<CloseOutlined />}
                            onClick={handleClose}
                            className="text-gray-300 hover:text-white hover:bg-white/10"
                        />
                    </Tooltip>
                </div>
            </div>

            {/* Central Visualizer Area */}
            <div className="flex-1 flex flex-col items-center justify-center text-center my-6">
                {modeState === 'UNSUPPORTED_BROWSER' ? (
                    <div className="max-w-md bg-red-950/40 border border-red-800/50 p-8 rounded-2xl text-center shadow-2xl">
                        <WarningOutlined className="text-5xl text-orange-400 mb-4" />
                        <h3 className="text-xl font-bold text-gray-100 mb-2">
                            Trình duyệt chưa hỗ trợ
                        </h3>
                        <p className="text-gray-300 text-sm leading-relaxed mb-4">
                            Tính năng Nhận dạng giọng nói (Web Speech API) yêu cầu trình duyệt tương thích.
                            Vui lòng sử dụng <strong>Google Chrome</strong> hoặc <strong>Microsoft Edge</strong> để trải nghiệm Live Mode.
                        </p>
                        <Button type="primary" danger onClick={handleClose}>
                            Đóng
                        </Button>
                    </div>
                ) : isMicrophoneDenied ? (
                    <div className="max-w-md bg-red-950/40 border border-red-800/50 p-8 rounded-2xl text-center shadow-2xl">
                        <WarningOutlined className="text-5xl text-orange-400 mb-4" />
                        <h3 className="text-xl font-bold text-gray-100 mb-2">
                            Chưa cấp quyền microphone
                        </h3>
                        <p className="text-gray-300 text-sm leading-relaxed mb-4">
                            Chrome đã hỗ trợ nhận dạng giọng nói, nhưng cần quyền dùng microphone. Hãy bấm biểu tượng ổ khóa cạnh địa chỉ <strong>{typeof window !== 'undefined' ? window.location.host : 'trình duyệt'}</strong>, đặt Microphone thành <strong>Cho phép</strong>, rồi tải lại trang.
                        </p>
                        <Button type="primary" danger onClick={handleClose}>
                            Đóng
                        </Button>
                    </div>
                ) : (
                    <>
                        <div className="mb-6">
                            <AudioVisualizer
                                modeState={modeState}
                                micAudioLevel={micAudioLevel}
                                size={280}
                            />
                        </div>

                        <div className="text-lg sm:text-xl font-medium text-gray-200 tracking-wide transition-all">
                            {getStatusText()}
                        </div>
                        {lastError && (
                            <div className="mt-3 max-w-md text-sm text-orange-300">
                                {lastError}
                            </div>
                        )}
                        {modeState === 'LISTENING' && (
                            <div className={`mt-2 text-sm font-medium ${micAudioLevel >= 8 ? 'text-emerald-400' : 'text-gray-500'}`}>
                                {micAudioLevel >= 8
                                    ? `Microphone đang nhận âm thanh · ${Math.round(micAudioLevel)}%`
                                    : 'Microphone đang chờ âm thanh...'}
                            </div>
                        )}
                    </>
                )}

                {/* Subtitle Display */}
                {showSubtitles && modeState !== 'UNSUPPORTED_BROWSER' && !isMicrophoneDenied && (
                    <div className="mt-8 max-w-2xl w-full min-h-[80px] bg-white/5 border border-white/10 rounded-2xl p-4 sm:p-6 backdrop-blur-md transition-all">
                        {modeState === 'SPEAKING' || modeState === 'PAUSED' ? (
                            <div>
                                <div className="text-xs uppercase tracking-wider text-red-400 font-semibold mb-1">
                                    AIRC Assistant:
                                </div>
                                <div className="text-base sm:text-lg text-gray-100 italic">
                                    &quot;{aiSubtitle || '...'}&quot;
                                </div>
                            </div>
                        ) : (
                            <div>
                                <div className="text-xs uppercase tracking-wider text-emerald-400 font-semibold mb-1">
                                    Bạn:
                                </div>
                                <div className="text-base sm:text-lg text-gray-200">
                                    {transcript ? (
                                        <span>&quot;{transcript}&quot;</span>
                                    ) : (
                                        <span className="text-gray-500 italic">Hãy nói câu hỏi của bạn...</span>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Bottom Control Bar */}
            <div className="flex items-center justify-center gap-6 w-full max-w-md mx-auto">
                <Tooltip title={isMuted ? 'Bật Microphone' : 'Tắt Microphone'}>
                    <Button
                        type="default"
                        shape="circle"
                        size="large"
                        icon={isMuted ? <AudioMutedOutlined /> : <AudioOutlined />}
                        onClick={toggleMute}
                        disabled={modeState === 'UNSUPPORTED_BROWSER' || isMicrophoneDenied}
                        className={`h-14 w-14 text-xl flex items-center justify-center border-none transition-all ${
                            isMuted
                                ? 'bg-red-950 text-red-400 hover:bg-red-900'
                                : 'bg-white/10 text-white hover:bg-white/20'
                        }`}
                    />
                </Tooltip>

                {(modeState === 'SPEAKING' || modeState === 'PAUSED') && (
                    <Tooltip title={modeState === 'PAUSED' ? 'Tiếp tục phát' : 'Tạm dừng phát'}>
                        <Button
                            type="default"
                            shape="circle"
                            size="large"
                            icon={modeState === 'PAUSED' ? <CaretRightOutlined /> : <PauseOutlined />}
                            onClick={togglePause}
                            className="h-14 w-14 text-xl flex items-center justify-center border-none bg-white/10 text-white hover:bg-white/20 transition-all"
                        />
                    </Tooltip>
                )}

                <Tooltip title="Kết thúc Live Mode">
                    <Button
                        type="primary"
                        danger
                        shape="circle"
                        size="large"
                        icon={<CloseOutlined />}
                        onClick={handleClose}
                        className="h-14 w-14 text-xl flex items-center justify-center shadow-lg bg-red-600 hover:bg-red-700 border-none transition-all"
                    />
                </Tooltip>
            </div>
        </div>
    );
}

import React from 'react';
import Image from 'next/image';

/**
 * Component Logo AIRC
 * Hien thi logo AIRC dang SVG hoac text
 */
interface AIRCLogoProps {
    collapsed?: boolean;
    className?: string;
}

const AIRCLogo: React.FC<AIRCLogoProps> = ({ collapsed = false, className = '' }) => {
    return (
        <div className={`flex items-center justify-center p-4 ${className}`} style={{ height: 64 }}>
            {!collapsed ? (
                <div className="flex items-center gap-2">
                    <div className="relative h-10 w-auto min-w-[40px]">
                        <Image
                            src="/logo_airc.jpg"
                            alt="AIRC Logo"
                            fill
                            className="object-contain"
                            priority
                        />
                    </div>
                    <div className="hidden flex items-center justify-center w-8 h-8 bg-gradient-to-br from-red-600 to-red-800 rounded-lg shadow-sm text-white font-black text-lg">
                        A
                    </div>
                    <span className="text-2xl font-black text-gray-800 tracking-tighter">
                        AIRC <span className="text-red-700">Chat</span>
                    </span>
                </div>
            ) : (
                <div className="flex items-center justify-center relative h-8 w-8">
                    <Image
                        src="/logo_airc.jpg"
                        alt="AIRC"
                        fill
                        className="object-contain rounded-md"
                    />
                </div>
            )}
        </div>
    );
};

export default AIRCLogo;

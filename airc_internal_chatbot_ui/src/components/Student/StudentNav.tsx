'use client';

import React, { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Button, Avatar, Dropdown, MenuProps } from 'antd';
import { UserOutlined, LogoutOutlined, HomeOutlined } from '@ant-design/icons';
import useAuthStore from '@/stores/authStore';

/**
 * Navbar cho Student - Port tu legacy 'Nav' component
 * Su dung Ant Design + Tailwind
 */
const StudentNav: React.FC = () => {
    const router = useRouter();
    const pathname = usePathname();
    const { user, logout } = useAuthStore();
    // const [selectedKey, setSelectedKey] = useState('chat'); // Unused

    // Menu logic
    const handleLogout = () => {
        logout();
        router.push('/login');
    };

    const userMenu: MenuProps['items'] = [
        {
            key: 'profile',
            label: 'Profile',
            icon: <UserOutlined />,
            disabled: true // Placeholder
        },
        {
            type: 'divider',
        },
        {
            key: 'logout',
            label: 'Logout',
            icon: <LogoutOutlined />,
            onClick: handleLogout,
            danger: true
        },
    ];



    const isActive = (href: string) => pathname === href || pathname.startsWith(href + '/');

    return (
        <header className="sticky top-0 z-50 w-full border-b border-neutral-200/70 bg-white/80 backdrop-blur-md">
            <div className="mx-auto flex items-center justify-between px-4 py-3 md:px-6 max-w-7xl">
                {/* Left: Logo */}
                <div className="flex items-center gap-3 cursor-pointer" onClick={() => router.push('/dashboard/chat')}>
                    {/* Placeholder Logo Text if image missing */}
                    <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
                        AIRC
                    </span>
                </div>

                {/* Center: Tabs */}
                <nav className="hidden rounded-full bg-gray-100 px-1 py-1 sm:flex gap-1">
                    <Button
                        type="text"
                        shape="round"
                        className={`px-6 h-10 font-medium ${isActive('/dashboard/chat') ? 'bg-black text-white hover:!bg-black hover:!text-white' : 'text-gray-600 hover:bg-white'}`}
                        onClick={() => router.push('/dashboard/chat')}
                    >
                        Chat
                    </Button>
                </nav>

                {/* Right: User Profile */}
                <div className="flex items-center gap-3">
                    <div className="hidden sm:block text-right">
                        <div className="text-sm font-medium text-gray-900">{user?.full_name || user?.email}</div>
                        <div className="text-xs text-gray-500 capitalize">{user?.role}</div>
                    </div>
                    <Dropdown menu={{ items: userMenu }} placement="bottomRight" arrow>
                        <Avatar
                            size="large"
                            icon={<UserOutlined />}
                            className="cursor-pointer bg-gradient-to-tr from-blue-500 to-cyan-400 hover:opacity-90 transition-opacity"
                        />
                    </Dropdown>
                </div>
            </div>
        </header>
    );
};

export default StudentNav;

'use client';

import React from 'react';
import { Layout, Avatar, Dropdown, MenuProps, Space, Button, theme } from 'antd';
import { UserOutlined, LogoutOutlined, BellOutlined, SettingOutlined } from '@ant-design/icons';
import useAuthStore from '@/stores/authStore';

const { Header } = Layout;

interface HeaderProps {
    collapsed?: boolean;
}

/**
 * Component Header chinh cua ung dung
 * Hien thi User profile (DYNAMIC tu authStore)
 */
const MainHeader: React.FC<HeaderProps> = ({ collapsed }) => {
    const {
        token: { colorBgContainer, colorPrimary },
    } = theme.useToken();

    // Lay thong tin user tu auth store
    const { user, logout } = useAuthStore();

    // Menu dropdown cho user info
    const userMenuItems: MenuProps['items'] = [
        {
            key: 'profile',
            label: 'Thong tin tai khoan',
            icon: <UserOutlined />,
        },
        {
            key: 'settings',
            label: 'Cai dat',
            icon: <SettingOutlined />,
        },
        {
            type: 'divider',
        },
        {
            key: 'logout',
            label: 'Dang xuat',
            icon: <LogoutOutlined />,
            danger: true,
            onClick: () => logout(),
        },
    ];

    return (
        <Header
            style={{
                padding: '0 24px',
                background: colorBgContainer,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                position: 'sticky',
                top: 0,
                zIndex: 1000,
                boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
            }}
        >
            {/* Left side - EMPTY, logo nam o Sidebar */}
            <div className="flex items-center">
                {/* Logo is in Sidebar - do not duplicate here */}
            </div>

            {/* Right side - User Info (DYNAMIC) */}
            <Space size={24}>
                <Button
                    type="text"
                    icon={<BellOutlined style={{ fontSize: '18px' }} />}
                    style={{ borderRadius: '50%', width: 40, height: 40 }}
                />

                <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow>
                    <Space className="cursor-pointer hover:bg-gray-50 py-1 px-2 rounded-lg transition-colors">
                        <Avatar
                            style={{ backgroundColor: colorPrimary }}
                            icon={<UserOutlined />}
                        />
                        <div className="hidden md:block leading-tight">
                            <div className="font-semibold text-sm">{user?.full_name || 'User'}</div>
                            <div className="text-xs text-gray-500 capitalize">
                                {user?.role?.toLowerCase() || 'N/A'}
                            </div>
                        </div>
                    </Space>
                </Dropdown>
            </Space>
        </Header>
    );
};

export default MainHeader;

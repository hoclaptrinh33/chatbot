'use client';

import React, { useState } from 'react';
import { Layout, theme } from 'antd';
import MainSidebar from './Sidebar';
import MainHeader from './Header';
import StudentLayout from '../Student/StudentLayout';
import useAuthStore from '@/stores/authStore';

const { Content } = Layout;

interface MainLayoutProps {
    children: React.ReactNode;
}

/**
 * Main Layout Component
 * Bao gom Sidebar, Header va Content area
 */
const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
    const [collapsed, setCollapsed] = useState(false);
    const [hasHydrated, setHasHydrated] = useState(false);
    const { user } = useAuthStore();
    const {
        token: { borderRadiusLG },
    } = theme.useToken();

    // Wait for auth store to rehydrate before rendering
    React.useEffect(() => {
        const rehydrate = async () => {
            if (typeof window !== 'undefined') {
                await useAuthStore.persist.rehydrate();
                setHasHydrated(true);
            }
        };
        rehydrate();
    }, []);

    // Show loading while hydrating to prevent flash of wrong layout
    if (!hasHydrated) {
        return null; // Or a loader if preferred
    }

    const isInternGuest = user?.role === 'intern_guest';

    // RBAC: Serve separate layout for intern/guest users
    if (isInternGuest) {
        return <StudentLayout>{children}</StudentLayout>;
    }

    return (
            <Layout style={{ height: '100vh', overflow: 'hidden' }}>
            <MainSidebar
                collapsed={collapsed}
                onCollapse={setCollapsed}
            />

            <Layout style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <MainHeader collapsed={collapsed} />

                <Content style={{ margin: '24px 24px', flex: 1, minHeight: 0, overflow: 'hidden' }}>
                    <div
                        style={{
                            padding: 0,
                            height: '100%',
                            background: '#f5f5f5', // Transparent content bg to show cards better
                            borderRadius: borderRadiusLG,
                            overflow: 'auto',
                        }}
                    >
                        {children}
                    </div>
                </Content>
            </Layout>
        </Layout>
    );
};

export default MainLayout;

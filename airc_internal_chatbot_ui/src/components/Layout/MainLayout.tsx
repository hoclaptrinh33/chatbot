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

    const isStudent = user?.role === 'student';

    // RBAC: Serve separate layout for Student
    if (isStudent) {
        return <StudentLayout>{children}</StudentLayout>;
    }

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <MainSidebar
                collapsed={collapsed}
                onCollapse={setCollapsed}
            />

            <Layout>
                <MainHeader collapsed={collapsed} />

                <Content style={{ margin: '24px 24px', minHeight: 280 }}>
                    <div
                        style={{
                            padding: 24,
                            minHeight: '100%',
                            background: '#f5f5f5', // Transparent content bg to show cards better
                            borderRadius: borderRadiusLG,
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

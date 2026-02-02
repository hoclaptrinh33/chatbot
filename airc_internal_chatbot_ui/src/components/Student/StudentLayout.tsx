import React from 'react';
import { Layout } from 'antd';

const { Content } = Layout;

interface StudentLayoutProps {
    children: React.ReactNode;
}

/**
 * Layout rieng cho Student
 * Giong voi layout cu cua chatbot: Nav bar o tren, content o duoi
 */
const StudentLayout: React.FC<StudentLayoutProps> = ({ children }) => {
    return (
        <Layout className="min-h-screen bg-gray-50">
            {/* StudentNav removed. Chat component handles its own header/logout */}
            <Content className="p-0 h-screen">
                {children}
            </Content>
        </Layout>
    );
};

export default StudentLayout;

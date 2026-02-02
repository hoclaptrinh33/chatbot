import type { ThemeConfig } from 'antd';

// Cau hinh theme Ant Design cho AIRC Internal Chatbot
// Mau chu dao: Do AIRC (#D32F2F)
const theme: ThemeConfig = {
    token: {
        // Mau sac chu dao
        colorPrimary: '#D32F2F',         // Do AIRC chinh
        colorInfo: '#1976D2',            // Xanh thong tin (Blue 700)
        colorSuccess: '#388E3C',         // Xanh thanh cong (Green 700)
        colorWarning: '#F57C00',         // Cam canh bao (Orange 700)
        colorError: '#D32F2F',           // Do loi (Red 700)
        colorLink: '#D32F2F',            // Mau link

        // Font chu
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
        fontSize: 14,

        // Bo goc
        borderRadius: 8,

        // Layout
        wireframe: false,
    },
    components: {
        Button: {
            primaryShadow: '0 2px 0 rgba(211, 47, 47, 0.1)', // Shadow nhe mau do
            colorPrimaryHover: '#B71C1C', // Do dam hon khi hover (Red 900)
        },
        Layout: {
            headerBg: '#ffffff',
            bodyBg: '#f5f5f5',
            siderBg: '#ffffff',
        },
        Menu: {
            itemSelectedColor: '#D32F2F',
            itemSelectedBg: '#FFEBEE', // Do nhat (Red 50)
            itemHoverBg: '#FFEBEE',
        },
        Input: {
            activeBorderColor: '#D32F2F',
            hoverBorderColor: '#D32F2F',
        }
    }
};

export default theme;

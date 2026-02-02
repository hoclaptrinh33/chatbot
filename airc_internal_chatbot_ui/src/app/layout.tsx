import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ConfigProvider } from 'antd';
import AntdRegistry from '@/lib/AntdRegistry';
import theme from '@/theme/themeConfig';

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AIRC Internal Chatbot",
  description: "Internal Chatbot for AIRC",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AntdRegistry>
          <ConfigProvider theme={theme}>
            {children}
          </ConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  );
}

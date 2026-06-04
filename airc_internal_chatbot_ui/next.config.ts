import type { NextConfig } from "next";

const coreProxyTarget = process.env.CORE_INTERNAL_URL || "http://localhost:8000";
const authProxyTarget = process.env.AUTH_INTERNAL_URL || "http://localhost:8001";

const nextConfig: NextConfig = {
  /* config options here */
  output: "standalone",
  typescript: {
    ignoreBuildErrors: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${coreProxyTarget}/api/v1/:path*`,
      },
      {
        source: "/api/auth/:path*",
        destination: `${authProxyTarget}/api/auth/:path*`,
      },
      {
        source: "/api/rbac/:path*",
        destination: `${authProxyTarget}/api/rbac/:path*`,
      },
    ];
  },
};

export default nextConfig;

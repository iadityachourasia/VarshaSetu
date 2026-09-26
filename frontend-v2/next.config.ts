import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  async rewrites() {
    const backend = process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/science/:path*", destination: `${backend}/api/science/:path*` }];
  },
};

export default nextConfig;

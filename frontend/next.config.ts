import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Monaco is heavy; keep it client-only via dynamic import in DiffViewer
  reactStrictMode: true,
};

export default nextConfig;

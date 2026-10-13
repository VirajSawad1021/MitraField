import type { NextConfig } from "next";

const API = process.env.MITRA_API ?? "http://localhost:8020";
const dev = process.env.NODE_ENV !== "production";

// Production: a static export served by the FastAPI backend (same origin).
// Development: `next dev` proxies /api and /files to the backend.
const nextConfig: NextConfig = dev
  ? {
      async rewrites() {
        return [
          { source: "/api/:path*", destination: `${API}/api/:path*` },
          { source: "/files/:path*", destination: `${API}/files/:path*` },
        ];
      },
    }
  : { output: "export", trailingSlash: true, images: { unoptimized: true } };

export default nextConfig;

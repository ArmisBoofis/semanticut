import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /** Smaller Docker image: `node server.js` from `.next/standalone` (see frontend/Dockerfile). */
  output: "standalone",
};

export default nextConfig;

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  transpilePackages: ["@llamaindex/agent-app"],
  assetPrefix: process.env.LLAMA_DEPLOY_NEXTJS_ASSET_PREFIX || "",
};

export default nextConfig;

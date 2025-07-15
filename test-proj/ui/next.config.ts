import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  /* config options here */
  basePath: process.env.LLAMA_DEPLOY_NEXTJS_BASE_PATH,
  env: {
    NEXT_PUBLIC_LLAMA_DEPLOY_NEXTJS_DEPLOYMENT_NAME:
      process.env.LLAMA_DEPLOY_NEXTJS_DEPLOYMENT_NAME || "default",
  },
  turbopack: {
    resolveAlias: {
      "@llamaindex/components": path.resolve(
        __dirname,
        "node_modules/@llamaindex/components/src"
      ),
    },
  },
};

export default nextConfig;

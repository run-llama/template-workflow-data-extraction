import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({}) => {
  // Prefer the new NAME env; fall back to deprecated URL_ID for backwards compat
  const deploymentName =
    process.env.LLAMA_DEPLOY_DEPLOYMENT_NAME ||
    process.env.LLAMA_DEPLOY_DEPLOYMENT_URL_ID;
  // If only URL_ID is set, populate NAME for downstream code expecting it
  if (!process.env.LLAMA_DEPLOY_DEPLOYMENT_NAME && process.env.LLAMA_DEPLOY_DEPLOYMENT_URL_ID) {
    process.env.LLAMA_DEPLOY_DEPLOYMENT_NAME = process.env.LLAMA_DEPLOY_DEPLOYMENT_URL_ID;
  }
  const basePath = process.env.LLAMA_DEPLOY_DEPLOYMENT_BASE_PATH;
  const projectId = process.env.LLAMA_DEPLOY_PROJECT_ID;
  const port = process.env.PORT ? Number(process.env.PORT) : 3000;
  const baseUrl = process.env.LLAMA_CLOUD_BASE_URL;
  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: port,
      host: true,
    },
    build: {
      outDir: "dist",
      sourcemap: true,
    },
    base: basePath,
    define: {
      // Primary define uses NAME
      "import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_NAME": JSON.stringify(
        deploymentName
      ),
      // Keep deprecated URL_ID define for downstream consumers that still reference it
      "import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_URL_ID": JSON.stringify(
        process.env.LLAMA_DEPLOY_DEPLOYMENT_URL_ID || deploymentName
      ),
      "import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_BASE_PATH": JSON.stringify(basePath),
      ...(projectId && {
        "import.meta.env.VITE_LLAMA_DEPLOY_PROJECT_ID":
          JSON.stringify(projectId),
      }),
      ...(baseUrl && {
        "import.meta.env.VITE_LLAMA_CLOUD_BASE_URL": JSON.stringify(baseUrl),
      }),
    },
  };
});

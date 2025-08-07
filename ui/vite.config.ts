import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({}) => {
  const deploymentId = process.env.LLAMA_DEPLOY_NEXTJS_DEPLOYMENT_NAME;
  const basePath = `/deployments/${deploymentId}/ui`;
  const projectId = process.env.LLAMA_DEPLOY_PROJECT_ID;

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: 3000,
      host: true,
      hmr: {
        port: 3000,
      },
    },
    build: {
      outDir: "dist",
      sourcemap: true,
    },
    base: basePath,
    define: {
      "import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_NAME":
        JSON.stringify(deploymentId),
      "import.meta.env.VITE_LLAMA_DEPLOY_BASE_PATH": JSON.stringify(basePath),
      ...(projectId && {
        "import.meta.env.VITE_LLAMA_CLOUD_PROJECT_ID":
          JSON.stringify(projectId),
      }),
    },
  };
});

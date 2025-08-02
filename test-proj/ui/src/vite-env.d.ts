/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LLAMA_CLOUD_API_KEY: string;
  readonly VITE_LLAMA_CLOUD_BASE_URL: string;

  // injected from llama_deploy
  readonly LLAMA_DEPLOY_NEXTJS_BASE_PATH: string;
  readonly NEXT_PUBLIC_LLAMA_DEPLOY_DEPLOYMENT_NAME: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

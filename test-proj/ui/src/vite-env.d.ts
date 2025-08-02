/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LLAMA_CLOUD_API_KEY?: string;
  readonly VITE_LLAMA_CLOUD_BASE_URL?: string;

  // injected from llama_deploy
  readonly VITE_LLAMA_DEPLOY_BASE_PATH: string;
  readonly VITE_LLAMA_DEPLOY_DEPLOYMENT_NAME: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

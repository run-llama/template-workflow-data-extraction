/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LLAMA_CLOUD_API_KEY: string;
  readonly VITE_LLAMA_CLOUD_BASE_URL: string;
  readonly VITE_AGENT_NAME: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

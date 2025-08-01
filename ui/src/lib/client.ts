import { client as platformClient } from "@llamaindex/cloud/api";

const platformToken = import.meta.env.VITE_LLAMA_CLOUD_API_KEY;
const apiBaseUrl = import.meta.env.VITE_LLAMA_CLOUD_BASE_URL;

// Configure the platform client
platformClient.setConfig({
  baseUrl: apiBaseUrl,
  headers: {
    ...(platformToken && { authorization: `Bearer ${platformToken}` }),
  },
});

export { platformClient };

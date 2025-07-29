import { client as platformClient } from "@llamaindex/cloud/api";

const platformToken = process.env.NEXT_PUBLIC_LLAMA_CLOUD_API_KEY;
const apiBaseUrl = process.env.NEXT_PUBLIC_LLAMA_CLOUD_BASE_URL;

// Configure the platform client
platformClient.setConfig({
  baseUrl: apiBaseUrl,
  headers: {
    ...(platformToken && { authorization: `Bearer ${platformToken}` }),
  },
});

export { platformClient };

import { client as platformClient } from "@llamaindex/cloud/api";

const platformToken = import.meta.env.VITE_LLAMA_CLOUD_API_KEY;
const apiBaseUrl = import.meta.env.VITE_LLAMA_CLOUD_BASE_URL;
const projectId = import.meta.env.VITE_LLAMA_CLOUD_PROJECT_ID;

// Configure the platform client
platformClient.setConfig({
  baseUrl: apiBaseUrl,
  headers: {
    // optionally use a backend API token scoped to a project. For local development,
    ...(platformToken && { authorization: `Bearer ${platformToken}` }),
    // This header is required for requests to correctly scope to the agent's project
    // when authenticating with a user cookie
    ...(projectId && { "Project-Id": projectId }),
  },
});

export { platformClient };

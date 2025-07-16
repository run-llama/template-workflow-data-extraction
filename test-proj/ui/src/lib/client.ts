import { client as platformClient } from "@llamaindex/cloud/api";

const platformToken = process.env.NEXT_PUBLIC_LLAMA_CLOUD_API_KEY;
const apiBaseUrl = process.env.NEXT_PUBLIC_LLAMA_CLOUD_BASE_URL;

const baseUrl =
  "/deployments/" +
  process.env.NEXT_PUBLIC_LLAMA_DEPLOY_NEXTJS_DEPLOYMENT_NAME +
  "/ui/api/extracted-data";

// Configure the platform client
platformClient.setConfig({
  baseUrl: apiBaseUrl,
  headers: {
    ...(platformToken && { authorization: `Bearer ${platformToken}` }),
  },
});

export { platformClient, baseUrl };

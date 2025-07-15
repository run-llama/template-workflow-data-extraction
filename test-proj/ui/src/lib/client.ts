import { client as platformClient } from "@llamaindex/cloud/api";

const platformToken =
  process.env.NEXT_PUBLIC_LLAMA_CLOUD_API_KEY ||
  process.env.LLAMA_CLOUD_API_KEY;

const baseUrl =
  "/deployments/" +
  process.env.NEXT_PUBLIC_LLAMA_DEPLOY_NEXTJS_DEPLOYMENT_NAME +
  "/ui/api/extracted-data";
const apiUrl = "https://api.cloud.llamaindex.ai";


// Configure the platform client
platformClient.setConfig({
  baseUrl: apiUrl,
  headers: {
    ...(platformToken && { authorization: platformToken }),
  },
});

export { platformClient, apiUrl, baseUrl };

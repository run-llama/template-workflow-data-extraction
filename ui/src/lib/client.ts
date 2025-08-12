import { MySchema } from "@/schemas/MySchema";
import { ExtractedData } from "@llamaindex/cloud/beta/agent";
import { ApiClients } from "@llamaindex/ui";
import {
  createCloudAgentClient,
  createLlamaDeployClient,
  createLlamaDeployConfig,
  cloudApiClient,
} from "@llamaindex/ui";
import { EXTRACTED_DATA_COLLECTION } from "./config";

const platformToken = import.meta.env.VITE_LLAMA_CLOUD_API_KEY;
const apiBaseUrl = import.meta.env.VITE_LLAMA_CLOUD_BASE_URL;
const projectId = import.meta.env.VITE_LLAMA_DEPLOY_PROJECT_ID;

// Configure the platform client
cloudApiClient.setConfig({
  baseUrl: apiBaseUrl,
  headers: {
    // optionally use a backend API token scoped to a project. For local development,
    ...(platformToken && { authorization: `Bearer ${platformToken}` }),
    // This header is required for requests to correctly scope to the agent's project
    // when authenticating with a user cookie
    ...(projectId && { "Project-Id": projectId }),
  },
});

const agentClient = createCloudAgentClient<ExtractedData<MySchema>>({
  baseUrl: apiBaseUrl,
  apiKey: platformToken,
  windowUrl: typeof window !== "undefined" ? window.location.href : undefined,
  collection: EXTRACTED_DATA_COLLECTION,
});

const clients: ApiClients = {
  llamaDeployClient: createLlamaDeployClient(createLlamaDeployConfig()),
  cloudApiClient: cloudApiClient,
  agentDataClient: agentClient,
};

export { clients, agentClient };

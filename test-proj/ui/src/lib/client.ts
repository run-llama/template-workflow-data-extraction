import { MySchema } from "@/schemas/MySchema";
import { ExtractedData } from "llama-cloud-services/beta/agent";
import {
  ApiClients,
  createWorkflowClient,
  createWorkflowConfig,
} from "@llamaindex/ui";
import { createCloudAgentClient, cloudApiClient } from "@llamaindex/ui";
import { AGENT_NAME, EXTRACTED_DATA_COLLECTION } from "./config";

const platformToken = import.meta.env.VITE_LLAMA_CLOUD_API_KEY;
const apiBaseUrl = import.meta.env.VITE_LLAMA_CLOUD_BASE_URL;
const projectId = import.meta.env.VITE_LLAMA_DEPLOY_PROJECT_ID;

// Configure the platform client
cloudApiClient.setConfig({
  ...(apiBaseUrl && { baseUrl: apiBaseUrl }),
  headers: {
    // optionally use a backend API token scoped to a project. For local development,
    ...(platformToken && { authorization: `Bearer ${platformToken}` }),
    // This header is required for requests to correctly scope to the agent's project
    // when authenticating with a user cookie
    ...(projectId && { "Project-Id": projectId }),
  },
});

const agentClient = createCloudAgentClient<ExtractedData<MySchema>>({
  client: cloudApiClient,
  windowUrl: typeof window !== "undefined" ? window.location.href : undefined,
  collection: EXTRACTED_DATA_COLLECTION,
});

const workflowsClient = createWorkflowClient(
  createWorkflowConfig({
    baseUrl: `/deployments/${AGENT_NAME}/`,
  }),
);

const clients: ApiClients = {
  workflowsClient: workflowsClient,
  cloudApiClient: cloudApiClient,
  agentDataClient: agentClient,
};

export { clients, agentClient };

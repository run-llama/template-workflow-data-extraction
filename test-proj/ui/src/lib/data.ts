import { MySchema } from "@/schemas/MySchema";
import {
  AgentClient,
  createAgentDataClient,
  ExtractedData,
} from "@llamaindex/cloud/beta/agent";
import { AGENT_NAME, EXTRACTED_DATA_COLLECTION } from "./config";

export const data: AgentClient<ExtractedData<MySchema>> = createAgentDataClient<
  ExtractedData<MySchema>
>({
  baseUrl: process.env.NEXT_PUBLIC_LLAMA_CLOUD_BASE_URL,
  apiKey: process.env.NEXT_PUBLIC_LLAMA_CLOUD_API_KEY,
  agentUrlId: AGENT_NAME,
  windowUrl: typeof window !== "undefined" ? window.location.href : undefined,
  collection: EXTRACTED_DATA_COLLECTION,
});

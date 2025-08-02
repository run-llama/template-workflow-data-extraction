import { MySchema } from "@/schemas/MySchema";
import {
  AgentClient,
  createAgentDataClient,
  ExtractedData,
} from "@llamaindex/cloud/beta/agent";
import { EXTRACTED_DATA_COLLECTION } from "./config";

export const data: AgentClient<ExtractedData<MySchema>> = createAgentDataClient<
  ExtractedData<MySchema>
>({
  baseUrl: import.meta.env.VITE_LLAMA_CLOUD_BASE_URL,
  apiKey: import.meta.env.VITE_LLAMA_CLOUD_API_KEY,
  windowUrl: typeof window !== "undefined" ? window.location.href : undefined,
  collection: EXTRACTED_DATA_COLLECTION,
});

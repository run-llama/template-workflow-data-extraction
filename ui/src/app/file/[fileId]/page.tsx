import {
  ExtractedDataGrid,
  zodToJsonSchema,
} from "@llamaindex/agent-app/server";
// TODO - import your schema from @/schemas/SchemaName
import { Placeholder } from "@/schemas/Placeholder";

interface PageProps {
  params: Promise<{ fileId: string }>;
}

export default async function FilePage({ params }: PageProps) {
  const { fileId } = await params;
  return (
    <div>
      <ExtractedDataGrid
        fileId={fileId}
        schema={zodToJsonSchema(Placeholder)}
      />
    </div>
  );
}

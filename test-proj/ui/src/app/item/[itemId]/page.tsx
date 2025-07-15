"use client";
import {
  AcceptReject,
  Badge,
  ExtractedDataDisplay,
  FilePreview,
  ProcessingSteps,
  useItemData,
} from "@llamaindex/components/ui";
import { Clock, XCircle } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { InvoiceSchema } from "../../../schemas/InvoiceSchema";
import { useToolbar } from "@/lib/ToolbarContext";
import { useRouter } from "next/navigation";
import { zodToJsonSchema } from "@llamaindex/components/lib";
import { data as dataClient } from "@/lib/data";

export default function ItemPage() {
  const { itemId } = useParams();
  const [isStepsCollapsed, setIsStepsCollapsed] = useState(false);
  const { setButtons } = useToolbar();

  // Use the hook to fetch item data
  const itemHookData = useItemData({
    jsonSchema: zodToJsonSchema(InvoiceSchema, { lastFields: ["line_items"] }),
    itemId: itemId as string,
    isMock: false,
    client: dataClient,
  });

  const router = useRouter();

  useEffect(() => {
    setButtons(() => [
      <div className="ml-auto flex items-center">
        <AcceptReject
          itemData={itemHookData}
          onComplete={() => router.push("/")}
        />
      </div>,
    ]);
    return () => {
      setButtons(() => []);
    };
  }, [itemHookData.data]);

  const {
    item: itemData,
    data,
    setData,
    loading: isLoading,
    error,
  } = itemHookData;

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <Clock className="h-8 w-8 animate-spin mx-auto mb-2" />
          <div className="text-sm text-gray-500">Loading item...</div>
        </div>
      </div>
    );
  }

  if (error || !itemData) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <XCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
          <div className="text-sm text-gray-500">
            Error loading item: {error || "Item not found"}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-gray-50">
      {/* Left Side - File Preview */}
      <div className="w-1/2 border-r border-gray-200 bg-white">
        <div className="h-full p-4 flex flex-col">
          <div className="mb-4 flex-shrink-0">
            <div className="flex items-center justify-between">
              <h1 className="text-lg font-semibold text-gray-900">
                {itemData.data.file_name}
              </h1>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline">
                {itemData.data.status.replace("_", " ")}
              </Badge>
            </div>
          </div>

          <div className="flex-1 border border-gray-200 rounded-lg overflow-hidden">
            {itemData.data.file_id && (
              <FilePreview
                fileId={itemData.data.file_id}
                onBoundingBoxClick={(box, pageNumber) => {
                  console.log(
                    "Bounding box clicked:",
                    box,
                    "on page:",
                    pageNumber
                  );
                }}
              />
            )}
          </div>
        </div>
      </div>

      {/* Right Side - Review Panel */}
      <div className="flex-1 bg-white overflow-y-auto">
        <div className="p-4 space-y-4">
          {/* Processing Steps */}
          {(itemData as any).workflow_events && (
            <ProcessingSteps
              workflowEvents={(itemData as any).workflow_events}
              isCollapsed={isStepsCollapsed}
              onToggle={() => setIsStepsCollapsed(!isStepsCollapsed)}
              title="Workflow Progress"
            />
          )}

          {/* Extracted Data */}
          <ExtractedDataDisplay
            data={(data as Record<string, unknown>) || {}}
            confidence={
              (itemData.data.confidence as Record<string, number>) || {}
            }
            title="Extracted Data"
            onChange={(updatedData) => {
              setData(updatedData as any);
            }}
            jsonSchema={itemHookData.jsonSchema}
          />
        </div>
      </div>
    </div>
  );
}

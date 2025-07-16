"use client";
import {
  AcceptReject,
  ExtractedDataDisplay,
  FilePreview,
  ProcessingSteps,
  useItemData,
} from "@llamaindex/components/ui";
import { Clock, XCircle } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { MySchema } from "../../../schemas/MySchema";
import { useToolbar } from "@/lib/ToolbarContext";
import { useRouter } from "next/navigation";
import { zodToJsonSchema } from "@llamaindex/components/lib";
import { data as dataClient } from "@/lib/data";
import { platformClient } from "@/lib/client";
import { APP_TITLE } from "@/lib/config";

export default function ItemPage() {
  const { itemId } = useParams();
  const [isStepsCollapsed, setIsStepsCollapsed] = useState(false);
  const { setButtons, setBreadcrumbs } = useToolbar();

  // Use the hook to fetch item data
  const itemHookData = useItemData({
    jsonSchema: zodToJsonSchema(MySchema),
    itemId: itemId as string,
    isMock: false,
    client: dataClient,
  });

  const router = useRouter();

  // Update breadcrumb when item data loads
  useEffect(() => {
    const fileName = itemHookData.item?.data?.file_name;
    if (fileName) {
      setBreadcrumbs([
        { label: APP_TITLE, href: "/" },
        {
          label: fileName,
          isCurrentPage: true,
        },
      ]);
    }

    return () => {
      // Reset to default breadcrumb when leaving the page
      setBreadcrumbs([{ label: APP_TITLE, href: "/" }]);
    };
  }, [itemHookData.item?.data?.file_name, setBreadcrumbs]);

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
  }, [itemHookData.data, setButtons]);

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
            client={platformClient}
          />
        )}
      </div>

      {/* Right Side - Review Panel */}
      <div className="flex-1 bg-white h-full overflow-y-auto">
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

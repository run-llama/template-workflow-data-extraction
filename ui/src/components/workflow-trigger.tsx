import {
  Button,
  FileUploader,
  FILE_TYPE_GROUPS,
  FileUploadData,
} from "@llamaindex/ui";
import { Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useWorkflow } from "@llamaindex/chat-ui";
import { toast } from "sonner";

interface UIToast {
  type: `${string}process_file.UIToast`;
  data: {
    level: string;
    message: string;
  };
}

interface FileEvent {
  type: `${string}process_file.FileEvent`;
  data: {
    file_id: string;
  };
}

export default function TriggerFileWorkflow({
  onSuccess = () => {
    window.location.reload();
  },
}: {
  onSuccess?: (result: any) => void;
}) {
  const [deployment, setDeployment] = useState<string>("");
  // Get deployment from path or environment
  useEffect(() => {
    const deploymentFromPath = window.location.pathname.split("/")[2];
    setDeployment(deploymentFromPath);
  }, []);

  // Only create workflow if deployment exists
  const wf = useWorkflow<UIToast | FileEvent>({
    workflow: "process-file",
    deployment: deployment,
    onError(error) {
      console.error("Workflow error:", error);
    },
    onStopEvent(event) {
      onSuccess(event);
    },
  });

  useEffect(() => {
    const lastEvent = wf.events[wf.events.length - 1];
    if (lastEvent?.type.endsWith("process_file.UIToast")) {
      const lastEventData = lastEvent.data as UIToast["data"];
      if (lastEventData.level === "info") {
        toast.info(lastEventData.message);
      } else if (lastEventData.level === "warning") {
        toast.warning(lastEventData.message);
      } else if (lastEventData.level === "error") {
        toast.error(lastEventData.message);
      }
    }
  }, [wf.events.length]);

  const prevStatus = useRef<string>(wf.status);
  useEffect(() => {
    const currentStatus = wf.status;
    const previousStatus = prevStatus.current;
    prevStatus.current = currentStatus;
    if (currentStatus !== "running" && previousStatus === "running") {
      // some sort of bug in the useWorkflow onStopEvent hook
      onSuccess(wf.events[wf.events.length - 1]);
    }
  }, [wf.status]);

  const handleFileUpload = async (data: FileUploadData[]) => {
    const { fileId } = data[0];

    if (fileId) {
      wf.start({
        file_id: fileId,
      });
    } else {
      console.error("No file_id available from upload");
    }
  };

  // If not ready, show loading state
  if (!deployment) {
    return (
      <Button disabled className="cursor-not-allowed">
        <Loader2 className="animate-spin h-5 w-5" />
        Loading...
      </Button>
    );
  }

  return (
    <FileUploader
      title="Process File"
      description="Upload a file to extract information."
      inputFields={[]}
      multiple={false}
      allowedFileTypes={[
        ...FILE_TYPE_GROUPS.IMAGES,
        ...FILE_TYPE_GROUPS.DOCUMENTS,
      ]}
      maxFileSizeBytes={50 * 1000 * 1000} // 50MB
      onSuccess={handleFileUpload}
      isProcessing={wf.status === "running"}
    />
  );
}

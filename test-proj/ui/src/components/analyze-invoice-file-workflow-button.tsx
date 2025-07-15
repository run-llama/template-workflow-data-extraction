"use client";
import { Button } from "@llamaindex/components/ui";
import { Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { JSONValue, useWorkflow } from "@llamaindex/chat-ui";
import { toast } from "sonner";

interface StatusEvent {
  type: "process_file.StatusEvent";
  data: {
    status: string;
  };
}

interface FileEvent {
  type: "process_file.FileEvent";
  data: {
    file_name: string;
    file_type: string;
    file_size: number;
    file_hash: string;
    file: string;
  };
}

export default function TriggerFileWorkflow({
  onSuccess = () => {
    window.location.reload();
  },
}: {
  onSuccess?: (result: any) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [deployment, setDeployment] = useState<string>("");

  // Make sure it only runs on the client
  useEffect(() => {
    const deploymentFromPath = window.location.pathname.split("/")[2];
    setDeployment(deploymentFromPath);
  }, []);

  const clearInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Only create workflow if deployment exists
  const wf = useWorkflow<StatusEvent | FileEvent>({
    workflow: "process-file",
    deployment: deployment,
    onError(error) {
      console.error("Workflow error:", error);
      clearInput();
    },
    onStopEvent(event) {
      clearInput();
      onSuccess(event);
    },
  });

  useEffect(() => {
    const lastEvent = wf.events[wf.events.length - 1];
    if (lastEvent?.type === "process_file.StatusEvent") {
      toast.info(lastEvent.data.status);
    }
  }, [wf.events.length]);

  const handleFileSelect = () => {
    if (wf.status === "running" || !deployment) {
      return;
    }
    fileInputRef.current?.click();
  };

  const validateFileType = (file: File): boolean => {
    const allowedTypes = [
      "image/png",
      "image/jpeg",
      "image/jpg",
      "application/pdf",
    ];
    const allowedExtensions = [".png", ".jpg", ".jpeg", ".pdf"];

    // Check MIME type
    if (allowedTypes.includes(file.type)) {
      return true;
    }

    // Fallback: check file extension (in case MIME type is not set correctly)
    const fileName = file.name.toLowerCase();
    return allowedExtensions.some((ext) => fileName.endsWith(ext));
  };

  const handleFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!validateFileType(file)) {
      toast.error("Please select a PNG, PDF, or JPG file.");
      clearInput();
      return;
    }

    const fileInfo = await getFileInfo(file);
    wf.start({
      file_name: file.name,
      file_type: file.type,
      file_size: file.size,
      file_hash: fileInfo.sha256,
      file: fileInfo.base64,
    });
  };

  // 如果还没准备好，显示加载状态
  if (!deployment) {
    return (
      <Button disabled className="cursor-not-allowed">
        <Loader2 className="animate-spin h-5 w-5" />
        Loading...
      </Button>
    );
  }

  return (
    <>
      <Button
        onClick={handleFileSelect}
        disabled={wf.status === "running"}
        className="cursor-pointer"
      >
        {wf.status === "running" ? (
          <>
            <Loader2 className="animate-spin h-5 w-5" />
            Processing...
          </>
        ) : (
          "Upload File"
        )}
      </Button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".png,.jpg,.jpeg,.pdf"
        onChange={handleFileChange}
        style={{ display: "none" }}
      />
    </>
  );
}

interface FileInfo {
  base64: string;
  sha256: string;
}

/**
 * Serialize the file to a base64 string and a SHA256 hash.
 */
async function getFileInfo(file: File): Promise<FileInfo> {
  const reader = new FileReader();

  // Get base64
  const base64Promise = new Promise<string>((resolve, reject) => {
    reader.onload = (e: ProgressEvent<FileReader>) => {
      const result = e.target?.result;
      if (typeof result === "string") {
        resolve(result.split(",")[1]); // Remove data URL prefix
      } else {
        reject(
          new Error(
            "Failed to read file. Expected string, got " + typeof result
          )
        );
      }
    };
    reader.readAsDataURL(file);
  });

  // Get SHA256
  const sha256Promise = new Promise<string>((resolve, reject) => {
    const fileReader = new FileReader();
    fileReader.onload = async (e: ProgressEvent<FileReader>) => {
      const result = e.target?.result;
      if (result instanceof ArrayBuffer) {
        const hashBuffer = await crypto.subtle.digest("SHA-256", result);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray
          .map((b) => b.toString(16).padStart(2, "0"))
          .join("");
        resolve(hashHex);
      } else {
        reject(new Error("Failed to read file as ArrayBuffer"));
      }
    };
    fileReader.readAsArrayBuffer(file);
  });

  const [base64, sha256] = await Promise.all([base64Promise, sha256Promise]);
  return { base64, sha256 };
}

import {
  ItemCount,
  WorkflowTrigger,
  WorkflowProgressBar,
  ExtractedDataItemGrid,
} from "@llamaindex/ui";
import type { TypedAgentData } from "llama-cloud-services/beta/agent";
import styles from "./HomePage.module.css";
import { useNavigate } from "react-router-dom";
import { agentClient } from "@/lib/client";

const deployment = import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_NAME;

export default function HomePage() {
  const lastMonth = new Date(
    new Date().setMonth(new Date().getMonth() - 1),
  ).toISOString();
  const navigate = useNavigate();
  const goToItem = (item: TypedAgentData) => {
    navigate(`/item/${item.id}`);
  };
  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <div className={styles.grid}>
          <ItemCount
            title="Total Items"
            filter={{ created_at: { gt: lastMonth } }}
            client={agentClient}
          />
          <ItemCount
            title="Reviewed"
            filter={{
              created_at: { gt: lastMonth },
              status: { eq: "approved" },
            }}
            client={agentClient}
          />
          <ItemCount
            title="Needs Review"
            filter={{
              created_at: { gt: lastMonth },
              status: { eq: "pending_review" },
            }}
            client={agentClient}
          />
        </div>
        <div className={styles.commandBar}>
          <WorkflowTrigger
            deployment={deployment}
            workflow="process-file"
            customWorkflowInput={(files) => {
              return {
                file_id: files[0].fileId,
              };
            }}
          />
        </div>
        <WorkflowProgressBar className={styles.progressBar} />
        <ExtractedDataItemGrid
          onRowClick={goToItem}
          builtInColumns={{
            fileName: true,
            status: true,
            createdAt: true,
            itemsToReview: true,
            actions: true,
          }}
        />
      </main>
    </div>
  );
}

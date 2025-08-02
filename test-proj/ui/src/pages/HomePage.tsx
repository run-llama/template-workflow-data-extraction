import { ItemGrid, ItemCount } from "@llamaindex/ui";
import type { TypedAgentData } from "@llamaindex/cloud/beta/agent";
import styles from "./HomePage.module.css";
import { useNavigate } from "react-router-dom";
import TriggerFileWorkflow from "@/components/workflow-trigger";
import { data } from "@/lib/data";

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
            title="Total Documents"
            filter={{ created_at: { gt: lastMonth } }}
            client={data}
          />
          <ItemCount
            title="Reviewed"
            filter={{
              created_at: { gt: lastMonth },
              status: { eq: "approved" },
            }}
            client={data}
          />
          <ItemCount
            title="Needs Review"
            filter={{
              created_at: { gt: lastMonth },
              status: { eq: "pending_review" },
            }}
            client={data}
          />
        </div>
        <div className={styles.commandBar}>
          <TriggerFileWorkflow />
        </div>
        <ItemGrid
          onRowClick={goToItem}
          builtInColumns={{
            fileName: true,
            status: true,
            createdAt: true,
            itemsToReview: true,
            actions: true,
          }}
          client={data}
        />
      </main>
    </div>
  );
}

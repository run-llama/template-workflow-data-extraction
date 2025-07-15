"use client";
import { ItemGrid, ItemCount } from "@llamaindex/components/ui";
import type { TypedAgentData } from "@llamaindex/cloud/beta/agent";
import styles from "./page.module.css";
import { useRouter } from "next/navigation";
import TriggerFileWorkflow from "@/components/analyze-invoice-file-workflow-button";
import { data } from "@/lib/data";

export default function Home() {
  const lastMonth = new Date(
    new Date().setMonth(new Date().getMonth() - 1)
  ).toISOString();
  const router = useRouter();
  const goToItem = (item: TypedAgentData) => {
    router.push(`/item/${item.id}`);
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
          }}
          client={data}
        />
      </main>
    </div>
  );
}

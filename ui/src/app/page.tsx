import { FileCount, FileGrid } from "@llamaindex/agent-app/server";
import styles from "./page.module.css";

export default function Home() {
  const lastMonth = new Date(
    new Date().setMonth(new Date().getMonth() - 1)
  ).toISOString();
  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <div className={styles.grid}>
          <FileCount
            title="Total Documents"
            filter_fields={{ created_at: { gt: lastMonth } }}
            filter_status_counts={{}}
          />
          <FileCount
            title="Reviewed"
            filter_fields={{ created_at: { gt: lastMonth } }}
            filter_status_counts={{ pending_review: { eq: 0 } }}
          />
          <FileCount
            title="Needs Review"
            filter_fields={{ created_at: { gt: lastMonth } }}
            filter_status_counts={{ pending_review: { gt: 0 } }}
          />
        </div>
        <FileGrid
          fileRoute="/file"
          includeColumns={[
            {
              standardColumn: "file_name",
            },
            {
              standardColumn: "status",
            },
            {
              standardColumn: "synced_at",
            },
            {
              standardColumn: "created_at",
            },
          ]}
        />
      </main>
    </div>
  );
}

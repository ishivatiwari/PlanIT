import { SystemStatus } from "@/components/system-status";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Connection status | PlanIT" };

export default function StatusPage() {
  return (
    <>
      <div className="page-intro">
        <span className="eyebrow">Workspace essentials</span>
        <h1>Connection status</h1>
        <p>
          A live look at the services behind this preview. You can check the
          connection again at any time.
        </p>
      </div>
      <SystemStatus />
    </>
  );
}

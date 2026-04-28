import { SessionStatus } from "@/types";

const LABELS: Record<SessionStatus, string> = {
  queued: "Queued",
  processing: "Processing",
  complete: "Complete",
  error: "Error",
};

export function StatusBadge({ status }: { status: SessionStatus }) {
  return (
    <span className={`badge badge-${status}`}>{LABELS[status]}</span>
  );
}

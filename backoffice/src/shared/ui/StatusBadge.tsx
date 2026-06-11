import { Badge } from "@/shared/ui/Badge";
import { ProcessingStatus } from "@/shared/types/backoffice";

const tones: Record<ProcessingStatus, "blue" | "green" | "yellow" | "red"> = {
  pending: "yellow",
  processing: "blue",
  ready: "green",
  failed: "red"
};

export function StatusBadge({ status }: { status: ProcessingStatus }) {
  return <Badge tone={tones[status]}>{status}</Badge>;
}

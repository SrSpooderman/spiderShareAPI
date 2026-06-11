import { useQuery } from "@tanstack/react-query";

import { backofficeService } from "@/shared/api/backofficeService";
import { PageHeader } from "@/shared/ui/PageHeader";

export function WorkerRawLogsPage() {
  const { data = [] } = useQuery({
    queryKey: ["worker-raw-logs"],
    queryFn: backofficeService.getRawLogs
  });

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Worker"
        title="Logs crudos"
        description="Vista secundaria para consola del worker cuando exista fuente de logs configurada."
      />
      <article className="terminal-panel" aria-label="Worker raw logs">
        {data.map((entry) => (
          <code key={`${entry.createdAt}-${entry.line}`}>{entry.line}</code>
        ))}
      </article>
    </section>
  );
}

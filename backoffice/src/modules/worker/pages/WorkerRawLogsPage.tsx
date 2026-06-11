import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { backofficeService } from "@/shared/api/backofficeService";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { PaginationControls } from "@/shared/ui/PaginationControls";
import { QueryPanelState } from "@/shared/ui/QueryPanelState";

const PAGE_SIZE = 100;

export function WorkerRawLogsPage() {
  const [offset, setOffset] = useState(0);
  const { data = [], isError, isLoading } = useQuery({
    queryKey: ["worker-raw-logs", offset],
    queryFn: () => backofficeService.getRawLogs({ limit: PAGE_SIZE, offset })
  });

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Worker"
        title="Logs crudos"
        description="Vista secundaria para consola del worker cuando exista fuente de logs configurada."
      />
      <QueryPanelState
        errorDescription="No se pudieron recuperar las lineas de consola del worker."
        errorTitle="Error cargando logs"
        isError={isError}
        isLoading={isLoading}
        loadingDescription="Consultando logs derivados de eventos del worker."
        loadingTitle="Cargando logs"
      />
      <article className="terminal-panel" aria-label="Worker raw logs">
        {data.map((entry) => (
          <code key={`${entry.createdAt}-${entry.line}`}>{entry.line}</code>
        ))}
        {!isLoading && !isError && !data.length ? (
          <EmptyState title="Sin logs" description="Todavia no hay lineas registradas." />
        ) : null}
      </article>
      <PaginationControls
        itemCount={data.length}
        limit={PAGE_SIZE}
        offset={offset}
        onNext={() => setOffset((current) => current + PAGE_SIZE)}
        onPrevious={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
      />
    </section>
  );
}

import { useQuery } from "@tanstack/react-query";

import { backofficeService } from "@/shared/api/backofficeService";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { QueryPanelState } from "@/shared/ui/QueryPanelState";

export function WorkerQueuePage() {
  const { data = [], isError, isLoading } = useQuery({
    queryKey: ["queue-jobs"],
    queryFn: backofficeService.getQueueJobs
  });

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Worker"
        title="Cola RQ"
        description="Vista operativa de jobs pendientes, activos y fallidos."
      />
      <article className="panel">
        <QueryPanelState
          errorDescription="No se pudo recuperar el estado de la cola RQ."
          errorTitle="Error cargando cola"
          isError={isError}
          isLoading={isLoading}
          loadingDescription="Consultando jobs pendientes, activos y fallidos."
          loadingTitle="Cargando cola"
        />
        <div className="table-shell">
          <table>
            <thead>
              <tr>
                <th>Job</th>
                <th>Video</th>
                <th>Estado</th>
                <th>Intentos</th>
                <th>Encolado</th>
              </tr>
            </thead>
            <tbody>
              {data.map((job) => (
                <tr key={job.id}>
                  <td>{job.id}</td>
                  <td>{job.videoId}</td>
                  <td><Badge tone={job.status === "failed" ? "red" : "blue"}>{job.status}</Badge></td>
                  <td>{job.attempts}</td>
                  <td>{job.enqueuedAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!isLoading && !isError && !data.length ? (
            <EmptyState title="Cola vacia" description="No hay jobs visibles en este momento." />
          ) : null}
        </div>
      </article>
    </section>
  );
}

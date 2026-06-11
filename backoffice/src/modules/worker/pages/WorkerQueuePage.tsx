import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCcw, Trash2 } from "lucide-react";

import { useAuth } from "@/modules/auth/AuthContext";
import { backofficeService } from "@/shared/api/backofficeService";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { QueryPanelState } from "@/shared/ui/QueryPanelState";

export function WorkerQueuePage() {
  const queryClient = useQueryClient();
  const { isSuperAdmin } = useAuth();
  const { data = [], isError, isLoading } = useQuery({
    queryKey: ["queue-jobs"],
    queryFn: backofficeService.getQueueJobs
  });
  const requeueJob = useMutation({
    mutationFn: backofficeService.requeueJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["queue-jobs"] });
      queryClient.invalidateQueries({ queryKey: ["audit"] });
      queryClient.invalidateQueries({ queryKey: ["worker-events"] });
    }
  });
  const deleteJob = useMutation({
    mutationFn: backofficeService.deleteJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["queue-jobs"] });
      queryClient.invalidateQueries({ queryKey: ["audit"] });
    }
  });
  const clearFailedJobs = useMutation({
    mutationFn: backofficeService.clearFailedJobs,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["queue-jobs"] });
      queryClient.invalidateQueries({ queryKey: ["audit"] });
    }
  });

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Worker"
        title="Cola RQ"
        description="Vista operativa de jobs pendientes, activos y fallidos."
        actions={
          isSuperAdmin ? (
            <button
              className="button danger"
              disabled={clearFailedJobs.isPending}
              onClick={() => clearFailedJobs.mutate()}
              type="button"
            >
              <Trash2 size={16} />
              Limpiar fallidos
            </button>
          ) : null
        }
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
                {isSuperAdmin ? <th className="align-right">Acciones</th> : null}
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
                  {isSuperAdmin ? (
                    <td className="align-right">
                      <button
                        className="button ghost"
                        disabled={requeueJob.isPending}
                        onClick={() => requeueJob.mutate(job.id)}
                        title="Reencolar job"
                        type="button"
                      >
                        <RefreshCcw size={15} />
                      </button>
                      <button
                        className="button ghost"
                        disabled={deleteJob.isPending}
                        onClick={() => deleteJob.mutate(job.id)}
                        title="Eliminar job"
                        type="button"
                      >
                        <Trash2 size={15} />
                      </button>
                    </td>
                  ) : null}
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

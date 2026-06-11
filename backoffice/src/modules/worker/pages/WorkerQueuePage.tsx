import { useQuery } from "@tanstack/react-query";

import { backofficeService } from "@/shared/api/backofficeService";
import { Badge } from "@/shared/ui/Badge";
import { PageHeader } from "@/shared/ui/PageHeader";

export function WorkerQueuePage() {
  const { data = [] } = useQuery({
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
        </div>
      </article>
    </section>
  );
}

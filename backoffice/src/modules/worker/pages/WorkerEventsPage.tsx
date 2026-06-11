import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { backofficeService } from "@/shared/api/backofficeService";
import { Badge } from "@/shared/ui/Badge";
import { PageHeader } from "@/shared/ui/PageHeader";

export function WorkerEventsPage() {
  const { data = [] } = useQuery({
    queryKey: ["worker-events"],
    queryFn: backofficeService.getWorkerEvents
  });

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Worker"
        title="Eventos"
        description="Eventos estructurados del worker para timeline, diagnostico y busqueda."
      />
      <article className="panel">
        <div className="toolbar">
          <input aria-label="Buscar eventos" placeholder="Buscar evento, video o job" />
          <select aria-label="Filtrar nivel">
            <option>Todos los niveles</option>
            <option>info</option>
            <option>warning</option>
            <option>error</option>
          </select>
        </div>
        <div className="table-shell">
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Nivel</th>
                <th>Evento</th>
                <th>Video</th>
                <th>Job</th>
                <th>Mensaje</th>
              </tr>
            </thead>
            <tbody>
              {data.map((event) => (
                <tr key={event.id}>
                  <td>{event.createdAt}</td>
                  <td><Badge tone={event.level === "error" ? "red" : "green"}>{event.level}</Badge></td>
                  <td>{event.eventType}</td>
                  <td>{event.videoId ? <Link to={`/videos/${event.videoId}`}>{event.videoId}</Link> : "-"}</td>
                  <td>{event.jobId ?? "-"}</td>
                  <td>{event.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}

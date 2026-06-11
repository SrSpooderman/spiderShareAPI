import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { backofficeService } from "@/shared/api/backofficeService";
import { WorkerEvent } from "@/shared/types/backoffice";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { PaginationControls } from "@/shared/ui/PaginationControls";
import { QueryPanelState } from "@/shared/ui/QueryPanelState";

const PAGE_SIZE = 50;

export function WorkerEventsPage() {
  const [search, setSearch] = useState("");
  const [level, setLevel] = useState<WorkerEvent["level"] | "">("");
  const [offset, setOffset] = useState(0);
  const { data = [], isError, isLoading } = useQuery({
    queryKey: ["worker-events", level, offset],
    queryFn: () =>
      backofficeService.getWorkerEvents({
        level: level || undefined,
        limit: PAGE_SIZE,
        offset
      })
  });
  const visibleEvents = search
    ? data.filter((event) =>
        [event.eventType, event.message, event.videoId, event.jobId]
          .filter(Boolean)
          .some((value) => value?.toLowerCase().includes(search.toLowerCase()))
      )
    : data;

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Worker"
        title="Eventos"
        description="Eventos estructurados del worker para timeline, diagnostico y busqueda."
      />
      <article className="panel">
        <div className="toolbar">
          <input
            aria-label="Buscar eventos"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar evento, video o job"
            value={search}
          />
          <select
            aria-label="Filtrar nivel"
            onChange={(event) => {
              setLevel(event.target.value as WorkerEvent["level"] | "");
              setOffset(0);
            }}
            value={level}
          >
            <option value="">Todos los niveles</option>
            <option value="info">info</option>
            <option value="warning">warning</option>
            <option value="error">error</option>
          </select>
        </div>
        <QueryPanelState
          errorDescription="No se pudieron recuperar los eventos del worker."
          errorTitle="Error cargando eventos"
          isError={isError}
          isLoading={isLoading}
          loadingDescription="Consultando eventos estructurados del worker."
          loadingTitle="Cargando eventos"
        />
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
              {visibleEvents.map((event) => (
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
          {!isLoading && !isError && !visibleEvents.length ? (
            <EmptyState title="Sin eventos" description="No hay eventos para los filtros actuales." />
          ) : null}
        </div>
        <PaginationControls
          itemCount={data.length}
          limit={PAGE_SIZE}
          offset={offset}
          onNext={() => setOffset((current) => current + PAGE_SIZE)}
          onPrevious={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
        />
      </article>
    </section>
  );
}

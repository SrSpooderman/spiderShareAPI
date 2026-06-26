import { useQuery } from "@tanstack/react-query";
import type { Dispatch, SetStateAction } from "react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { backofficeService } from "@/shared/api/backofficeService";
import { formatDateTime } from "@/shared/formatters/dateTime";
import { WorkerEvent } from "@/shared/types/backoffice";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { PaginationControls } from "@/shared/ui/PaginationControls";
import { QueryPanelState } from "@/shared/ui/QueryPanelState";

const PAGE_SIZE = 100;

function levelTone(level: WorkerEvent["level"]): "green" | "yellow" | "red" {
  return level === "error" ? "red" : level === "warning" ? "yellow" : "green";
}

export function WorkerRawLogsPage() {
  const [search, setSearch] = useState("");
  const [level, setLevel] = useState<WorkerEvent["level"] | "">("");
  const [eventType, setEventType] = useState("");
  const [workerName, setWorkerName] = useState("");
  const [videoId, setVideoId] = useState("");
  const [jobId, setJobId] = useState("");
  const [createdFrom, setCreatedFrom] = useState("");
  const [createdTo, setCreatedTo] = useState("");
  const [offset, setOffset] = useState(0);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const filters = { search, level: level || undefined, eventType, workerName, videoId, jobId, createdFrom, createdTo, limit: PAGE_SIZE, offset };
  const { data = [], isError, isLoading, refetch } = useQuery({
    queryKey: ["worker-event-console", filters],
    queryFn: () => backofficeService.getWorkerEvents(filters)
  });

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = window.setInterval(() => void refetch(), 10_000);
    return () => window.clearInterval(interval);
  }, [autoRefresh, refetch]);

  function changeFilter<T extends string>(setter: Dispatch<SetStateAction<T>>, value: T) {
    setter(value);
    setOffset(0);
  }

  return (
    <section className="stack">
      <PageHeader eyebrow="Worker" title="Consola de eventos" description="Eventos estructurados del worker, con filtros y detalle operativo." actions={<button className="button ghost" onClick={() => setAutoRefresh((enabled) => !enabled)} type="button">{autoRefresh ? "Pausar actualización" : "Actualizar cada 10 s"}</button>} />
      <article className="panel">
        <div className="toolbar event-console-filters">
          <input aria-label="Buscar eventos" placeholder="Texto en evento o mensaje" value={search} onChange={(event) => changeFilter(setSearch, event.target.value)} />
          <select aria-label="Filtrar nivel" value={level} onChange={(event) => changeFilter(setLevel, event.target.value as WorkerEvent["level"] | "")}><option value="">Todos los niveles</option><option value="info">info</option><option value="warning">warning</option><option value="error">error</option></select>
          <input aria-label="Filtrar tipo de evento" placeholder="Tipo de evento" value={eventType} onChange={(event) => changeFilter(setEventType, event.target.value)} />
          <input aria-label="Filtrar worker" placeholder="Worker" value={workerName} onChange={(event) => changeFilter(setWorkerName, event.target.value)} />
          <input aria-label="Filtrar video" placeholder="Video ID" value={videoId} onChange={(event) => changeFilter(setVideoId, event.target.value)} />
          <input aria-label="Filtrar job" placeholder="Job ID" value={jobId} onChange={(event) => changeFilter(setJobId, event.target.value)} />
          <input aria-label="Desde" title="Desde" type="datetime-local" value={createdFrom} onChange={(event) => changeFilter(setCreatedFrom, event.target.value)} />
          <input aria-label="Hasta" title="Hasta" type="datetime-local" value={createdTo} onChange={(event) => changeFilter(setCreatedTo, event.target.value)} />
        </div>
        <QueryPanelState errorDescription="No se pudieron recuperar los eventos del worker." errorTitle="Error cargando consola" isError={isError} isLoading={isLoading} loadingDescription="Consultando eventos estructurados del worker." loadingTitle="Cargando consola" />
        <div className="table-shell">
          <table>
            <thead><tr><th>Fecha</th><th>Nivel</th><th>Evento</th><th>Worker</th><th>Video</th><th>Job</th><th>Mensaje / metadata</th></tr></thead>
            <tbody>{data.map((event) => <tr key={event.id}><td>{formatDateTime(event.createdAt)}</td><td><Badge tone={levelTone(event.level)}>{event.level}</Badge></td><td>{event.eventType}</td><td>{event.workerName}</td><td>{event.videoId ? <Link to={`/videos/${event.videoId}`}>{event.videoId}</Link> : "-"}</td><td>{event.jobId ?? "-"}</td><td><div>{event.message}</div>{event.metadata ? <details className="event-metadata"><summary>metadata</summary><pre>{JSON.stringify(event.metadata, null, 2)}</pre></details> : null}</td></tr>)}</tbody>
          </table>
          {!isLoading && !isError && !data.length ? <EmptyState title="Sin eventos" description="No hay eventos para los filtros seleccionados." /> : null}
        </div>
        <PaginationControls itemCount={data.length} limit={PAGE_SIZE} offset={offset} onNext={() => setOffset((current) => current + PAGE_SIZE)} onPrevious={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))} />
      </article>
    </section>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RotateCcw } from "lucide-react";
import { useParams } from "react-router-dom";

import { backofficeService } from "@/shared/api/backofficeService";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { StatusBadge } from "@/shared/ui/StatusBadge";

export function VideoDetailPage() {
  const { videoId = "" } = useParams();
  const queryClient = useQueryClient();
  const { data: video } = useQuery({
    queryKey: ["video", videoId],
    queryFn: () => backofficeService.getVideo(videoId),
    enabled: Boolean(videoId)
  });
  const { data: events = [] } = useQuery({
    queryKey: ["worker-events"],
    queryFn: backofficeService.getWorkerEvents
  });
  const retry = useMutation({
    mutationFn: () => backofficeService.retryVideo(videoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["video", videoId] })
  });

  const videoEvents = events.filter((event) => event.videoId === videoId);

  if (!video) {
    return <EmptyState title="Cargando video" description="Recuperando detalle operativo." />;
  }

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Detalle video"
        title={video.title}
        description={`Owner: ${video.ownerUsername}`}
        actions={
          video.processingStatus !== "ready" ? (
            <button className="button primary" onClick={() => retry.mutate()}>
              <RotateCcw size={16} />
              Reintentar
            </button>
          ) : null
        }
      />

      <div className="content-grid two">
        <article className="panel">
          <div className="panel-header">
            <h2>Estado</h2>
            <StatusBadge status={video.processingStatus} />
          </div>
          <dl className="description-list">
            <div><dt>Archivo</dt><dd>{video.originalFilename}</dd></div>
            <div><dt>Resolucion</dt><dd>{video.width && video.height ? `${video.width}x${video.height}` : "-"}</dd></div>
            <div><dt>Duracion</dt><dd>{video.durationSeconds ? `${video.durationSeconds}s` : "-"}</dd></div>
            <div><dt>Thumbnail</dt><dd>{video.thumbnailPath ?? "-"}</dd></div>
          </dl>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>Ultimo error</h2>
          </div>
          {video.latestProcessingError ? (
            <dl className="description-list">
              <div><dt>Intento</dt><dd>{video.latestProcessingError.attempt}</dd></div>
              <div><dt>Tipo</dt><dd>{video.latestProcessingError.errorType}</dd></div>
              <div><dt>Job</dt><dd>{video.latestProcessingError.jobId ?? "-"}</dd></div>
              <div><dt>Mensaje</dt><dd>{video.latestProcessingError.errorMessage}</dd></div>
            </dl>
          ) : (
            <EmptyState title="Sin errores" description="No hay fallos registrados para este video." />
          )}
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h2>Variantes</h2>
        </div>
        <div className="variant-list">
          {video.variants.length ? (
            video.variants.map((variant) => (
              <div className="variant-row" key={variant.type}>
                <strong>{variant.type}</strong>
                <Badge>{variant.codec}</Badge>
                <span>{variant.width}x{variant.height}</span>
                <span>{Math.round(variant.sizeBytes / 1024 / 1024)} MB</span>
              </div>
            ))
          ) : (
            <EmptyState title="Sin variantes" description="El video aun no tiene salidas procesadas." />
          )}
        </div>
      </article>

      <article className="panel">
        <div className="panel-header">
          <h2>Timeline worker</h2>
        </div>
        <div className="timeline">
          {videoEvents.map((event) => (
            <div className="timeline-item" key={event.id}>
              <span className={`status-dot ${event.level === "error" ? "bad" : "ok"}`} />
              <div>
                <strong>{event.eventType}</strong>
                <p>{event.message}</p>
                <small>{event.createdAt}</small>
              </div>
            </div>
          ))}
          {!videoEvents.length ? (
            <EmptyState title="Sin eventos" description="Todavia no hay eventos del worker para este video." />
          ) : null}
        </div>
      </article>
    </section>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "@/modules/auth/AuthContext";
import { backofficeService } from "@/shared/api/backofficeService";
import { ProcessingStatus, VideoListFilters } from "@/shared/types/backoffice";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { PaginationControls } from "@/shared/ui/PaginationControls";
import { QueryPanelState } from "@/shared/ui/QueryPanelState";
import { StatusBadge } from "@/shared/ui/StatusBadge";

const PAGE_SIZE = 25;

export function VideoListPage() {
  const queryClient = useQueryClient();
  const { isSuperAdmin } = useAuth();
  const [title, setTitle] = useState("");
  const [owner, setOwner] = useState("");
  const [status, setStatus] = useState<ProcessingStatus | "">("");
  const [visibility, setVisibility] = useState<"public" | "registered" | "">("");
  const [sortBy, setSortBy] = useState<NonNullable<VideoListFilters["sortBy"]>>("created_at");
  const [sortDirection, setSortDirection] = useState<NonNullable<VideoListFilters["sortDirection"]>>("desc");
  const [offset, setOffset] = useState(0);

  const filters: VideoListFilters = {
    title,
    owner,
    status: status || undefined,
    visibility: visibility || undefined,
    sortBy,
    sortDirection,
    limit: PAGE_SIZE,
    offset
  };

  const { data = [], isError, isLoading } = useQuery({
    queryKey: ["videos", filters],
    queryFn: () => backofficeService.getVideos(filters)
  });

  const deleteVideo = useMutation({
    mutationFn: backofficeService.deleteVideo,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["videos"] })
  });

  function resetOffset() {
    setOffset(0);
  }

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Contenido"
        title="Videos"
        description="Listado operativo con filtros, paginacion y acciones disponibles segun permisos."
      />

      <article className="panel">
        <div className="toolbar">
          <input
            aria-label="Buscar por titulo"
            onChange={(event) => {
              setTitle(event.target.value);
              resetOffset();
            }}
            placeholder="Titulo"
            value={title}
          />
          <input
            aria-label="Buscar por owner"
            onChange={(event) => {
              setOwner(event.target.value);
              resetOffset();
            }}
            placeholder="Owner"
            value={owner}
          />
          <select
            aria-label="Filtrar estado"
            onChange={(event) => {
              setStatus(event.target.value as ProcessingStatus | "");
              resetOffset();
            }}
            value={status}
          >
            <option value="">Todos los estados</option>
            <option value="pending">pending</option>
            <option value="processing">processing</option>
            <option value="ready">ready</option>
            <option value="failed">failed</option>
          </select>
          <select
            aria-label="Filtrar visibilidad"
            onChange={(event) => {
              setVisibility(event.target.value as "public" | "registered" | "");
              resetOffset();
            }}
            value={visibility}
          >
            <option value="">Todas las visibilidades</option>
            <option value="public">public</option>
            <option value="registered">registered</option>
          </select>
          <select
            aria-label="Ordenar por"
            onChange={(event) => {
              setSortBy(event.target.value as NonNullable<VideoListFilters["sortBy"]>);
              resetOffset();
            }}
            value={sortBy}
          >
            <option value="created_at">Alta</option>
            <option value="source_created_at">Fecha origen</option>
            <option value="updated_at">Actualizacion</option>
            <option value="title">Titulo</option>
            <option value="favorite_count">Favoritos</option>
            <option value="duration_seconds">Duracion</option>
          </select>
          <select
            aria-label="Direccion de orden"
            onChange={(event) => {
              setSortDirection(event.target.value as NonNullable<VideoListFilters["sortDirection"]>);
              resetOffset();
            }}
            value={sortDirection}
          >
            <option value="desc">Descendente</option>
            <option value="asc">Ascendente</option>
          </select>
        </div>
        <QueryPanelState
          errorDescription="No se pudo recuperar el listado administrativo de videos."
          errorTitle="Error cargando videos"
          isError={isError}
          isLoading={isLoading}
          loadingDescription="Consultando videos con los filtros seleccionados."
          loadingTitle="Cargando videos"
        />
        <div className="table-shell">
          <table>
            <thead>
              <tr>
                <th>Titulo</th>
                <th>Owner</th>
                <th>Estado</th>
                <th>Visibilidad</th>
                <th>Duracion</th>
                <th>Ultimo error</th>
                <th className="align-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {data.map((video) => (
                <tr key={video.id}>
                  <td>{video.title}</td>
                  <td>{video.ownerUsername}</td>
                  <td><StatusBadge status={video.processingStatus} /></td>
                  <td><Badge>{video.visibility}</Badge></td>
                  <td>{video.durationSeconds ? `${video.durationSeconds}s` : "-"}</td>
                  <td>{video.latestProcessingError?.errorType ?? "-"}</td>
                  <td className="align-right">
                    <Link className="button ghost" to={`/videos/${video.id}`}>
                      Abrir
                    </Link>
                    {isSuperAdmin ? (
                      <button
                        className="button ghost"
                        disabled={deleteVideo.isPending}
                        onClick={() => deleteVideo.mutate(video.id)}
                        title="Borrar video"
                        type="button"
                      >
                        <Trash2 size={15} />
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!isLoading && !isError && !data.length ? (
            <EmptyState title="Sin videos" description="No hay videos para los filtros actuales." />
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

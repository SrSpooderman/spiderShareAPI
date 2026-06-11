import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { backofficeService } from "@/shared/api/backofficeService";
import { Badge } from "@/shared/ui/Badge";
import { PageHeader } from "@/shared/ui/PageHeader";
import { StatusBadge } from "@/shared/ui/StatusBadge";

export function VideoListPage() {
  const { data = [] } = useQuery({
    queryKey: ["videos"],
    queryFn: backofficeService.getVideos
  });

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Contenido"
        title="Videos"
        description="Listado operativo preparado para filtros por estado, owner, fecha y titulo."
      />

      <article className="panel">
        <div className="toolbar">
          <input aria-label="Buscar videos" placeholder="Buscar por titulo u owner" />
          <select aria-label="Filtrar estado">
            <option>Todos los estados</option>
            <option>pending</option>
            <option>processing</option>
            <option>ready</option>
            <option>failed</option>
          </select>
        </div>
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
                <th />
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
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}

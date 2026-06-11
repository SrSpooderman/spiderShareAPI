import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { backofficeService } from "@/shared/api/backofficeService";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { StatusBadge } from "@/shared/ui/StatusBadge";

export function UserDetailPage() {
  const { userId = "" } = useParams();
  const { data: user, isError, isLoading } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => backofficeService.getUser(userId),
    enabled: Boolean(userId)
  });

  if (!user) {
    return (
      <EmptyState
        title={isError ? "No se pudo cargar el usuario" : "Cargando usuario"}
        description={
          isError
            ? "El usuario no existe o no tienes permisos para consultar este detalle."
            : isLoading
              ? "Recuperando actividad y conteos."
              : "No hay detalle disponible para este usuario."
        }
      />
    );
  }

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Detalle usuario"
        title={user.username}
        description={user.displayName ?? "Sin nombre visible configurado."}
      />

      <div className="content-grid two">
        <article className="panel">
          <div className="panel-header">
            <h2>Cuenta</h2>
            <Badge tone={user.isActive ? "green" : "red"}>{user.isActive ? "active" : "inactive"}</Badge>
          </div>
          <dl className="description-list">
            <div><dt>Rol</dt><dd><Badge tone={user.role === "super_admin" ? "blue" : "neutral"}>{user.role}</Badge></dd></div>
            <div><dt>Videos</dt><dd>{user.videoCount}</dd></div>
            <div><dt>Ultimo login</dt><dd>{user.lastLoginAt ?? "-"}</dd></div>
            <div><dt>Creado</dt><dd>{user.createdAt}</dd></div>
            <div><dt>Actualizado</dt><dd>{user.updatedAt}</dd></div>
          </dl>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>Acciones</h2>
          </div>
          <EmptyState
            title="Acciones no conectadas"
            description="Activar, desactivar y cambiar rol quedan pendientes para conectar reglas de permisos y auditoria especifica."
          />
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h2>Videos recientes</h2>
        </div>
        <div className="table-shell">
          <table>
            <thead>
              <tr>
                <th>Titulo</th>
                <th>Estado</th>
                <th>Visibilidad</th>
                <th>Creado</th>
                <th className="align-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {user.recentVideos.map((video) => (
                <tr key={video.id}>
                  <td>{video.title}</td>
                  <td><StatusBadge status={video.processingStatus} /></td>
                  <td><Badge>{video.visibility}</Badge></td>
                  <td>{video.createdAt}</td>
                  <td className="align-right">
                    <Link className="button ghost" to={`/videos/${video.id}`}>
                      Abrir
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!user.recentVideos.length ? (
            <EmptyState title="Sin videos" description="Este usuario no tiene videos recientes." />
          ) : null}
        </div>
      </article>
    </section>
  );
}

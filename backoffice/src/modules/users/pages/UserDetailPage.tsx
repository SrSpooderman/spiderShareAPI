import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "@/modules/auth/AuthContext";
import { backofficeService } from "@/shared/api/backofficeService";
import { UserRole } from "@/shared/types/backoffice";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { StatusBadge } from "@/shared/ui/StatusBadge";

export function UserDetailPage() {
  const { userId = "" } = useParams();
  const queryClient = useQueryClient();
  const { isSuperAdmin, user: currentUser } = useAuth();
  const { data: user, isError, isLoading } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => backofficeService.getUser(userId),
    enabled: Boolean(userId)
  });
  const updateUser = useMutation({
    mutationFn: (input: { role?: Exclude<UserRole, "super_admin">; isActive?: boolean }) =>
      backofficeService.updateUser(userId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user", userId] });
      queryClient.invalidateQueries({ queryKey: ["users"] });
      queryClient.invalidateQueries({ queryKey: ["audit"] });
    }
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

  const canManageUser =
    isSuperAdmin && currentUser?.id !== user.id && user.role !== "super_admin";

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
            <div><dt>Origen</dt><dd><Badge tone={user.authProvider === "oidc" ? "blue" : "neutral"}>{user.authProvider}</Badge></dd></div>
            {user.authProvider === "oidc" ? (
              <>
                <div><dt>Email OIDC</dt><dd>{user.oidcEmail ?? "-"}</dd></div>
                <div><dt>Nombre OIDC</dt><dd>{user.oidcName ?? "-"}</dd></div>
                <div><dt>Sub OIDC</dt><dd>{user.oidcSubject ?? "-"}</dd></div>
                <div><dt>Grupos OIDC</dt><dd>{user.oidcGroups.length ? user.oidcGroups.join(", ") : "-"}</dd></div>
              </>
            ) : null}
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
          {canManageUser ? (
            <div className="action-list">
              <label className="field">
                <span>Rol</span>
                <select
                  disabled={updateUser.isPending}
                  onChange={(event) => {
                    const nextRole = event.target.value as Exclude<UserRole, "super_admin">;
                    if (nextRole !== user.role) {
                      updateUser.mutate({ role: nextRole });
                    }
                  }}
                  value={user.role === "super_admin" ? "admin" : user.role}
                >
                  <option value="user">user</option>
                  <option value="admin">admin</option>
                </select>
              </label>
              <button
                className={user.isActive ? "button danger" : "button primary"}
                disabled={updateUser.isPending}
                onClick={() => updateUser.mutate({ isActive: !user.isActive })}
                type="button"
              >
                {user.isActive ? "Desactivar usuario" : "Activar usuario"}
              </button>
            </div>
          ) : (
            <EmptyState
              title="Sin acciones disponibles"
              description="No puedes modificar este usuario desde tu sesion actual."
            />
          )}
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

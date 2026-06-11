import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { backofficeService } from "@/shared/api/backofficeService";
import { UserRole } from "@/shared/types/backoffice";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { QueryPanelState } from "@/shared/ui/QueryPanelState";

export function UserListPage() {
  const [username, setUsername] = useState("");
  const [role, setRole] = useState<UserRole | "">("");
  const [isActive, setIsActive] = useState<"true" | "false" | "">("");
  const filters = {
    username,
    role: role || undefined,
    isActive: isActive === "" ? undefined : isActive === "true"
  };

  const { data = [], isError, isLoading } = useQuery({
    queryKey: ["users", filters],
    queryFn: () => backofficeService.getUsers(filters)
  });

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Identidad"
        title="Usuarios"
        description="Gestion operativa de usuarios, roles y estado de cuenta."
      />
      <article className="panel">
        <div className="toolbar">
          <input
            aria-label="Buscar usuario"
            onChange={(event) => setUsername(event.target.value)}
            placeholder="Username"
            value={username}
          />
          <select
            aria-label="Filtrar rol"
            onChange={(event) => setRole(event.target.value as UserRole | "")}
            value={role}
          >
            <option value="">Todos los roles</option>
            <option value="user">user</option>
            <option value="admin">admin</option>
            <option value="super_admin">super_admin</option>
          </select>
          <select
            aria-label="Filtrar estado"
            onChange={(event) => setIsActive(event.target.value as "true" | "false" | "")}
            value={isActive}
          >
            <option value="">Todos los estados</option>
            <option value="true">active</option>
            <option value="false">inactive</option>
          </select>
        </div>
        <QueryPanelState
          errorDescription="No se pudo consultar el listado administrativo de usuarios."
          errorTitle="Error cargando usuarios"
          isError={isError}
          isLoading={isLoading}
          loadingDescription="Consultando usuarios con los filtros seleccionados."
          loadingTitle="Cargando usuarios"
        />
        <div className="table-shell">
          <table>
            <thead>
              <tr>
                <th>Username</th>
                <th>Nombre</th>
                <th>Rol</th>
                <th>Estado</th>
                <th>Videos</th>
                <th className="align-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {data.map((user) => (
                <tr key={user.id}>
                  <td>{user.username}</td>
                  <td>{user.displayName ?? "-"}</td>
                  <td><Badge tone={user.role === "super_admin" ? "blue" : "neutral"}>{user.role}</Badge></td>
                  <td><Badge tone={user.isActive ? "green" : "red"}>{user.isActive ? "active" : "inactive"}</Badge></td>
                  <td>{user.videoCount}</td>
                  <td className="align-right">
                    <Link className="button ghost" to={`/users/${user.id}`}>
                      Abrir
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!isLoading && !isError && !data.length ? (
            <EmptyState title="Sin usuarios" description="No hay usuarios para los filtros actuales." />
          ) : null}
        </div>
      </article>
    </section>
  );
}

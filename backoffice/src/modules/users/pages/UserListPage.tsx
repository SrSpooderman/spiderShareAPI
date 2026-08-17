import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { backofficeService } from "@/shared/api/backofficeService";
import { useAuth } from "@/modules/auth/AuthContext";
import { UserCreateInput, UserRole } from "@/shared/types/backoffice";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { QueryPanelState } from "@/shared/ui/QueryPanelState";

export function UserListPage() {
  const { user: currentUser } = useAuth();
  const [username, setUsername] = useState("");
  const [role, setRole] = useState<UserRole | "">("");
  const [isActive, setIsActive] = useState<"true" | "false" | "">("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [newUser, setNewUser] = useState<UserCreateInput>({
    username: "",
    password: "",
    role: "user"
  });
  const queryClient = useQueryClient();
  const filters = {
    username,
    role: role || undefined,
    isActive: isActive === "" ? undefined : isActive === "true"
  };

  const { data = [], isError, isLoading } = useQuery({
    queryKey: ["users", filters],
    queryFn: () => backofficeService.getUsers(filters)
  });
  const createUser = useMutation({
    mutationFn: backofficeService.createUser,
    onSuccess: async () => {
      setNewUser({ username: "", password: "", role: "user" });
      setCreateError(null);
      setShowCreateForm(false);
      await queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: () => setCreateError("No se pudo crear el usuario. Revisa los datos e inténtalo de nuevo.")
  });

  function submitCreateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreateError(null);
    createUser.mutate(newUser);
  }

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Identidad"
        title="Usuarios"
        description="Gestion operativa de usuarios, roles y estado de cuenta."
        actions={
          <button className="button primary" type="button" onClick={() => setShowCreateForm((visible) => !visible)}>
            {showCreateForm ? "Cancelar" : "Crear usuario"}
          </button>
        }
      />
      {showCreateForm ? (
        <article className="panel">
          <form className="user-create-form" onSubmit={submitCreateUser}>
            <div className="field">
              <label htmlFor="new-username">Username</label>
              <input id="new-username" minLength={3} maxLength={100} required value={newUser.username} onChange={(event) => setNewUser({ ...newUser, username: event.target.value })} />
            </div>
            <div className="field">
              <label htmlFor="new-password">Contraseña</label>
              <input id="new-password" minLength={8} maxLength={128} required type="password" value={newUser.password} onChange={(event) => setNewUser({ ...newUser, password: event.target.value })} />
            </div>
            <div className="field">
              <label htmlFor="new-role">Rol</label>
              <select id="new-role" value={newUser.role} onChange={(event) => setNewUser({ ...newUser, role: event.target.value as UserCreateInput["role"] })}>
                <option value="user">user</option>
                {currentUser?.role === "super_admin" ? <option value="admin">admin</option> : null}
              </select>
            </div>
            <button className="button primary" disabled={createUser.isPending} type="submit">
              {createUser.isPending ? "Creando..." : "Crear usuario"}
            </button>
            {createError ? <p className="form-error" role="alert">{createError}</p> : null}
          </form>
        </article>
      ) : null}
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
                <th>Origen</th>
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
                  <td><Badge tone={user.authProvider === "oidc" ? "blue" : "neutral"}>{user.authProvider}</Badge></td>
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

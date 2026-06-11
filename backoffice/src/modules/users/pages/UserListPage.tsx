import { useQuery } from "@tanstack/react-query";

import { backofficeService } from "@/shared/api/backofficeService";
import { Badge } from "@/shared/ui/Badge";
import { PageHeader } from "@/shared/ui/PageHeader";

export function UserListPage() {
  const { data = [] } = useQuery({
    queryKey: ["users"],
    queryFn: backofficeService.getUsers
  });

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Identidad"
        title="Usuarios"
        description="Gestion operativa de usuarios, roles y estado de cuenta."
      />
      <article className="panel">
        <div className="table-shell">
          <table>
            <thead>
              <tr>
                <th>Username</th>
                <th>Nombre</th>
                <th>Rol</th>
                <th>Estado</th>
                <th>Videos</th>
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}

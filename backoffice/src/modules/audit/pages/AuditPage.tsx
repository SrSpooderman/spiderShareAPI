import { useQuery } from "@tanstack/react-query";

import { backofficeService } from "@/shared/api/backofficeService";
import { Badge } from "@/shared/ui/Badge";
import { PageHeader } from "@/shared/ui/PageHeader";

export function AuditPage() {
  const { data = [] } = useQuery({
    queryKey: ["audit"],
    queryFn: backofficeService.getAuditEntries
  });

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Seguridad"
        title="Auditoria"
        description="Registro de acciones administrativas sensibles."
      />
      <article className="panel">
        <div className="table-shell">
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Actor</th>
                <th>Accion</th>
                <th>Entidad</th>
                <th>Resultado</th>
              </tr>
            </thead>
            <tbody>
              {data.map((entry) => (
                <tr key={entry.id}>
                  <td>{entry.createdAt}</td>
                  <td>{entry.actorUsername}</td>
                  <td>{entry.action}</td>
                  <td>{entry.entity}</td>
                  <td><Badge tone={entry.result === "success" ? "green" : "red"}>{entry.result}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}

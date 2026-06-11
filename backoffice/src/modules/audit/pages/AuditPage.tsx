import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { backofficeService } from "@/shared/api/backofficeService";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { PaginationControls } from "@/shared/ui/PaginationControls";
import { QueryPanelState } from "@/shared/ui/QueryPanelState";

const PAGE_SIZE = 50;

export function AuditPage() {
  const [offset, setOffset] = useState(0);
  const { data = [], isError, isLoading } = useQuery({
    queryKey: ["audit", offset],
    queryFn: () => backofficeService.getAuditEntries({ limit: PAGE_SIZE, offset })
  });

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Seguridad"
        title="Auditoria"
        description="Registro de acciones administrativas sensibles."
      />
      <article className="panel">
        <QueryPanelState
          errorDescription="No se pudo recuperar el registro de auditoria."
          errorTitle="Error cargando auditoria"
          isError={isError}
          isLoading={isLoading}
          loadingDescription="Consultando acciones administrativas recientes."
          loadingTitle="Cargando auditoria"
        />
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
          {!isLoading && !isError && !data.length ? (
            <EmptyState title="Sin auditoria" description="Todavia no hay acciones administrativas registradas." />
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

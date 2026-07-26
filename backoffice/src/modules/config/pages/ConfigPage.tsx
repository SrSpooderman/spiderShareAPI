import { useQuery } from "@tanstack/react-query";

import { backofficeService } from "@/shared/api/backofficeService";
import { ConfigEntry } from "@/shared/types/backoffice";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { QueryPanelState } from "@/shared/ui/QueryPanelState";

export function ConfigPage() {
  const { data = [], isError, isLoading } = useQuery({
    queryKey: ["admin-config"],
    queryFn: backofficeService.getConfig
  });
  const groupedConfig = groupByCategory(data);

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Administracion"
        title="Configuracion"
        description="Variables operativas visibles para administracion, excluyendo enlaces y valores privados."
      />
      <QueryPanelState
        errorDescription="No se pudo recuperar la configuracion segura del entorno."
        errorTitle="Error cargando configuracion"
        isError={isError}
        isLoading={isLoading}
        loadingDescription="Leyendo variables visibles del entorno."
        loadingTitle="Cargando configuracion"
      />

      {!isLoading && !isError && groupedConfig.length === 0 ? (
        <EmptyState title="Sin configuracion" description="No hay variables visibles configuradas." />
      ) : null}

      {groupedConfig.map(([category, entries]) => (
        <article className="panel" key={category}>
          <div className="panel-header">
            <h2>{category}</h2>
            <Badge>{entries.length}</Badge>
          </div>
          <div className="table-shell">
            <table>
              <thead>
                <tr>
                  <th>Variable</th>
                  <th>Valor</th>
                  <th>Tipo</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.key}>
                    <td>
                      <code>{entry.key}</code>
                    </td>
                    <td className="config-value">{formatConfigValue(entry.value)}</td>
                    <td>
                      <Badge tone={entry.valueType === "empty" ? "yellow" : "neutral"}>
                        {entry.valueType}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ))}
    </section>
  );
}

function groupByCategory(entries: ConfigEntry[]) {
  const groups = new Map<string, ConfigEntry[]>();
  entries.forEach((entry) => {
    groups.set(entry.category, [...(groups.get(entry.category) ?? []), entry]);
  });
  return Array.from(groups.entries());
}

function formatConfigValue(value: ConfigEntry["value"]) {
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "-";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (value === null || value === "") {
    return "-";
  }
  return String(value);
}

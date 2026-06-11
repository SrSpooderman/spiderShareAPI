import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Clock, ServerCog, Video } from "lucide-react";
import { ReactNode } from "react";
import { Link } from "react-router-dom";

import { backofficeService } from "@/shared/api/backofficeService";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { QueryPanelState } from "@/shared/ui/QueryPanelState";
import { StatusBadge } from "@/shared/ui/StatusBadge";

export function DashboardPage() {
  const { data, isError, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: backofficeService.getDashboard
  });

  const totals = data?.totals;

  return (
    <section className="stack">
      <PageHeader
        eyebrow="Operacion"
        title="Dashboard"
        description="Resumen rapido del estado de videos, cola y servicios."
      />
      <QueryPanelState
        errorDescription="No se pudo recuperar el resumen operativo del backoffice."
        errorTitle="Error cargando dashboard"
        isError={isError}
        isLoading={isLoading}
        loadingDescription="Consultando servicios, cola y videos recientes."
        loadingTitle="Cargando dashboard"
      />

      <div className="metric-grid">
        <Metric icon={<Video />} label="Videos" value={totals?.videos ?? "-"} />
        <Metric icon={<Clock />} label="Pending" value={totals?.pending ?? "-"} tone="yellow" />
        <Metric icon={<ServerCog />} label="Processing" value={totals?.processing ?? "-"} tone="blue" />
        <Metric icon={<CheckCircle2 />} label="Ready" value={totals?.ready ?? "-"} tone="green" />
        <Metric icon={<AlertTriangle />} label="Failed" value={totals?.failed ?? "-"} tone="red" />
      </div>

      <div className="content-grid two">
        <article className="panel">
          <div className="panel-header">
            <h2>Servicios</h2>
          </div>
          <div className="service-list">
            {data?.services.map((service) => (
              <div className="service-row" key={service.name}>
                <span className={`status-dot ${service.status === "ok" ? "ok" : "warn"}`} />
                <strong>{service.name}</strong>
                <span>{service.detail}</span>
              </div>
            ))}
            {!isLoading && !isError && !data?.services.length ? (
              <EmptyState title="Sin servicios" description="No hay estados de servicio disponibles." />
            ) : null}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>Cola</h2>
            <Link to="/worker/queue">Ver cola</Link>
          </div>
          <div className="queue-summary">
            <Badge tone="yellow">{totals?.queuedJobs ?? 0} queued</Badge>
            <Badge tone="blue">{totals?.activeJobs ?? 0} active</Badge>
            <Badge tone="red">{totals?.failedJobs ?? 0} failed</Badge>
          </div>
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h2>Ultimos fallos</h2>
          <Link to="/videos">Ver videos</Link>
        </div>
        <div className="table-shell">
          <table>
            <thead>
              <tr>
                <th>Titulo</th>
                <th>Owner</th>
                <th>Estado</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {data?.recentFailures.map((video) => (
                <tr key={video.id}>
                  <td>
                    <Link to={`/videos/${video.id}`}>{video.title}</Link>
                  </td>
                  <td>{video.ownerUsername}</td>
                  <td><StatusBadge status={video.processingStatus} /></td>
                  <td>{video.latestProcessingError?.errorType ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!isLoading && !isError && !data?.recentFailures.length ? (
            <EmptyState title="Sin fallos recientes" description="No hay videos fallidos en el resumen actual." />
          ) : null}
        </div>
      </article>
    </section>
  );
}

function Metric({
  icon,
  label,
  value,
  tone = "neutral"
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  tone?: "neutral" | "blue" | "green" | "yellow" | "red";
}) {
  return (
    <article className={`metric metric-${tone}`}>
      <div>{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

import { PageHeader } from "@/shared/ui/PageHeader";

const sampleLogs = [
  "event=jaimito.worker.redis_ready queue=video-processing",
  "event=video.job.received video_id=video-3 job_id=video-processing-video-3",
  "event=jaimito.job.failed video_id=video-3 job_id=video-processing-video-3 error_type=CalledProcessError"
];

export function WorkerRawLogsPage() {
  return (
    <section className="stack">
      <PageHeader
        eyebrow="Worker"
        title="Logs crudos"
        description="Vista secundaria para consola del worker cuando exista fuente de logs configurada."
      />
      <article className="terminal-panel" aria-label="Worker raw logs">
        {sampleLogs.map((line) => (
          <code key={line}>{line}</code>
        ))}
      </article>
    </section>
  );
}

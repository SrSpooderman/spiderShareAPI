import {
  AuditEntry,
  BackofficeUser,
  DashboardSummary,
  QueueJob,
  VideoDetail,
  VideoSummary,
  WorkerEvent
} from "@/shared/types/backoffice";

const failedError = {
  id: "err-1",
  videoId: "video-3",
  attempt: 2,
  errorType: "CalledProcessError",
  errorMessage: "ffmpeg exited with status 1",
  jobId: "video-processing-video-3",
  durationMs: 8234,
  createdAt: "2026-06-11T09:24:00Z"
};

export const videos: VideoSummary[] = [
  {
    id: "video-1",
    title: "Boss clip",
    ownerUsername: "alice",
    ownerId: "user-1",
    processingStatus: "ready",
    visibility: "public",
    durationSeconds: 42.8,
    createdAt: "2026-06-11T08:20:00Z",
    latestProcessingError: null
  },
  {
    id: "video-2",
    title: "Speedrun attempt",
    ownerUsername: "marcos",
    ownerId: "user-2",
    processingStatus: "processing",
    visibility: "registered",
    durationSeconds: null,
    createdAt: "2026-06-11T09:10:00Z",
    latestProcessingError: null
  },
  {
    id: "video-3",
    title: "Raid highlight",
    ownerUsername: "nora",
    ownerId: "user-3",
    processingStatus: "failed",
    visibility: "public",
    durationSeconds: null,
    createdAt: "2026-06-11T09:12:00Z",
    latestProcessingError: failedError
  },
  {
    id: "video-4",
    title: "PvP clutch",
    ownerUsername: "sam",
    ownerId: "user-4",
    processingStatus: "pending",
    visibility: "public",
    durationSeconds: null,
    createdAt: "2026-06-11T09:19:00Z",
    latestProcessingError: null
  }
];

export const videoDetails: Record<string, VideoDetail> = Object.fromEntries(
  videos.map((video) => [
    video.id,
    {
      ...video,
      originalFilename: `${video.id}.mp4`,
      width: video.processingStatus === "ready" ? 1920 : null,
      height: video.processingStatus === "ready" ? 1080 : null,
      thumbnailPath:
        video.processingStatus === "ready" ? `thumbnails/${video.id}/thumbnail.jpg` : null,
      variants:
        video.processingStatus === "ready"
          ? [
              {
                type: "original_av1",
                codec: "av1",
                width: 1920,
                height: 1080,
                sizeBytes: 21_400_000
              },
              {
                type: "low_h264",
                codec: "h264",
                width: 1280,
                height: 720,
                sizeBytes: 8_900_000
              }
            ]
          : []
    }
  ])
);

export const workerEvents: WorkerEvent[] = [
  {
    id: "evt-1",
    eventType: "jaimito.worker.redis_ready",
    level: "info",
    message: "Redis responde; worker listo",
    videoId: null,
    jobId: null,
    workerName: "jaimito_worker",
    createdAt: "2026-06-11T09:00:00Z"
  },
  {
    id: "evt-2",
    eventType: "video.job.received",
    level: "info",
    message: "Job recibido para procesar video",
    videoId: "video-3",
    jobId: "video-processing-video-3",
    workerName: "jaimito_worker",
    createdAt: "2026-06-11T09:20:00Z"
  },
  {
    id: "evt-3",
    eventType: "video.processing.failed",
    level: "error",
    message: "ffmpeg exited with status 1",
    videoId: "video-3",
    jobId: "video-processing-video-3",
    workerName: "jaimito_worker",
    createdAt: "2026-06-11T09:24:00Z"
  }
];

export const queueJobs: QueueJob[] = [
  {
    id: "video-processing-video-2",
    videoId: "video-2",
    status: "started",
    attempts: 1,
    enqueuedAt: "2026-06-11T09:10:00Z"
  },
  {
    id: "video-processing-video-4",
    videoId: "video-4",
    status: "queued",
    attempts: 0,
    enqueuedAt: "2026-06-11T09:19:00Z"
  }
];

export const users: BackofficeUser[] = [
  {
    id: "user-1",
    username: "alice",
    displayName: "Alice",
    role: "user",
    isActive: true,
    videoCount: 12
  },
  {
    id: "user-2",
    username: "admin",
    displayName: "Admin",
    role: "super_admin",
    isActive: true,
    videoCount: 2
  }
];

export const auditEntries: AuditEntry[] = [
  {
    id: "audit-1",
    actorUsername: "admin",
    action: "processing.retry.requested",
    entity: "video-3",
    result: "success",
    createdAt: "2026-06-11T09:30:00Z"
  }
];

export const dashboard: DashboardSummary = {
  totals: {
    videos: videos.length,
    pending: videos.filter((video) => video.processingStatus === "pending").length,
    processing: videos.filter((video) => video.processingStatus === "processing").length,
    ready: videos.filter((video) => video.processingStatus === "ready").length,
    failed: videos.filter((video) => video.processingStatus === "failed").length,
    queuedJobs: queueJobs.filter((job) => job.status === "queued").length,
    activeJobs: queueJobs.filter((job) => job.status === "started").length,
    failedJobs: queueJobs.filter((job) => job.status === "failed").length
  },
  services: [
    { name: "API", status: "ok", detail: "Responding" },
    { name: "MySQL", status: "ok", detail: "Healthy" },
    { name: "Redis", status: "ok", detail: "Healthy" },
    { name: "Worker", status: "warning", detail: "1 failed video" }
  ],
  recentFailures: videos.filter((video) => video.processingStatus === "failed"),
  recentUploads: videos.slice(0, 3)
};

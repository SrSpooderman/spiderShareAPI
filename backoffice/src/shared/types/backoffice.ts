export type ProcessingStatus = "pending" | "processing" | "ready" | "failed";
export type HealthStatus = "ok" | "warning" | "down";
export type UserRole = "user" | "admin" | "super_admin";

export type DashboardSummary = {
  totals: {
    videos: number;
    pending: number;
    processing: number;
    ready: number;
    failed: number;
    queuedJobs: number;
    activeJobs: number;
    failedJobs: number;
  };
  services: Array<{
    name: string;
    status: HealthStatus;
    detail: string;
  }>;
  recentFailures: VideoSummary[];
  recentUploads: VideoSummary[];
};

export type ProcessingError = {
  id: string;
  videoId: string;
  attempt: number;
  errorType: string;
  errorMessage: string;
  jobId: string | null;
  durationMs: number | null;
  createdAt: string;
};

export type VideoSummary = {
  id: string;
  title: string;
  ownerUsername: string;
  ownerId: string;
  processingStatus: ProcessingStatus;
  visibility: "public" | "registered";
  durationSeconds: number | null;
  createdAt: string;
  latestProcessingError: ProcessingError | null;
};

export type VideoListFilters = {
  status?: ProcessingStatus;
  title?: string;
  owner?: string;
  visibility?: "public" | "registered";
  limit?: number;
  offset?: number;
};

export type VideoDetail = VideoSummary & {
  originalFilename: string;
  width: number | null;
  height: number | null;
  thumbnailPath: string | null;
  variants: Array<{
    type: string;
    codec: string;
    width: number;
    height: number;
    sizeBytes: number;
  }>;
};

export type WorkerEvent = {
  id: string;
  eventType: string;
  level: "info" | "warning" | "error";
  message: string;
  videoId: string | null;
  jobId: string | null;
  workerName: string;
  createdAt: string;
};

export type QueueJob = {
  id: string;
  videoId: string;
  status: "queued" | "started" | "failed" | "deferred";
  attempts: number;
  enqueuedAt: string;
};

export type BackofficeUser = {
  id: string;
  username: string;
  displayName: string | null;
  role: UserRole;
  isActive: boolean;
  videoCount: number;
};

export type UserListFilters = {
  username?: string;
  role?: UserRole;
  isActive?: boolean;
};

export type BackofficeUserDetail = BackofficeUser & {
  lastLoginAt: string | null;
  createdAt: string;
  updatedAt: string;
  recentVideos: VideoSummary[];
};

export type AuditEntry = {
  id: string;
  actorUsername: string;
  action: string;
  entity: string;
  result: "success" | "failed";
  createdAt: string;
};

export type OffsetPagination = {
  limit?: number;
  offset?: number;
};

export type WorkerEventFilters = OffsetPagination & {
  level?: WorkerEvent["level"];
  videoId?: string;
  jobId?: string;
};

export type RawLogLine = {
  line: string;
  source: string;
  createdAt: string | null;
};

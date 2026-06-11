import { apiRequest } from "@/shared/api/httpClient";
import {
  AuditEntry,
  BackofficeUser,
  DashboardSummary,
  QueueJob,
  RawLogLine,
  VideoDetail,
  VideoSummary,
  WorkerEvent
} from "@/shared/types/backoffice";

export const backofficeService = {
  async getDashboard(): Promise<DashboardSummary> {
    return apiRequest<DashboardSummary>("/admin/dashboard");
  },

  async getVideos(): Promise<VideoSummary[]> {
    return apiRequest<VideoSummary[]>("/admin/videos");
  },

  async getVideo(videoId: string): Promise<VideoDetail> {
    return apiRequest<VideoDetail>(`/admin/videos/${videoId}`);
  },

  async retryVideo(videoId: string): Promise<void> {
    return apiRequest<void>(`/admin/videos/${videoId}/processing/retry`, {
      method: "POST"
    });
  },

  async getWorkerEvents(): Promise<WorkerEvent[]> {
    return apiRequest<WorkerEvent[]>("/admin/worker/events");
  },

  async getQueueJobs(): Promise<QueueJob[]> {
    return apiRequest<QueueJob[]>("/admin/queue/jobs");
  },

  async getUsers(): Promise<BackofficeUser[]> {
    return apiRequest<BackofficeUser[]>("/admin/users");
  },

  async getAuditEntries(): Promise<AuditEntry[]> {
    return apiRequest<AuditEntry[]>("/admin/audit");
  },

  async getRawLogs(): Promise<RawLogLine[]> {
    return apiRequest<RawLogLine[]>("/admin/worker/logs");
  }
};

import { env } from "@/shared/config/env";
import { apiRequest } from "@/shared/api/httpClient";
import {
  auditEntries,
  dashboard,
  queueJobs,
  users,
  videoDetails,
  videos,
  workerEvents
} from "@/shared/api/mockData";
import {
  AuditEntry,
  BackofficeUser,
  DashboardSummary,
  QueueJob,
  VideoDetail,
  VideoSummary,
  WorkerEvent
} from "@/shared/types/backoffice";

const wait = (ms = 180) => new Promise((resolve) => window.setTimeout(resolve, ms));

export const backofficeService = {
  async getDashboard(): Promise<DashboardSummary> {
    if (env.useMocks) {
      await wait();
      return dashboard;
    }
    return apiRequest<DashboardSummary>("/admin/dashboard");
  },

  async getVideos(): Promise<VideoSummary[]> {
    if (env.useMocks) {
      await wait();
      return videos;
    }
    return apiRequest<VideoSummary[]>("/admin/videos");
  },

  async getVideo(videoId: string): Promise<VideoDetail> {
    if (env.useMocks) {
      await wait();
      return videoDetails[videoId] ?? videoDetails["video-1"];
    }
    return apiRequest<VideoDetail>(`/admin/videos/${videoId}`);
  },

  async retryVideo(videoId: string): Promise<void> {
    if (env.useMocks) {
      await wait();
      return;
    }
    return apiRequest<void>(`/admin/videos/${videoId}/processing/retry`, {
      method: "POST"
    });
  },

  async getWorkerEvents(): Promise<WorkerEvent[]> {
    if (env.useMocks) {
      await wait();
      return workerEvents;
    }
    return apiRequest<WorkerEvent[]>("/admin/worker/events");
  },

  async getQueueJobs(): Promise<QueueJob[]> {
    if (env.useMocks) {
      await wait();
      return queueJobs;
    }
    return apiRequest<QueueJob[]>("/admin/queue/jobs");
  },

  async getUsers(): Promise<BackofficeUser[]> {
    if (env.useMocks) {
      await wait();
      return users;
    }
    return apiRequest<BackofficeUser[]>("/admin/users");
  },

  async getAuditEntries(): Promise<AuditEntry[]> {
    if (env.useMocks) {
      await wait();
      return auditEntries;
    }
    return apiRequest<AuditEntry[]>("/admin/audit");
  }
};

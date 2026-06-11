import { apiRequest } from "@/shared/api/httpClient";
import {
  AuditEntry,
  BackofficeUser,
  BackofficeUserDetail,
  DashboardSummary,
  OffsetPagination,
  QueueJob,
  RawLogLine,
  UserListFilters,
  UserUpdateInput,
  VideoDetail,
  VideoListFilters,
  VideoSummary,
  WorkerEvent,
  WorkerEventFilters
} from "@/shared/types/backoffice";

function queryString(params: Record<string, string | number | boolean | undefined>) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      searchParams.set(key, String(value));
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export const backofficeService = {
  async getDashboard(): Promise<DashboardSummary> {
    return apiRequest<DashboardSummary>("/admin/dashboard");
  },

  async getVideos(filters: VideoListFilters = {}): Promise<VideoSummary[]> {
    return apiRequest<VideoSummary[]>(
      `/admin/videos${queryString({
        status: filters.status,
        title: filters.title,
        owner: filters.owner,
        visibility: filters.visibility,
        limit: filters.limit,
        offset: filters.offset
      })}`
    );
  },

  async getVideo(videoId: string): Promise<VideoDetail> {
    return apiRequest<VideoDetail>(`/admin/videos/${videoId}`);
  },

  async retryVideo(videoId: string): Promise<void> {
    return apiRequest<void>(`/admin/videos/${videoId}/processing/retry`, {
      method: "POST"
    });
  },

  async deleteVideo(videoId: string): Promise<void> {
    return apiRequest<void>(`/admin/videos/${videoId}`, {
      method: "DELETE"
    });
  },

  async getWorkerEvents(filters: WorkerEventFilters = {}): Promise<WorkerEvent[]> {
    return apiRequest<WorkerEvent[]>(
      `/admin/worker/events${queryString({
        video_id: filters.videoId,
        job_id: filters.jobId,
        level: filters.level,
        limit: filters.limit,
        offset: filters.offset
      })}`
    );
  },

  async getQueueJobs(): Promise<QueueJob[]> {
    return apiRequest<QueueJob[]>("/admin/queue/jobs");
  },

  async requeueJob(jobId: string): Promise<QueueJob> {
    return apiRequest<QueueJob>(`/admin/queue/jobs/${jobId}/requeue`, {
      method: "POST"
    });
  },

  async deleteJob(jobId: string): Promise<void> {
    return apiRequest<void>(`/admin/queue/jobs/${jobId}`, {
      method: "DELETE"
    });
  },

  async clearFailedJobs(): Promise<void> {
    return apiRequest<void>("/admin/queue/failed-jobs", {
      method: "DELETE"
    });
  },

  async getUsers(filters: UserListFilters = {}): Promise<BackofficeUser[]> {
    return apiRequest<BackofficeUser[]>(
      `/admin/users${queryString({
        username: filters.username,
        role: filters.role,
        is_active: filters.isActive
      })}`
    );
  },

  async getUser(userId: string): Promise<BackofficeUserDetail> {
    return apiRequest<BackofficeUserDetail>(`/admin/users/${userId}`);
  },

  async updateUser(userId: string, input: UserUpdateInput): Promise<BackofficeUserDetail> {
    return apiRequest<BackofficeUserDetail>(`/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(input)
    });
  },

  async getAuditEntries(pagination: OffsetPagination = {}): Promise<AuditEntry[]> {
    return apiRequest<AuditEntry[]>(
      `/admin/audit${queryString({
        limit: pagination.limit,
        offset: pagination.offset
      })}`
    );
  },

  async getRawLogs(pagination: OffsetPagination = {}): Promise<RawLogLine[]> {
    return apiRequest<RawLogLine[]>(
      `/admin/worker/logs${queryString({
        limit: pagination.limit,
        offset: pagination.offset
      })}`
    );
  }
};

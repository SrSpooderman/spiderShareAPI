import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/layouts/AppShell";
import { AuditPage } from "@/modules/audit/pages/AuditPage";
import { ConfigPage } from "@/modules/config/pages/ConfigPage";
import { DashboardPage } from "@/modules/dashboard/pages/DashboardPage";
import { LoginPage } from "@/modules/auth/pages/LoginPage";
import { OidcCallbackPage } from "@/modules/auth/pages/OidcCallbackPage";
import { RequireAuth } from "@/modules/auth/RequireAuth";
import { UserDetailPage } from "@/modules/users/pages/UserDetailPage";
import { UserListPage } from "@/modules/users/pages/UserListPage";
import { VideoDetailPage } from "@/modules/videos/pages/VideoDetailPage";
import { VideoListPage } from "@/modules/videos/pages/VideoListPage";
import { WorkerEventsPage } from "@/modules/worker/pages/WorkerEventsPage";
import { WorkerQueuePage } from "@/modules/worker/pages/WorkerQueuePage";
import { WorkerRawLogsPage } from "@/modules/worker/pages/WorkerRawLogsPage";

const basename = (import.meta.env.BASE_URL || "/").replace(/\/$/, "") || "/";

export const router = createBrowserRouter(
  [
    {
      path: "/login",
      element: <LoginPage />
    },
    {
      path: "/login/oidc/callback",
      element: <OidcCallbackPage />
    },
    {
      path: "/",
      element: (
        <RequireAuth>
          <AppShell />
        </RequireAuth>
      ),
      children: [
        { index: true, element: <Navigate to="/dashboard" replace /> },
        { path: "dashboard", element: <DashboardPage /> },
        { path: "config", element: <ConfigPage /> },
        { path: "videos", element: <VideoListPage /> },
        { path: "videos/:videoId", element: <VideoDetailPage /> },
        { path: "worker/queue", element: <WorkerQueuePage /> },
        { path: "worker/events", element: <WorkerEventsPage /> },
        { path: "worker/logs", element: <WorkerRawLogsPage /> },
        { path: "users", element: <UserListPage /> },
        { path: "users/:userId", element: <UserDetailPage /> },
        { path: "audit", element: <AuditPage /> }
      ]
    }
  ],
  { basename }
);

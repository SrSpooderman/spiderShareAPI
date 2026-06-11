import {
  Activity,
  ClipboardList,
  LayoutDashboard,
  ListVideo,
  ScrollText,
  ServerCog,
  ShieldCheck,
  Users
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { env } from "@/shared/config/env";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/videos", label: "Videos", icon: ListVideo },
  { to: "/worker/queue", label: "Cola", icon: ServerCog },
  { to: "/worker/events", label: "Eventos", icon: Activity },
  { to: "/worker/logs", label: "Logs", icon: ScrollText },
  { to: "/users", label: "Usuarios", icon: Users },
  { to: "/audit", label: "Auditoria", icon: ClipboardList }
];

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={28} />
          <div>
            <strong>SpiderShare</strong>
            <span>Backoffice</span>
          </div>
        </div>

        <nav className="nav-list" aria-label="Backoffice navigation">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              <item.icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <span className="eyebrow">Entorno</span>
            <strong>{env.appEnv}</strong>
          </div>
          <div className="topbar-status">
            <span className="status-dot ok" />
            <span>{env.useMocks ? "Datos mock" : env.apiBaseUrl}</span>
          </div>
        </header>
        <div className="page-frame">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

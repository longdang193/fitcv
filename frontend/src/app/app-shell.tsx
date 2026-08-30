import React, { useState, useEffect, useCallback } from "react";
import {
  discoverFeatureRoutes,
  matchRoute,
  FeatureRoute,
} from "./route-registry";
import { Navigation, NavGroup, Button } from "../components";
import {
  notificationStore,
  TransientNotification,
} from "../lib/notifications";

export const AppShell: React.FC = () => {
  const [routes] = useState<FeatureRoute[]>(() => discoverFeatureRoutes());
  const [currentHash, setCurrentHash] = useState<string>(() => {
    if (typeof window !== "undefined" && window.location.hash) {
      return window.location.hash;
    }
    return "#/overview";
  });
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof document !== "undefined") {
      const existing = document.documentElement.getAttribute("data-theme");
      if (existing === "dark" || existing === "light") return existing;
    }
    return "light";
  });
  const [notifications, setNotifications] = useState<TransientNotification[]>([]);
  const [isNotifOpen, setIsNotifOpen] = useState(false);

  // Sync hash routing
  useEffect(() => {
    const handleHashChange = () => {
      const h = window.location.hash || "#/overview";
      setCurrentHash(h);
      setIsMobileMenuOpen(false);
    };

    window.addEventListener("hashchange", handleHashChange);
    if (!window.location.hash) {
      window.location.hash = "#/overview";
    }

    return () => {
      window.removeEventListener("hashchange", handleHashChange);
    };
  }, []);

  // Sync theme
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Subscribe to transient notifications
  useEffect(() => {
    const unsubscribe = notificationStore.subscribe(setNotifications);
    return unsubscribe;
  }, []);

  // Keyboard Escape listener for mobile drawer and dropdown
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (isMobileMenuOpen) setIsMobileMenuOpen(false);
        if (isNotifOpen) setIsNotifOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isMobileMenuOpen, isNotifOpen]);

  const activeRoute = matchRoute(currentHash, routes);
  const ActiveComponent = activeRoute.component;

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const handleNavigate = useCallback((href: string) => {
    window.location.hash = href;
    setCurrentHash(href);
    setIsMobileMenuOpen(false);
  }, []);

  // Build navigation groups from routes and standard structure
  const navGroups: NavGroup[] = [
    {
      id: "workspace",
      title: "Workspace",
      defaultOpen: true,
      items: [
        { id: "overview", label: "Overview", href: "#/overview" },
        { id: "candidate-profile", label: "Candidate Profile", href: "#/candidate-profile" },
        { id: "scans", label: "Scans", href: "#/scans" },
        { id: "runs", label: "Runs", href: "#/runs" },
        { id: "bookmarks", label: "Bookmarks", href: "#/bookmarks" },
      ],
    },
    {
      id: "settings",
      title: "Settings & System",
      defaultOpen: true,
      items: [
        { id: "providers", label: "API Providers", href: "#/settings/providers" },
        { id: "llm", label: "LLM Configuration", href: "#/settings/llm" },
        { id: "prompts", label: "Prompts", href: "#/settings/prompts" },
        { id: "synonyms", label: "Synonyms", href: "#/settings/synonyms" },
        { id: "personalization", label: "Personalization", href: "#/settings/personalization" },
        { id: "system", label: "System Diagnostics", href: "#/settings/system" },
      ],
    },
  ];

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div className="app-shell">
      {/* Mobile Scrim */}
      {isMobileMenuOpen && (
        <div
          className="sidebar-scrim"
          role="presentation"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`sidebar ${isMobileMenuOpen ? "is-open" : ""}`}
        aria-label="Application Sidebar"
      >
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            F
          </div>
          <div className="brand-text">
            <strong>FitCV</strong>
            <small>Local Control Plane</small>
          </div>
        </div>

        <Navigation
          groups={navGroups}
          currentPath={currentHash}
          onNavigate={handleNavigate}
        />
      </aside>

      {/* Main Content Area */}
      <div className="main-content-area">
        <header className="app-header">
          <div className="header-title-area">
            <Button
              className="mobile-menu-btn"
              variant="icon"
              aria-label={isMobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={isMobileMenuOpen}
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              ☰
            </Button>
            <h1>{activeRoute.title}</h1>
          </div>

          <div className="header-actions">
            {/* Global Notification Bell */}
            <div style={{ position: "relative" }}>
              <Button
                variant="icon"
                className="notification-bell-btn"
                aria-label={`Notifications (${unreadCount} unread)`}
                aria-expanded={isNotifOpen}
                onClick={() => setIsNotifOpen(!isNotifOpen)}
              >
                🔔
                {unreadCount > 0 && (
                  <span className="notification-badge" aria-hidden="true">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </Button>

              {isNotifOpen && (
                <div
                  className="notification-dropdown"
                  role="dialog"
                  aria-label="Transient Notifications"
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "12px 16px",
                      borderBottom: "1px solid var(--border-soft)",
                    }}
                  >
                    <strong style={{ fontSize: 13 }}>Notifications</strong>
                    <div style={{ display: "flex", gap: 8 }}>
                      {unreadCount > 0 && (
                        <button
                          type="button"
                          className="btn-subtle"
                          style={{ fontSize: 12, padding: "2px 6px", cursor: "pointer", border: 0, background: "transparent" }}
                          onClick={() => notificationStore.markAllAsRead()}
                        >
                          Mark all read
                        </button>
                      )}
                      {notifications.length > 0 && (
                        <button
                          type="button"
                          className="btn-subtle"
                          style={{ fontSize: 12, padding: "2px 6px", cursor: "pointer", border: 0, background: "transparent" }}
                          onClick={() => notificationStore.clearAll()}
                        >
                          Clear all
                        </button>
                      )}
                    </div>
                  </div>

                  <div style={{ maxHeight: 360, overflowY: "auto" }}>
                    {notifications.length === 0 ? (
                      <div style={{ padding: "24px 16px", textAlign: "center", color: "var(--muted)", fontSize: 13 }}>
                        No notifications
                      </div>
                    ) : (
                      notifications.map((n) => (
                        <div
                          key={n.id}
                          className={`notification-item ${!n.read ? "unread" : ""}`}
                          onClick={() => notificationStore.markAsRead(n.id)}
                        >
                          <div className="notification-item-header">
                            <strong style={{ fontSize: 13 }}>{n.title}</strong>
                            <button
                              type="button"
                              aria-label="Dismiss notification"
                              style={{ border: 0, background: "transparent", cursor: "pointer", color: "var(--muted)", fontSize: 14 }}
                              onClick={(e) => {
                                e.stopPropagation();
                                notificationStore.dismiss(n.id);
                              }}
                            >
                              ✕
                            </button>
                          </div>
                          {n.message && <p style={{ margin: 0, fontSize: 12, color: "var(--muted)" }}>{n.message}</p>}
                          {n.actionLabel && n.onAction && (
                            <div style={{ marginTop: 6 }}>
                              <Button
                                size="compact"
                                variant="primary"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  n.onAction?.();
                                }}
                              >
                                {n.actionLabel}
                              </Button>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Theme Toggle */}
            <Button
              variant="icon"
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
              onClick={toggleTheme}
            >
              {theme === "light" ? "🌙" : "☀️"}
            </Button>
          </div>
        </header>

        {/* Scrollable page body */}
        <main className="app-scroll" tabIndex={-1}>
          <ActiveComponent />
        </main>
      </div>

      {/* Floating toast notifications */}
      <div className="toast-container" aria-live="polite" aria-atomic="true">
        {notifications.slice(0, 3).map((n) => (
          <div key={n.id} className="toast-item">
            <div style={{ flex: 1 }}>
              <strong style={{ display: "block", fontSize: 13 }}>{n.title}</strong>
              {n.message && <span style={{ fontSize: 12, color: "var(--muted)" }}>{n.message}</span>}
            </div>
            <button
              type="button"
              aria-label="Close toast"
              style={{ border: 0, background: "transparent", cursor: "pointer", color: "var(--muted)" }}
              onClick={() => notificationStore.dismiss(n.id)}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

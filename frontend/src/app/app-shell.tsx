import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
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
  const [notifications, setNotifications] = useState<TransientNotification[]>(() =>
    notificationStore.getNotifications()
  );
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [routeAnnouncement, setRouteAnnouncement] = useState("");
  const notificationButtonRef = useRef<HTMLButtonElement>(null);
  const notificationPanelRef = useRef<HTMLDivElement>(null);
  const notificationWasOpen = useRef(false);
  const mobileMenuButtonRef = useRef<HTMLButtonElement>(null);
  const mobileMenuWasOpenRef = useRef(false);
  const sidebarRef = useRef<HTMLElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const isFirstRouteMount = useRef(true);

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

  // Handle mobile drawer focus management
  useEffect(() => {
    if (isMobileMenuOpen) {
      mobileMenuWasOpenRef.current = true;
      const firstFocusable = sidebarRef.current?.querySelector<HTMLElement>(
        "a[href], button, input, select, textarea, [tabindex]:not([tabindex='-1'])"
      );
      firstFocusable?.focus();
    } else if (mobileMenuWasOpenRef.current) {
      mobileMenuWasOpenRef.current = false;
      mobileMenuButtonRef.current?.focus();
    }
  }, [isMobileMenuOpen]);

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

  useEffect(() => {
    if (!isNotifOpen) {
      if (notificationWasOpen.current) notificationButtonRef.current?.focus();
      notificationWasOpen.current = false;
      return;
    }

    notificationWasOpen.current = true;
    const panel = notificationPanelRef.current;
    if (!panel) return;

    const focusable = () =>
      Array.from(
        panel.querySelectorAll<HTMLElement>(
          "button, a[href], [tabindex]:not([tabindex='-1'])"
        )
      );
    focusable()[0]?.focus();

    const handleTab = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const items = focusable();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    const handleOutsideClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!panel.contains(target) && !notificationButtonRef.current?.contains(target)) {
        setIsNotifOpen(false);
      }
    };

    panel.addEventListener("keydown", handleTab);
    document.addEventListener("mousedown", handleOutsideClick);
    return () => {
      panel.removeEventListener("keydown", handleTab);
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, [isNotifOpen]);

  const activeRoute = matchRoute(currentHash, routes);
  const ActiveComponent = activeRoute.component;

  // Route-change polite screen reader announcement without stealing keyboard focus
  useEffect(() => {
    if (isFirstRouteMount.current) {
      isFirstRouteMount.current = false;
      return;
    }
    setRouteAnnouncement(`Navigated to ${activeRoute.title}`);
  }, [activeRoute.id, activeRoute.title]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const handleNavigate = useCallback((href: string) => {
    window.location.hash = href;
    setCurrentHash(href);
    setIsMobileMenuOpen(false);
  }, []);

  // Build navigation groups dynamically from discovered routes SSOT
  const navGroups: NavGroup[] = useMemo(() => {
    const workspaceItems = routes
      .filter((r) => r.group === "workspace")
      .map((r) => ({
        id: r.id,
        label: r.title,
        href: r.path,
        icon: r.icon,
      }));

    const settingsItems = routes
      .filter((r) => r.group === "settings" || r.group === "system")
      .map((r) => ({
        id: r.id,
        label: r.title,
        href: r.path,
        icon: r.icon,
      }));

    return [
      {
        id: "workspace",
        title: "Workspace",
        defaultOpen: true,
        items: workspaceItems,
      },
      {
        id: "settings",
        title: "Settings & System",
        defaultOpen: true,
        items: settingsItems,
      },
    ];
  }, [routes]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div className="app-shell">
      {/* Skip to main content for keyboard accessibility */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

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
        ref={sidebarRef}
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
            <button
              ref={mobileMenuButtonRef}
              type="button"
              className="mobile-menu-btn mobile-toggle-btn"
              aria-label={isMobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={isMobileMenuOpen}
              onClick={() => setIsMobileMenuOpen((prev) => !prev)}
            >
              {isMobileMenuOpen ? "✕" : "☰"}
            </button>
            <h1
              ref={headingRef}
              tabIndex={-1}
              id="main-page-heading"
              style={{ margin: 0, fontSize: 18, fontWeight: 700 }}
            >
              {activeRoute.title}
            </h1>
          </div>

          <div className="header-actions">
            {/* Notifications Dropdown */}
            <div style={{ position: "relative" }}>
              <Button
                variant="icon"
                className="notification-bell-btn"
                ref={notificationButtonRef}
                aria-label={
                  unreadCount > 0
                    ? `Notifications, ${unreadCount} unread ${unreadCount === 1 ? "notification" : "notifications"}`
                    : "Notifications, no unread notifications"
                }
                aria-expanded={isNotifOpen}
                onClick={() => setIsNotifOpen((prev) => !prev)}
              >
                🔔
                {unreadCount > 0 && (
                  <span
                    style={{
                      position: "absolute",
                      top: 2,
                      right: 2,
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: "var(--accent)",
                    }}
                    aria-hidden="true"
                  />
                )}
              </Button>

              {isNotifOpen && (
                <div
                  ref={notificationPanelRef}
                  className="notification-dropdown dropdown-panel"
                  role="dialog"
                  aria-label="Notifications panel"
                  aria-modal="false"
                  style={{
                    position: "absolute",
                    right: 0,
                    top: "calc(100% + 8px)",
                    width: 320,
                    maxWidth: "90vw",
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    boxShadow: "var(--shadow)",
                    zIndex: 50,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "10px 14px",
                      borderBottom: "1px solid var(--border-soft)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <strong style={{ fontSize: 13 }}>Notifications</strong>
                      {unreadCount > 0 && (
                        <span
                          className="badge"
                          aria-label={`${unreadCount} unread ${unreadCount === 1 ? "notification" : "notifications"}`}
                          style={{ fontSize: 11, minHeight: 18, padding: "0 6px" }}
                        >
                          {unreadCount}
                        </span>
                      )}
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      {unreadCount > 0 && (
                        <button
                          type="button"
                          className="btn-subtle"
                          aria-label="Mark all notifications as read"
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
                          aria-label="Clear all notifications"
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
                          aria-label={!n.read ? `Unread notification: ${n.title}` : undefined}
                          onClick={() => notificationStore.markAsRead(n.id)}
                        >
                          <div className="notification-item-header">
                            <strong style={{ fontSize: 13 }}>{n.title}</strong>
                            <button
                              type="button"
                              className="notification-dismiss-btn"
                              aria-label={`Dismiss notification: ${n.title}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                notificationStore.dismiss(n.id);
                              }}
                            >
                              ✕
                            </button>
                          </div>
                          {n.message && <p style={{ margin: 0, fontSize: 12, color: "var(--muted)" }}>{n.message}</p>}
                          {n.actionLabel && n.href && (
                            <div style={{ marginTop: 6 }}>
                              <a className="btn btn-primary" href={n.href} onClick={() => notificationStore.markAsRead(n.id)}>
                                {n.actionLabel}
                              </a>
                            </div>
                          )}
                          {n.actionLabel && n.onAction && !n.href && (
                            <div style={{ marginTop: 6 }}>
                              <Button
                                size="compact"
                                variant="primary"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  notificationStore.activateAction(n.id);
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

        {/* Live region for route announcements */}
        <div
          className="sr-only route-announcement"
          role="status"
          aria-live="polite"
          aria-atomic="true"
        >
          {routeAnnouncement}
        </div>

        {/* Scrollable page body */}
        <main id="main-content" className="app-scroll" tabIndex={-1}>
          <ActiveComponent />
        </main>
      </div>

      {/* Floating toast notifications */}
      <div className="toast-container" aria-live="polite" aria-atomic="true">
        {notifications.slice(0, 3).map((n) => (
          <div
            key={n.id}
            className="toast-item"
            onMouseEnter={() => notificationStore.pauseAutoDismiss(n.id)}
            onMouseLeave={() => notificationStore.resumeAutoDismiss(n.id)}
            onFocusCapture={() => notificationStore.pauseAutoDismiss(n.id)}
            onBlurCapture={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
                notificationStore.resumeAutoDismiss(n.id);
              }
            }}
          >
            <div style={{ flex: 1 }}>
              <strong style={{ display: "block", fontSize: 13 }}>{n.title}</strong>
              {n.message && <span style={{ fontSize: 12, color: "var(--muted)" }}>{n.message}</span>}
            </div>
            <button
              type="button"
              className="toast-dismiss-btn"
              aria-label="Close toast"
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

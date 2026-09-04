import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { discoverFeatureRoutes, matchRoute } from "./route-registry";
import { notificationStore } from "../lib/notifications";
import { AppShell } from "./app-shell";

describe("Frontend App Shell & Whole-Slice Integration", () => {
  beforeEach(() => {
    notificationStore.clearAll();
    if (typeof window !== "undefined") {
      window.location.hash = "#/overview";
    }
  });

  afterEach(() => {
    notificationStore.clearAll();
  });

  it("proves dynamic registration of all production slices", () => {
    const routes = discoverFeatureRoutes();
    const routeIds = routes.map((r) => r.id);

    // Completion-critical personal fitcv core journeys
    expect(routeIds).toContain("overview");
    expect(routeIds).toContain("candidate-profile");
    expect(routeIds).toContain("scans");
    expect(routeIds).toContain("runs");
    expect(routeIds).toContain("bookmarks");
    expect(routeIds).toContain("personalization");

    // Supporting slice
    expect(routeIds).toContain("synonyms");
  });

  it("handles cross-slice route matching without duplicate registry drift", () => {
    const routes = discoverFeatureRoutes();

    // Verify all routes are discoverable and matchable
    routes.forEach((route) => {
      const matched = matchRoute(route.path, routes);
      expect(matched.id).toBe(route.id);
    });
  });

  it("manages transient notifications with source dedupe and zero-badge rule", () => {
    expect(notificationStore.getUnreadCount()).toBe(0);

    const n1 = notificationStore.notify({
      dedupe: { actionId: "test-act-1" },
      type: "success",
      title: "Action Finished",
      message: "Run completed successfully",
    });

    expect(notificationStore.getUnreadCount()).toBe(1);
    expect(notificationStore.getNotifications()).toHaveLength(1);

    // Duplicate observation updates existing entry
    notificationStore.notify({
      dedupe: { actionId: "test-act-1" },
      type: "info",
      title: "Action Updated",
      message: "Run details refreshed",
    });

    expect(notificationStore.getNotifications()).toHaveLength(1);
    expect(notificationStore.getNotifications()[0].title).toBe("Action Updated");

    // Mark read
    notificationStore.markAsRead(n1.id);
    expect(notificationStore.getUnreadCount()).toBe(0);
  });
  it("renders accessible route heading, announcement region, and mobile toggle in AppShell", () => {
    const markup = renderToStaticMarkup(React.createElement(AppShell));

    // Route heading focusable with tabIndex -1
    expect(markup).toContain('id="main-page-heading"');
    expect(markup).toContain('tabindex="-1"');

    // Route announcement live region
    expect(markup).toContain('class="sr-only route-announcement"');
    expect(markup).toContain('role="status"');
    expect(markup).toContain('aria-live="polite"');

    // Mobile nav toggle button with accessible label
    expect(markup).toContain('class="mobile-menu-btn mobile-toggle-btn"');
    expect(markup).toContain('aria-label="Open navigation menu"');

    // Notification bell default accessible name
    expect(markup).toContain('aria-label="Notifications, no unread notifications"');
  });

  it("updates notification button accessible name to explicit unread count and noun", () => {
    notificationStore.notify({
      dedupe: "unread-1",
      type: "info",
      title: "New Job Found",
    });

    const markup = renderToStaticMarkup(React.createElement(AppShell));
    expect(markup).toContain('aria-label="Notifications, 1 unread notification"');
  });

});

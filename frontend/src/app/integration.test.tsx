import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { discoverFeatureRoutes, matchRoute } from "./route-registry";
import { notificationStore } from "../lib/notifications";

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
    expect(routeIds).toContain("job-evaluation");
    expect(routeIds).toContain("cv-review");
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
});

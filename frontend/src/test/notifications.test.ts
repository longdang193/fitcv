import { describe, it, expect, beforeEach } from "vitest";
import {
  notificationStore,
  buildDedupeKey,
} from "../lib/notifications";

describe("transient notifications store", () => {
  beforeEach(() => {
    notificationStore.clearAll();
  });

  it("builds priority dedupe keys accurately", () => {
    expect(buildDedupeKey({ actionId: "act-123" })).toBe("action:act-123");
    expect(buildDedupeKey({ eventId: "evt-456" })).toBe("event:evt-456");
    expect(
      buildDedupeKey({
        sourceType: "scan",
        sourceId: "scan-1",
        revision: 2,
        state: "completed",
      })
    ).toBe("state:scan:scan-1:2:completed");
    expect(
      buildDedupeKey({
        operation: "submit_run",
        sourceId: "run-1",
        errorCode: "conflict",
        attemptIdentity: "att-1",
      })
    ).toBe("request:submit_run:run-1:conflict:att-1");
  });

  it("deduplicates notifications by key and updates state", () => {
    notificationStore.notify({
      dedupe: { actionId: "retry-scan-1" },
      type: "info",
      title: "Retrying scan...",
    });

    expect(notificationStore.getNotifications()).toHaveLength(1);
    expect(notificationStore.getUnreadCount()).toBe(1);

    // Second notification with same dedupe updates the entry rather than adding duplicate
    notificationStore.notify({
      dedupe: { actionId: "retry-scan-1" },
      type: "success",
      title: "Scan retried successfully",
    });

    const notifs = notificationStore.getNotifications();
    expect(notifs).toHaveLength(1);
    expect(notifs[0].title).toBe("Scan retried successfully");
    expect(notifs[0].type).toBe("success");
  });

  it("supports markAsRead, markAllAsRead, dismiss, and clearAll", () => {
    const n1 = notificationStore.notify({
      dedupe: "k1",
      type: "info",
      title: "First",
    });
    const n2 = notificationStore.notify({
      dedupe: "k2",
      type: "warning",
      title: "Second",
    });

    expect(notificationStore.getUnreadCount()).toBe(2);

    notificationStore.markAsRead(n1.id);
    expect(notificationStore.getUnreadCount()).toBe(1);

    notificationStore.markAllAsRead();
    expect(notificationStore.getUnreadCount()).toBe(0);

    notificationStore.dismiss(n2.id);
    expect(notificationStore.getNotifications()).toHaveLength(1);

    notificationStore.clearAll();
    expect(notificationStore.getNotifications()).toHaveLength(0);
  });
});

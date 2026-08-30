/**
 * FitCV Client-Side Transient Notifications Store
 * Session-scoped, client-owned projection with priority deduplication.
 */

export type NotificationType = "info" | "success" | "warning" | "error";

export interface ActionDedupe {
  actionId: string;
}

export interface EventDedupe {
  eventId: string;
}

export interface StateDedupe {
  sourceType: string;
  sourceId: string;
  revision: string | number;
  state: string;
}

export interface RequestDedupe {
  operation: string;
  sourceId?: string;
  errorCode: string;
  attemptIdentity: string | number;
}

export type DedupeInput = ActionDedupe | EventDedupe | StateDedupe | RequestDedupe | string;

export function buildDedupeKey(dedupe: DedupeInput): string {
  if (typeof dedupe === "string") {
    return dedupe;
  }
  if ("actionId" in dedupe) {
    return `action:${dedupe.actionId}`;
  }
  if ("eventId" in dedupe) {
    return `event:${dedupe.eventId}`;
  }
  if ("sourceType" in dedupe) {
    return `state:${dedupe.sourceType}:${dedupe.sourceId}:${dedupe.revision}:${dedupe.state}`;
  }
  if ("operation" in dedupe) {
    return `request:${dedupe.operation}:${dedupe.sourceId || ""}:${dedupe.errorCode}:${dedupe.attemptIdentity}`;
  }
  return `unknown:${Date.now()}`;
}

export interface TransientNotification {
  id: string;
  dedupeKey: string;
  type: NotificationType;
  title: string;
  message?: string;
  read: boolean;
  createdAt: number;
  actionLabel?: string;
  onAction?: () => void;
}

type NotificationListener = (notifications: TransientNotification[]) => void;

class TransientNotificationStore {
  private notifications: TransientNotification[] = [];
  private listeners: Set<NotificationListener> = new Set();
  private nextId = 1;

  public notify(options: {
    dedupe: DedupeInput;
    type: NotificationType;
    title: string;
    message?: string;
    actionLabel?: string;
    onAction?: () => void;
  }): TransientNotification {
    const dedupeKey = buildDedupeKey(options.dedupe);
    const existingIndex = this.notifications.findIndex((n) => n.dedupeKey === dedupeKey);

    const notification: TransientNotification = {
      id: `notif-${this.nextId++}`,
      dedupeKey,
      type: options.type,
      title: options.title,
      message: options.message,
      read: false,
      createdAt: Date.now(),
      actionLabel: options.actionLabel,
      onAction: options.onAction,
    };

    if (existingIndex >= 0) {
      // Replace existing with updated timestamp and unread state
      this.notifications[existingIndex] = notification;
    } else {
      this.notifications.unshift(notification);
    }

    // Keep max 50 recent notifications
    if (this.notifications.length > 50) {
      this.notifications = this.notifications.slice(0, 50);
    }

    this.emit();
    return notification;
  }

  public markAsRead(id: string): void {
    const target = this.notifications.find((n) => n.id === id);
    if (target && !target.read) {
      target.read = true;
      this.emit();
    }
  }

  public markAllAsRead(): void {
    let changed = false;
    for (const n of this.notifications) {
      if (!n.read) {
        n.read = true;
        changed = true;
      }
    }
    if (changed) {
      this.emit();
    }
  }

  public dismiss(id: string): void {
    const before = this.notifications.length;
    this.notifications = this.notifications.filter((n) => n.id !== id);
    if (this.notifications.length !== before) {
      this.emit();
    }
  }

  public clearAll(): void {
    if (this.notifications.length > 0) {
      this.notifications = [];
      this.emit();
    }
  }

  public getNotifications(): TransientNotification[] {
    return [...this.notifications];
  }

  public getUnreadCount(): number {
    return this.notifications.filter((n) => !n.read).length;
  }

  public subscribe(listener: NotificationListener): () => void {
    this.listeners.add(listener);
    listener(this.getNotifications());
    return () => {
      this.listeners.delete(listener);
    };
  }

  private emit(): void {
    const copy = this.getNotifications();
    for (const listener of this.listeners) {
      listener(copy);
    }
  }
}

export const notificationStore = new TransientNotificationStore();

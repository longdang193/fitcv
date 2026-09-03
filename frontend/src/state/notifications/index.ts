/**
 * FitCV Client-Side Transient Notifications Store
 * Session-scoped, client-owned projection with priority deduplication.
 * Spec: docs/superpowers/specs/2026-08-29-fitcv-client-transient-notifications-spec.md
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
  sourceType?: string;
  sourceId?: string;
  href?: string;
}

type NotificationListener = (notifications: TransientNotification[]) => void;

const STORAGE_KEY = "fitcv:session_notifications:v1";

function isSafeHref(href: unknown): href is string {
  return (
    typeof href === "string" &&
    (href.startsWith("#/") || href.startsWith("/app/#/"))
  );
}

function isNotification(value: unknown): value is TransientNotification {
  if (!value || typeof value !== "object") return false;
  const notification = value as Partial<TransientNotification>;
  return (
    typeof notification.id === "string" && notification.id.trim().length > 0 &&
    typeof notification.dedupeKey === "string" && notification.dedupeKey.trim().length > 0 &&
    typeof notification.title === "string" && notification.title.trim().length > 0 &&
    ["info", "success", "warning", "error"].includes(notification.type as string) &&
    typeof notification.read === "boolean" &&
    typeof notification.createdAt === "number" && Number.isFinite(notification.createdAt) &&
    (notification.message === undefined || typeof notification.message === "string") &&
    (notification.actionLabel === undefined ||
      (typeof notification.actionLabel === "string" &&
        notification.actionLabel.trim().length > 0 &&
        isSafeHref(notification.href))) &&
    (notification.href === undefined || isSafeHref(notification.href)) &&
    (notification.sourceType === undefined || typeof notification.sourceType === "string") &&
    (notification.sourceId === undefined || typeof notification.sourceId === "string")
  );
}

export class TransientNotificationStore {
  private notifications: TransientNotification[] = [];
  private listeners: Set<NotificationListener> = new Set();
  private nextId = 1;

  constructor() {
    this.loadFromSessionStorage();
  }

  private loadFromSessionStorage(): void {
    if (typeof window === "undefined" || !window.sessionStorage) return;
    try {
      const raw = window.sessionStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          this.notifications = parsed.filter(isNotification).slice(0, 50);
          const maxId = this.notifications.reduce((acc, n) => {
            const num = parseInt(String(n.id).replace(/[^0-9]/g, ""), 10);
            return isNaN(num) ? acc : Math.max(acc, num);
          }, 0);
          this.nextId = maxId + 1;
        }
      }
    } catch {
      this.notifications = [];
    }
  }

  private saveToSessionStorage(): void {
    if (typeof window === "undefined" || !window.sessionStorage) return;
    try {
      const serializable = this.notifications.map(({ onAction, actionLabel, ...rest }) => ({
        ...rest,
        ...(rest.href ? { actionLabel } : {}),
      }));
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(serializable));
    } catch {
      // Non-critical transient storage error tolerated
    }
  }

  public notify(options: {
    dedupe: DedupeInput;
    type: NotificationType;
    title: string;
    message?: string;
    actionLabel?: string;
    onAction?: () => void;
    sourceType?: string;
    sourceId?: string;
    href?: string;
  }): TransientNotification {
    const dedupeKey = buildDedupeKey(options.dedupe);
    const safeHref = isSafeHref(options.href) ? options.href : undefined;
    const actionLabel = options.actionLabel && (safeHref || options.onAction)
      ? options.actionLabel
      : undefined;
    const existingIndex = this.notifications.findIndex((n) => n.dedupeKey === dedupeKey);

    if (existingIndex >= 0) {
      const existing = this.notifications[existingIndex];
      const updated: TransientNotification = {
        id: existing.id,
        dedupeKey,
        type: options.type,
        title: options.title,
        message: options.message,
        read: false,
        createdAt: Date.now(),
        actionLabel,
        onAction: options.onAction,
        sourceType: options.sourceType,
        sourceId: options.sourceId,
        href: safeHref,
      };
      this.notifications[existingIndex] = updated;
      this.saveToSessionStorage();
      this.emit();
      return updated;
    }

    const notification: TransientNotification = {
      id: `notif-${this.nextId++}`,
      dedupeKey,
      type: options.type,
      title: options.title,
      message: options.message,
      read: false,
      createdAt: Date.now(),
      actionLabel,
      onAction: options.onAction,
      sourceType: options.sourceType,
      sourceId: options.sourceId,
      href: safeHref,
    };

    this.notifications.unshift(notification);

    if (this.notifications.length > 50) {
      this.notifications = this.notifications.slice(0, 50);
    }

    this.saveToSessionStorage();
    this.emit();
    return notification;
  }

  public markAsRead(id: string): void {
    const target = this.notifications.find((n) => n.id === id);
    if (target && !target.read) {
      target.read = true;
      this.saveToSessionStorage();
      this.emit();
    }
  }

  public activateAction(id: string): void {
    const target = this.notifications.find((n) => n.id === id);
    if (!target?.onAction) return;
    this.markAsRead(id);
    target.onAction();
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
      this.saveToSessionStorage();
      this.emit();
    }
  }

  public dismiss(id: string): void {
    const before = this.notifications.length;
    this.notifications = this.notifications.filter((n) => n.id !== id);
    if (this.notifications.length !== before) {
      this.saveToSessionStorage();
      this.emit();
    }
  }

  public clearAll(): void {
    if (this.notifications.length > 0) {
      this.notifications = [];
      this.saveToSessionStorage();
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

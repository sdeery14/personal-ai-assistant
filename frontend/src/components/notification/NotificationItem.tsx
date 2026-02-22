"use client";

import type { Notification } from "@/types/notification";
import { Button } from "@/components/ui";

interface NotificationItemProps {
  notification: Notification;
  onMarkAsRead: (id: string) => void;
  onDismiss: (id: string) => void;
}

const typeConfig: Record<string, { icon: string; color: string }> = {
  reminder: {
    icon: "\u{1F551}",
    color: "text-blue-500 dark:text-blue-400",
  },
  info: {
    icon: "\u{2139}\u{FE0F}",
    color: "text-gray-500 dark:text-gray-400",
  },
  warning: {
    icon: "\u{26A0}\u{FE0F}",
    color: "text-amber-500 dark:text-amber-400",
  },
};

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export function NotificationItem({
  notification,
  onMarkAsRead,
  onDismiss,
}: NotificationItemProps) {
  const config = typeConfig[notification.type] || typeConfig.info;

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 border-b border-gray-100 dark:border-gray-700 last:border-b-0 ${
        notification.is_read
          ? "bg-white dark:bg-gray-800"
          : "bg-blue-50 dark:bg-gray-750"
      }`}
    >
      <span className={`mt-0.5 text-base ${config.color}`} aria-hidden="true">
        {config.icon}
      </span>
      <div className="flex-1 min-w-0">
        <p
          className={`text-sm ${
            notification.is_read
              ? "text-gray-600 dark:text-gray-400"
              : "text-gray-900 dark:text-gray-100 font-medium"
          }`}
        >
          {notification.message}
        </p>
        <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
          {formatRelativeTime(notification.created_at)}
        </p>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        {!notification.is_read && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onMarkAsRead(notification.id)}
            className="text-xs text-gray-400 hover:text-blue-500 dark:text-gray-500 dark:hover:text-blue-400 px-1"
            aria-label="Mark as read"
          >
            Mark read
          </Button>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDismiss(notification.id)}
          className="text-xs text-gray-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400 px-1"
          aria-label="Dismiss notification"
        >
          &times;
        </Button>
      </div>
    </div>
  );
}

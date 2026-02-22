"use client";

import { useState } from "react";
import { useNotifications } from "@/hooks/useNotifications";
import { NotificationItem } from "@/components/notification/NotificationItem";
import { NotificationPreferences } from "@/components/notification/NotificationPreferences";
import { Button } from "@/components/ui";

export default function NotificationsPage() {
  const {
    notifications,
    total,
    isLoading,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    dismiss,
  } = useNotifications();

  const [showPreferences, setShowPreferences] = useState(false);

  return (
    <div className="mx-auto max-w-2xl p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Notifications
        </h1>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={markAllAsRead}
            className="text-xs"
          >
            Mark all as read
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowPreferences(!showPreferences)}
            className="text-xs"
          >
            {showPreferences ? "Hide settings" : "Settings"}
          </Button>
        </div>
      </div>

      {showPreferences && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <NotificationPreferences onClose={() => setShowPreferences(false)} />
        </div>
      )}

      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
        {isLoading && notifications.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
            Loading notifications...
          </div>
        ) : notifications.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
            No notifications yet
          </div>
        ) : (
          <>
            {notifications.map((n) => (
              <NotificationItem
                key={n.id}
                notification={n}
                onMarkAsRead={markAsRead}
                onDismiss={dismiss}
              />
            ))}
            {notifications.length < total && (
              <div className="p-3 text-center">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => fetchNotifications(notifications.length)}
                  className="text-xs"
                >
                  Load more
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

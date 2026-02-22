"use client";

import { useState, useCallback, useEffect } from "react";
import { useSession } from "next-auth/react";
import type { Notification } from "@/types/notification";
import { apiClient } from "@/lib/api-client";

export function useNotifications() {
  const { data: session } = useSession();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  const fetchNotifications = useCallback(
    async (offset = 0) => {
      if (!session?.accessToken) return;
      setIsLoading(true);
      try {
        const data = await apiClient.getNotifications({ limit: 20, offset });
        if (offset === 0) {
          setNotifications(data.items);
        } else {
          setNotifications((prev) => [...prev, ...data.items]);
        }
        setTotal(data.total);
      } catch {
        // silently fail
      } finally {
        setIsLoading(false);
      }
    },
    [session?.accessToken],
  );

  const fetchUnreadCount = useCallback(async () => {
    if (!session?.accessToken) return;
    try {
      const data = await apiClient.getUnreadCount();
      setUnreadCount(data.count);
    } catch {
      // silently fail
    }
  }, [session?.accessToken]);

  const markAsRead = useCallback(
    async (id: string) => {
      if (!session?.accessToken) return;
      // Optimistic update
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
      try {
        await apiClient.markNotificationAsRead(id);
      } catch {
        // Revert on failure
        fetchNotifications();
        fetchUnreadCount();
      }
    },
    [session?.accessToken, fetchNotifications, fetchUnreadCount],
  );

  const markAllAsRead = useCallback(async () => {
    if (!session?.accessToken) return;
    // Optimistic update
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
    try {
      await apiClient.markAllNotificationsAsRead();
    } catch {
      // Revert on failure
      fetchNotifications();
      fetchUnreadCount();
    }
  }, [session?.accessToken, fetchNotifications, fetchUnreadCount]);

  const dismiss = useCallback(
    async (id: string) => {
      if (!session?.accessToken) return;
      const dismissed = notifications.find((n) => n.id === id);
      // Optimistic update
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      setTotal((prev) => prev - 1);
      if (dismissed && !dismissed.is_read) {
        setUnreadCount((prev) => Math.max(0, prev - 1));
      }
      try {
        await apiClient.dismissNotification(id);
      } catch {
        // Revert on failure
        fetchNotifications();
        fetchUnreadCount();
      }
    },
    [session?.accessToken, notifications, fetchNotifications, fetchUnreadCount],
  );

  // Fetch on mount
  useEffect(() => {
    fetchNotifications();
    fetchUnreadCount();
  }, [fetchNotifications, fetchUnreadCount]);

  return {
    notifications,
    unreadCount,
    total,
    isLoading,
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
    dismiss,
  };
}

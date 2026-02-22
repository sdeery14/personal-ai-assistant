"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { Button } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import type {
  NotificationPreferences as Prefs,
  DeliveryChannel,
} from "@/types/notification";

interface NotificationPreferencesProps {
  onClose: () => void;
}

export function NotificationPreferences({ onClose }: NotificationPreferencesProps) {
  const { data: session } = useSession();
  const [deliveryChannel, setDeliveryChannel] = useState<DeliveryChannel>("in_app");
  const [quietStart, setQuietStart] = useState("");
  const [quietEnd, setQuietEnd] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchPreferences = useCallback(async () => {
    if (!session?.accessToken) return;
    setIsLoading(true);
    try {
      const prefs = await apiClient.getNotificationPreferences();
      setDeliveryChannel(prefs.delivery_channel);
      setQuietStart(prefs.quiet_hours_start || "");
      setQuietEnd(prefs.quiet_hours_end || "");
      setTimezone(prefs.quiet_hours_timezone || "UTC");
    } catch {
      // use defaults
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken]);

  useEffect(() => {
    fetchPreferences();
  }, [fetchPreferences]);

  const handleSave = async () => {
    setIsSaving(true);
    setMessage(null);
    try {
      await apiClient.updateNotificationPreferences({
        delivery_channel: deliveryChannel,
        quiet_hours_start: quietStart || null,
        quiet_hours_end: quietEnd || null,
        quiet_hours_timezone: timezone,
      });
      setMessage({ type: "success", text: "Preferences saved" });
    } catch {
      setMessage({ type: "error", text: "Failed to save preferences" });
    } finally {
      setIsSaving(false);
    }
  };

  const showQuietHours = deliveryChannel === "email" || deliveryChannel === "both";

  if (isLoading) {
    return (
      <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
        Loading preferences...
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          Notification Preferences
        </h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          aria-label="Close preferences"
        >
          &times;
        </button>
      </div>

      {/* Delivery Channel */}
      <div>
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
          Delivery Channel
        </label>
        <div className="space-y-1">
          {(["in_app", "email", "both"] as DeliveryChannel[]).map((channel) => (
            <label key={channel} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="delivery_channel"
                value={channel}
                checked={deliveryChannel === channel}
                onChange={() => setDeliveryChannel(channel)}
                className="text-blue-600"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {channel === "in_app"
                  ? "In-app only"
                  : channel === "email"
                    ? "Email only"
                    : "Both in-app and email"}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Quiet Hours (shown when email is enabled) */}
      {showQuietHours && (
        <div className="space-y-2">
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
            Email Quiet Hours
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Emails during quiet hours will be deferred until quiet hours end.
          </p>
          <div className="flex items-center gap-2">
            <input
              type="time"
              value={quietStart}
              onChange={(e) => setQuietStart(e.target.value)}
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm px-2 py-1 text-gray-900 dark:text-gray-100"
              placeholder="Start"
            />
            <span className="text-xs text-gray-500">to</span>
            <input
              type="time"
              value={quietEnd}
              onChange={(e) => setQuietEnd(e.target.value)}
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm px-2 py-1 text-gray-900 dark:text-gray-100"
              placeholder="End"
            />
          </div>
          <select
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm px-2 py-1 text-gray-900 dark:text-gray-100"
          >
            <option value="UTC">UTC</option>
            <option value="America/New_York">Eastern (US)</option>
            <option value="America/Chicago">Central (US)</option>
            <option value="America/Denver">Mountain (US)</option>
            <option value="America/Los_Angeles">Pacific (US)</option>
            <option value="Europe/London">London</option>
            <option value="Europe/Berlin">Central Europe</option>
            <option value="Asia/Tokyo">Tokyo</option>
          </select>
        </div>
      )}

      {/* Status Message */}
      {message && (
        <p
          className={`text-xs ${
            message.type === "success"
              ? "text-green-600 dark:text-green-400"
              : "text-red-600 dark:text-red-400"
          }`}
        >
          {message.text}
        </p>
      )}

      {/* Save Button */}
      <Button
        onClick={handleSave}
        size="sm"
        className="w-full"
        disabled={isSaving}
      >
        {isSaving ? "Saving..." : "Save Preferences"}
      </Button>
    </div>
  );
}

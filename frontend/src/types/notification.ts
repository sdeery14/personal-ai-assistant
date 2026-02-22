export type NotificationType = "reminder" | "info" | "warning";

export type DeliveryChannel = "in_app" | "email" | "both";

export interface Notification {
  id: string;
  message: string;
  type: NotificationType;
  is_read: boolean;
  conversation_id: string | null;
  created_at: string;
}

export interface NotificationPreferences {
  delivery_channel: DeliveryChannel;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  quiet_hours_timezone: string;
}

export interface NotificationPreferencesUpdate {
  delivery_channel?: DeliveryChannel;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  quiet_hours_timezone?: string;
}

export interface PaginatedNotifications {
  items: Notification[];
  total: number;
  limit: number;
  offset: number;
}

export interface UnreadCountResponse {
  count: number;
}

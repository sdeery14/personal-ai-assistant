import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { NotificationBell } from "../NotificationBell";
import type { Notification } from "@/types/notification";

// Mock useNotifications hook
const mockFetchNotifications = vi.fn();
const mockFetchUnreadCount = vi.fn();
const mockMarkAsRead = vi.fn();
const mockMarkAllAsRead = vi.fn();
const mockDismiss = vi.fn();

const defaultHookReturn = {
  notifications: [] as Notification[],
  unreadCount: 0,
  total: 0,
  isLoading: false,
  fetchNotifications: mockFetchNotifications,
  fetchUnreadCount: mockFetchUnreadCount,
  markAsRead: mockMarkAsRead,
  markAllAsRead: mockMarkAllAsRead,
  dismiss: mockDismiss,
};

vi.mock("@/hooks/useNotifications", () => ({
  useNotifications: () => defaultHookReturn,
}));

// Mock next-auth
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: { accessToken: "test-token", user: { name: "Test" } } }),
  getSession: () => Promise.resolve({ accessToken: "test-token" }),
}));

function makeNotification(overrides: Partial<Notification> = {}): Notification {
  return {
    id: "n-1",
    message: "Test notification",
    type: "info",
    is_read: false,
    conversation_id: null,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

describe("NotificationBell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    defaultHookReturn.notifications = [];
    defaultHookReturn.unreadCount = 0;
    defaultHookReturn.isLoading = false;
  });

  it("renders bell icon", () => {
    render(<NotificationBell />);
    const button = screen.getByRole("button", { name: /notifications/i });
    expect(button).toBeInTheDocument();
  });

  it("shows unread count badge when count > 0", () => {
    defaultHookReturn.unreadCount = 3;
    render(<NotificationBell />);
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("hides badge when unread count is 0", () => {
    defaultHookReturn.unreadCount = 0;
    render(<NotificationBell />);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("shows 99+ for large counts", () => {
    defaultHookReturn.unreadCount = 150;
    render(<NotificationBell />);
    expect(screen.getByText("99+")).toBeInTheDocument();
  });

  it("toggles panel visibility on click", () => {
    render(<NotificationBell />);
    const button = screen.getByRole("button", { name: /notifications/i });

    // Panel not visible initially
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    // Click to open
    fireEvent.click(button);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    // Click to close
    fireEvent.click(button);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows notification list in panel", () => {
    defaultHookReturn.notifications = [
      makeNotification({ id: "n-1", message: "First notification" }),
      makeNotification({ id: "n-2", message: "Second notification" }),
    ];

    render(<NotificationBell />);
    fireEvent.click(screen.getByRole("button", { name: /notifications/i }));

    expect(screen.getByText("First notification")).toBeInTheDocument();
    expect(screen.getByText("Second notification")).toBeInTheDocument();
  });

  it("shows empty state when no notifications", () => {
    defaultHookReturn.notifications = [];

    render(<NotificationBell />);
    fireEvent.click(screen.getByRole("button", { name: /notifications/i }));

    expect(screen.getByText("No notifications yet")).toBeInTheDocument();
  });

  it("refreshes data when panel is opened", () => {
    render(<NotificationBell />);
    fireEvent.click(screen.getByRole("button", { name: /notifications/i }));

    expect(mockFetchNotifications).toHaveBeenCalled();
    expect(mockFetchUnreadCount).toHaveBeenCalled();
  });
});

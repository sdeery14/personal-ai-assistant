"use client";

import { StreamError } from "@/lib/chat-stream";
import { Button } from "@/components/ui";

interface ChatErrorProps {
  error: StreamError;
  onRetry?: () => void;
}

const errorMessages: Record<StreamError["type"], { title: string; action: string }> = {
  connection: {
    title: "Connection lost",
    action: "Retry",
  },
  timeout: {
    title: "Request timed out",
    action: "Try again",
  },
  guardrail_violation: {
    title: "Message blocked",
    action: "Try rephrasing",
  },
  server_error: {
    title: "Something went wrong",
    action: "Retry",
  },
};

export function ChatError({ error, onRetry }: ChatErrorProps) {
  const config = errorMessages[error.type];

  return (
    <div className="mx-4 mb-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-red-800">{config.title}</p>
          <p className="mt-0.5 text-xs text-red-600">{error.message}</p>
        </div>
        {onRetry && error.type !== "guardrail_violation" && (
          <Button variant="ghost" size="sm" onClick={onRetry}>
            {config.action}
          </Button>
        )}
      </div>
    </div>
  );
}

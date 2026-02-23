import { StreamChunk } from "@/types/chat";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatStreamOptions {
  message?: string;
  conversationId?: string;
  accessToken: string;
  signal?: AbortSignal;
}

export type StreamError = {
  type: "connection" | "timeout" | "guardrail_violation" | "server_error";
  message: string;
};

/**
 * Async generator that streams SSE chat responses from the backend.
 * Uses fetch + ReadableStream (not EventSource) because we need POST + auth headers.
 */
export async function* chatStream(
  options: ChatStreamOptions,
): AsyncGenerator<StreamChunk | StreamError> {
  const { message, conversationId, accessToken, signal } = options;

  const body: Record<string, unknown> = { message: message ?? "" };
  if (conversationId) {
    body.conversation_id = conversationId;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return;
    }
    yield {
      type: "connection",
      message: "Cannot connect to the server. Please check your connection and try again.",
    };
    return;
  }

  if (response.status === 401) {
    yield {
      type: "server_error",
      message: "Session expired. Please log in again.",
    };
    return;
  }

  if (!response.ok) {
    yield {
      type: "server_error",
      message: `Server error (${response.status}). Please try again.`,
    };
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    yield {
      type: "connection",
      message: "Failed to read server response.",
    };
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE events (terminated by double newline)
      const events = buffer.split("\n\n");
      // Keep the last potentially incomplete event in the buffer
      buffer = events.pop() || "";

      for (const event of events) {
        const line = event.trim();
        if (!line.startsWith("data: ")) continue;

        const jsonStr = line.slice(6);
        try {
          const chunk = JSON.parse(jsonStr) as StreamChunk & {
            error?: string;
            error_type?: string;
          };

          if (chunk.error) {
            const errorType = chunk.error_type?.includes("guardrail")
              ? "guardrail_violation"
              : chunk.error?.includes("timed out")
                ? "timeout"
                : "server_error";

            yield {
              type: errorType,
              message: chunk.error,
            } as StreamError;
            return;
          }

          yield chunk as StreamChunk;
        } catch {
          // Skip malformed JSON
        }
      }
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return;
    }
    yield {
      type: "connection",
      message: "Connection lost during streaming. Please try again.",
    };
  } finally {
    reader.releaseLock();
  }
}

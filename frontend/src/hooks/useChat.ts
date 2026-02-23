"use client";

import { useCallback, useRef } from "react";
import { useSession } from "next-auth/react";
import { useChatStore } from "@/stores/chat-store";
import { chatStream, StreamError } from "@/lib/chat-stream";
import { StreamChunk } from "@/types/chat";

export function useChat() {
  const { data: session } = useSession();
  const abortControllerRef = useRef<AbortController | null>(null);

  const {
    messages,
    conversationId,
    isStreaming,
    error,
    lastFailedMessage,
    greetingRequested,
    addUserMessage,
    addAssistantMessage,
    appendStreamChunk,
    finalizeStream,
    setStreaming,
    setError,
    setLastFailedMessage,
    setGreetingRequested,
    clearMessages,
  } = useChatStore();

  /**
   * Shared streaming logic. When `message` is provided, it's a normal chat.
   * When omitted, it triggers an auto-greeting (no user bubble).
   */
  const streamResponse = useCallback(
    async (message?: string) => {
      const accessToken = (session as { accessToken?: string })?.accessToken;
      if (!accessToken) {
        setError({
          type: "server_error",
          message: "Session expired. Please log in again.",
        });
        return;
      }

      // Abort any existing stream
      abortControllerRef.current?.abort();
      const controller = new AbortController();
      abortControllerRef.current = controller;

      setStreaming(true);
      setError(null);
      setLastFailedMessage(null);

      // Create placeholder for assistant response
      const assistantId = addAssistantMessage();

      try {
        const stream = chatStream({
          message: message || undefined,
          conversationId: conversationId || undefined,
          accessToken,
          signal: controller.signal,
        });

        for await (const event of stream) {
          if ("type" in event && typeof (event as StreamError).type === "string" && "message" in event && !("sequence" in event)) {
            // This is a StreamError
            const streamError = event as StreamError;
            setError(streamError);
            if (message) {
              setLastFailedMessage(message);
            }
            // Remove the empty assistant message
            useChatStore.setState((state) => ({
              messages: state.messages.filter((m) => m.id !== assistantId),
            }));
            return;
          }

          // This is a StreamChunk
          const chunk = event as StreamChunk;
          if (chunk.content) {
            appendStreamChunk(assistantId, chunk.content);
          }
          if (chunk.is_final) {
            finalizeStream(assistantId, chunk.conversation_id || undefined);
          }
        }

        // If stream ended without a final chunk, finalize anyway
        finalizeStream(assistantId);
      } catch {
        // Unexpected error
        setError({
          type: "connection",
          message: "An unexpected error occurred. Please try again.",
        });
        if (message) {
          setLastFailedMessage(message);
        }
        useChatStore.setState((state) => ({
          messages: state.messages.filter((m) => m.id !== assistantId),
        }));
      }
    },
    [
      session,
      conversationId,
      addAssistantMessage,
      appendStreamChunk,
      finalizeStream,
      setStreaming,
      setError,
      setLastFailedMessage,
    ],
  );

  const sendMessage = useCallback(
    async (content: string) => {
      addUserMessage(content);
      await streamResponse(content);
    },
    [addUserMessage, streamResponse],
  );

  const requestGreeting = useCallback(async () => {
    setGreetingRequested(true);
    await streamResponse();
  }, [setGreetingRequested, streamResponse]);

  const retry = useCallback(() => {
    if (lastFailedMessage) {
      sendMessage(lastFailedMessage);
    }
  }, [lastFailedMessage, sendMessage]);

  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort();
    setStreaming(false);
  }, [setStreaming]);

  return {
    messages,
    conversationId,
    isStreaming,
    error,
    lastFailedMessage,
    greetingRequested,
    sendMessage,
    requestGreeting,
    retry,
    stopStreaming,
    clearMessages,
  };
}

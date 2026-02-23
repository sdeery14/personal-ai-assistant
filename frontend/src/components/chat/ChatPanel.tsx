"use client";

import { useEffect } from "react";
import { useChat } from "@/hooks/useChat";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import { ChatError } from "./ChatError";

export function ChatPanel() {
  const {
    messages,
    isStreaming,
    error,
    greetingRequested,
    sendMessage,
    requestGreeting,
    retry,
    stopStreaming,
  } = useChat();

  // Auto-trigger greeting when conversation is empty
  useEffect(() => {
    if (messages.length === 0 && !isStreaming && !greetingRequested) {
      requestGreeting();
    }
  }, [messages.length, isStreaming, greetingRequested, requestGreeting]);

  return (
    <div className="flex h-full flex-col">
      <MessageList messages={messages} isStreaming={isStreaming} />
      {error && <ChatError error={error} onRetry={retry} />}
      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}

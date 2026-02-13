"use client";

import { useChat } from "@/hooks/useChat";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import { ChatError } from "./ChatError";

export function ChatPanel() {
  const { messages, isStreaming, error, sendMessage, retry, stopStreaming } =
    useChat();

  return (
    <div className="flex h-full flex-col">
      <MessageList messages={messages} isStreaming={isStreaming} />
      {error && <ChatError error={error} onRetry={retry} />}
      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}

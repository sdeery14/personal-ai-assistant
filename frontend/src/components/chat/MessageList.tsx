"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { ChatMessage } from "@/types/chat";
import { MessageBubble } from "./MessageBubble";
import { StreamingIndicator } from "./StreamingIndicator";

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
}

export function MessageList({ messages, isStreaming }: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [userScrolledUp, setUserScrolledUp] = useState(false);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // Track if user has scrolled up
  const handleScroll = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setUserScrolledUp(!isAtBottom);
  }, []);

  // Auto-scroll on new content unless user scrolled up
  useEffect(() => {
    if (!userScrolledUp) {
      scrollToBottom();
    }
  }, [messages, isStreaming, userScrolledUp, scrollToBottom]);

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            Start a conversation
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Type a message below to begin.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-4 py-4"
    >
      <div className="mx-auto max-w-3xl space-y-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isStreaming &&
          !messages.some((m) => m.role === "assistant" && m.isStreaming) && (
            <StreamingIndicator />
          )}
        <div ref={bottomRef} />
      </div>

      {userScrolledUp && isStreaming && (
        <button
          onClick={() => {
            setUserScrolledUp(false);
            scrollToBottom();
          }}
          className="fixed bottom-24 right-8 rounded-full bg-blue-600 px-3 py-1.5 text-xs text-white shadow-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
        >
          Scroll to bottom
        </button>
      )}
    </div>
  );
}

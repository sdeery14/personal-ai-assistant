"use client";

import { useState, useCallback, useEffect } from "react";
import { useSession } from "next-auth/react";
import { ConversationSummary, PaginatedResponse } from "@/types/chat";
import { apiClient } from "@/lib/api-client";
import { useChatStore } from "@/stores/chat-store";

export function useConversations() {
  const { data: session } = useSession();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  const { conversationId, setConversationId, clearMessages, loadMessages } =
    useChatStore();

  const fetchConversations = useCallback(
    async (offset = 0) => {
      if (!session?.accessToken) return;
      setIsLoading(true);
      try {
        const data = await apiClient.get<PaginatedResponse<ConversationSummary>>(
          "/conversations",
          { limit: 50, offset },
        );
        if (offset === 0) {
          setConversations(data.items);
        } else {
          setConversations((prev) => [...prev, ...data.items]);
        }
        setTotal(data.total);
      } catch {
        // silently fail — conversations list is non-critical
      } finally {
        setIsLoading(false);
      }
    },
    [session?.accessToken],
  );

  const selectConversation = useCallback(
    async (id: string) => {
      if (!session?.accessToken) return;
      setConversationId(id);
      try {
        const data = await apiClient.get<{
          id: string;
          title: string | null;
          messages: { id: string; role: "user" | "assistant" | "system"; content: string; created_at: string }[];
        }>(`/conversations/${id}`);

        loadMessages(
          data.messages.map((m) => ({
            id: m.id,
            role: m.role as "user" | "assistant",
            content: m.content,
            isStreaming: false,
            timestamp: new Date(m.created_at),
          })),
        );
      } catch {
        // If conversation fails to load, clear state
        clearMessages();
      }
    },
    [session?.accessToken, setConversationId, loadMessages, clearMessages],
  );

  const newConversation = useCallback(() => {
    clearMessages();
  }, [clearMessages]);

  const renameConversation = useCallback(
    async (id: string, title: string) => {
      if (!session?.accessToken) return;
      try {
        await apiClient.patch(`/conversations/${id}`, { title });
        setConversations((prev) =>
          prev.map((c) => (c.id === id ? { ...c, title } : c)),
        );
      } catch {
        // silently fail
      }
    },
    [session?.accessToken],
  );

  const deleteConversation = useCallback(
    async (id: string) => {
      if (!session?.accessToken) return;
      try {
        await apiClient.del(`/conversations/${id}`);
        setConversations((prev) => prev.filter((c) => c.id !== id));
        setTotal((prev) => prev - 1);
        if (conversationId === id) {
          clearMessages();
        }
      } catch {
        // silently fail
      }
    },
    [session?.accessToken, conversationId, clearMessages],
  );

  // Load conversations on mount
  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  return {
    conversations,
    total,
    isLoading,
    conversationId,
    fetchConversations,
    selectConversation,
    newConversation,
    renameConversation,
    deleteConversation,
  };
}

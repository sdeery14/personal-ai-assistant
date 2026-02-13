"use client";

import { ConversationSummary } from "@/types/chat";
import { ConversationItem } from "./ConversationItem";
import { Button } from "@/components/ui";

interface ConversationListProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  total: number;
  isLoading: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
  onLoadMore: () => void;
}

export function ConversationList({
  conversations,
  activeId,
  total,
  isLoading,
  onSelect,
  onNew,
  onRename,
  onDelete,
  onLoadMore,
}: ConversationListProps) {
  const hasMore = conversations.length < total;

  return (
    <div className="flex flex-col h-full">
      <div className="p-3">
        <Button variant="primary" size="sm" className="w-full" onClick={onNew}>
          New conversation
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
        {conversations.map((conv) => (
          <ConversationItem
            key={conv.id}
            conversation={conv}
            isActive={conv.id === activeId}
            onSelect={onSelect}
            onRename={onRename}
            onDelete={onDelete}
          />
        ))}
        {conversations.length === 0 && !isLoading && (
          <p className="px-3 py-4 text-center text-xs text-gray-400 dark:text-gray-500">
            No conversations yet
          </p>
        )}
        {hasMore && (
          <div className="p-2">
            <Button
              variant="ghost"
              size="sm"
              className="w-full"
              onClick={onLoadMore}
              isLoading={isLoading}
            >
              Load more
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

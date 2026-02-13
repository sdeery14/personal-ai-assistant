"use client";

import { useState, useRef, useCallback, KeyboardEvent } from "react";
import { ConversationSummary } from "@/types/chat";

interface ConversationItemProps {
  conversation: ConversationSummary;
  isActive: boolean;
  onSelect: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}

export function ConversationItem({
  conversation,
  isActive,
  onSelect,
  onRename,
  onDelete,
}: ConversationItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const title = conversation.title || conversation.message_preview || "New conversation";

  const startEditing = useCallback(() => {
    setEditValue(title);
    setIsEditing(true);
    setTimeout(() => inputRef.current?.focus(), 0);
  }, [title]);

  const commitRename = useCallback(() => {
    const trimmed = editValue.trim();
    if (trimmed && trimmed !== title) {
      onRename(conversation.id, trimmed);
    }
    setIsEditing(false);
  }, [editValue, title, conversation.id, onRename]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        commitRename();
      } else if (e.key === "Escape") {
        setIsEditing(false);
      }
    },
    [commitRename],
  );

  return (
    <div
      className={`group flex items-center gap-2 rounded-md px-3 py-2 text-sm cursor-pointer transition-colors ${
        isActive
          ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
          : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
      }`}
      onClick={() => !isEditing && onSelect(conversation.id)}
      onDoubleClick={startEditing}
    >
      <div className="flex-1 min-w-0">
        {isEditing ? (
          <input
            ref={inputRef}
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={commitRename}
            onKeyDown={handleKeyDown}
            className="w-full rounded border border-gray-300 px-1 py-0.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <p className="truncate">{title}</p>
        )}
        <p className="truncate text-xs text-gray-400 dark:text-gray-500">
          {new Date(conversation.updated_at).toLocaleDateString()}
        </p>
      </div>
      {!isEditing && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(conversation.id);
          }}
          className="hidden rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-red-500 group-hover:block dark:text-gray-500 dark:hover:bg-gray-700 dark:hover:text-red-400"
          aria-label="Delete conversation"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-3.5 w-3.5">
            <path fillRule="evenodd" d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z" clipRule="evenodd" />
          </svg>
        </button>
      )}
    </div>
  );
}

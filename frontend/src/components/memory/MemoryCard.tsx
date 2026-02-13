"use client";

import { useState } from "react";
import { MemoryItem } from "@/types/memory";
import { Button, Dialog } from "@/components/ui";

interface MemoryCardProps {
  memory: MemoryItem;
  onDelete: (id: string) => void;
}

const typeBadgeColors: Record<string, string> = {
  fact: "bg-blue-100 text-blue-700",
  preference: "bg-purple-100 text-purple-700",
  decision: "bg-green-100 text-green-700",
  note: "bg-gray-100 text-gray-700",
  episode: "bg-amber-100 text-amber-700",
};

export function MemoryCard({ memory, onDelete }: MemoryCardProps) {
  const [showConfirm, setShowConfirm] = useState(false);

  const badgeColor = typeBadgeColors[memory.type] || typeBadgeColors.note;

  return (
    <>
      <div className="rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-sm">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${badgeColor}`}>
                {memory.type}
              </span>
              {memory.confidence < 0.8 && (
                <span className="text-xs text-gray-400">
                  {Math.round(memory.confidence * 100)}% confidence
                </span>
              )}
            </div>
            <p className="text-sm text-gray-900">{memory.content}</p>
            <p className="mt-2 text-xs text-gray-400">
              {new Date(memory.created_at).toLocaleDateString()}
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowConfirm(true)}
            className="shrink-0 text-gray-400 hover:text-red-500"
          >
            Delete
          </Button>
        </div>
      </div>
      <Dialog
        open={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={() => {
          onDelete(memory.id);
          setShowConfirm(false);
        }}
        title="Delete memory"
        description="Are you sure you want to delete this memory? This action cannot be undone."
        confirmLabel="Delete"
        confirmVariant="danger"
      />
    </>
  );
}

"use client";

export function StreamingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-2 text-gray-400 dark:text-gray-500">
      <span className="text-xs">Thinking</span>
      <span className="flex gap-0.5">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms] dark:bg-gray-500" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms] dark:bg-gray-500" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms] dark:bg-gray-500" />
      </span>
    </div>
  );
}

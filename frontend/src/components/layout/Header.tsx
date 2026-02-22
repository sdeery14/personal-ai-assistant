"use client";

import { useSession, signOut } from "next-auth/react";
import { Button } from "@/components/ui";
import { NotificationBell } from "@/components/notification";
import { ThemeToggle } from "./ThemeToggle";

export function Header() {
  const { data: session } = useSession();

  return (
    <header className="flex h-14 items-center justify-between border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4">
      <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">AI Assistant</h1>
      <div className="flex items-center gap-3">
        <NotificationBell />
        <ThemeToggle />
        {session?.user && (
          <>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {session.user.name}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => signOut({ callbackUrl: "/login" })}
            >
              Sign out
            </Button>
          </>
        )}
      </div>
    </header>
  );
}

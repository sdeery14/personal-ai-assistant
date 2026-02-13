"use client";

import { useSession, signOut } from "next-auth/react";
import { Button } from "@/components/ui";

export function Header() {
  const { data: session } = useSession();

  return (
    <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-4">
      <h1 className="text-lg font-semibold text-gray-900">AI Assistant</h1>
      <div className="flex items-center gap-3">
        {session?.user && (
          <>
            <span className="text-sm text-gray-600">
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

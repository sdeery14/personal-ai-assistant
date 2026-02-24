"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { Button } from "@/components/ui";
import { NotificationBell } from "@/components/notification";
import { ThemeToggle } from "./ThemeToggle";

const navItems = [
  { href: "/chat", label: "Chat" },
  { href: "/memory", label: "Memory" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/notifications", label: "Notifications" },
  { href: "/schedules", label: "Schedules" },
];

export function Header() {
  const { data: session } = useSession();
  const pathname = usePathname();
  const isAdmin = (session?.user as { isAdmin?: boolean })?.isAdmin;

  return (
    <header className="flex h-14 items-center justify-between border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4">
      <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">AI Assistant</h1>

      {/* Main navigation */}
      <nav className="hidden md:flex items-center gap-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              pathname.startsWith(item.href)
                ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                : "text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
            }`}
          >
            {item.label}
          </Link>
        ))}
        {isAdmin && (
          <Link
            href="/admin"
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              pathname.startsWith("/admin")
                ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                : "text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
            }`}
          >
            Admin
          </Link>
        )}
      </nav>

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

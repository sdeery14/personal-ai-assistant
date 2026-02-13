"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { useConversations } from "@/hooks/useConversations";
import { ConversationList } from "@/components/conversation/ConversationList";

const navItems = [
  { href: "/chat", label: "Chat" },
  { href: "/memory", label: "Memory" },
  { href: "/knowledge", label: "Knowledge" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const [mobileOpen, setMobileOpen] = useState(false);
  const {
    conversations,
    total,
    isLoading,
    conversationId,
    fetchConversations,
    selectConversation,
    newConversation,
    renameConversation,
    deleteConversation,
  } = useConversations();

  const isAdmin = (session?.user as { isAdmin?: boolean })?.isAdmin;

  const sidebarContent = (
    <>
      {/* Navigation */}
      <nav className="flex gap-1 border-b border-gray-200 dark:border-gray-700 px-3 py-2">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            onClick={() => setMobileOpen(false)}
            className={`rounded-md px-2 py-1 text-xs font-medium transition-colors ${
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
            onClick={() => setMobileOpen(false)}
            className={`rounded-md px-2 py-1 text-xs font-medium transition-colors ${
              pathname.startsWith("/admin")
                ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                : "text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
            }`}
          >
            Admin
          </Link>
        )}
      </nav>

      {/* Conversation list (only on chat page) */}
      {pathname.startsWith("/chat") && (
        <ConversationList
          conversations={conversations}
          activeId={conversationId}
          total={total}
          isLoading={isLoading}
          onSelect={(id) => {
            selectConversation(id);
            setMobileOpen(false);
          }}
          onNew={() => {
            newConversation();
            setMobileOpen(false);
          }}
          onRename={renameConversation}
          onDelete={deleteConversation}
          onLoadMore={() => fetchConversations(conversations.length)}
        />
      )}
    </>
  );

  return (
    <>
      {/* Mobile toggle button */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="fixed left-3 top-3.5 z-50 rounded-md p-1 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800 md:hidden"
        aria-label="Toggle sidebar"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
          <path fillRule="evenodd" d="M2 4.75A.75.75 0 0 1 2.75 4h14.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 4.75ZM2 10a.75.75 0 0 1 .75-.75h14.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 10Zm0 5.25a.75.75 0 0 1 .75-.75h14.5a.75.75 0 0 1 0 1.5H2.75a.75.75 0 0 1-.75-.75Z" clipRule="evenodd" />
        </svg>
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Desktop sidebar */}
      <aside className="hidden h-full w-64 flex-col border-r border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900 md:flex">
        {sidebarContent}
      </aside>

      {/* Mobile sidebar drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 flex-col border-r border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900 transition-transform md:hidden ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {sidebarContent}
      </aside>
    </>
  );
}

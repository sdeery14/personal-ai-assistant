"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const SUB_NAV_ITEMS = [
  { href: "/admin/evals", label: "Dashboard", exact: true },
  { href: "/admin/evals/agents", label: "Agents" },
  { href: "/admin/evals/experiments", label: "Experiments" },
  { href: "/admin/evals/datasets", label: "Datasets" },
  { href: "/admin/evals/trends", label: "Trends" },
];

export function EvalSubNav() {
  const pathname = usePathname();

  return (
    <nav className="flex gap-1 border-b border-gray-200 dark:border-gray-700 px-1 pb-2">
      {SUB_NAV_ITEMS.map((item) => {
        const isActive = item.exact
          ? pathname === item.href
          : pathname.startsWith(item.href);

        return (
          <Link
            key={item.href}
            href={item.href}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              isActive
                ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                : "text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

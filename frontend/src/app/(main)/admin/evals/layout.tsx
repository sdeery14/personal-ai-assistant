"use client";

import { useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { EvalSubNav } from "@/components/eval-nav/EvalSubNav";

export default function EvalsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session } = useSession();
  const router = useRouter();
  const isAdmin = (session?.user as { isAdmin?: boolean })?.isAdmin;

  useEffect(() => {
    if (session && !isAdmin) {
      router.replace("/chat");
    }
  }, [session, isAdmin, router]);

  if (!isAdmin) return null;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <EvalSubNav />
      <div className="mt-4">{children}</div>
    </div>
  );
}

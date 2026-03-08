"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Button, Card } from "@/components/ui";
import { Tabs } from "@/components/ui/Tabs";
import { TrendsTab } from "@/components/eval-dashboard/TrendsTab";
import { PromoteTab } from "@/components/eval-dashboard/PromoteTab";
import { RunEvalsTab } from "@/components/eval-dashboard/RunEvalsTab";
import { RollbackTab } from "@/components/eval-dashboard/RollbackTab";

const TABS = [
  { id: "trends", label: "Trends" },
  { id: "promote", label: "Promote" },
  { id: "run-evals", label: "Run Evals" },
  { id: "rollback", label: "Rollback" },
];

export default function EvalDashboardPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const isAdmin = (session?.user as { isAdmin?: boolean })?.isAdmin;
  const [activeTab, setActiveTab] = useState("trends");

  useEffect(() => {
    if (session && !isAdmin) {
      router.replace("/chat");
    }
  }, [session, isAdmin, router]);

  if (!isAdmin) return null;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Eval Dashboard
        </h1>
      </div>

      <Tabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="mt-4">
        {activeTab === "trends" && <TrendsTab />}
        {activeTab === "promote" && <PromoteTab />}
        {activeTab === "run-evals" && <RunEvalsTab />}
        {activeTab === "rollback" && <RollbackTab />}
      </div>
    </div>
  );
}

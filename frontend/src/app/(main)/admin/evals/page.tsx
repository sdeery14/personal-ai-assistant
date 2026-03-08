"use client";

import { useState } from "react";
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
  const [activeTab, setActiveTab] = useState("trends");

  return (
    <>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Dashboard
        </h1>
      </div>

      <Tabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="mt-4">
        {activeTab === "trends" && <TrendsTab />}
        {activeTab === "promote" && <PromoteTab />}
        {activeTab === "run-evals" && <RunEvalsTab />}
        {activeTab === "rollback" && <RollbackTab />}
      </div>
    </>
  );
}

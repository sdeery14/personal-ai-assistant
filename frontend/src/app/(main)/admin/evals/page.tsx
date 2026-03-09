"use client";

import { useState } from "react";
import { Tabs } from "@/components/ui/Tabs";
import { TrendsTab } from "@/components/eval-dashboard/TrendsTab";
import { RunEvalsTab } from "@/components/eval-dashboard/RunEvalsTab";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "run-evals", label: "Run Evals" },
];

export default function EvalDashboardPage() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Dashboard
        </h1>
      </div>

      <Tabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="mt-4">
        {activeTab === "overview" && <TrendsTab />}
        {activeTab === "run-evals" && <RunEvalsTab />}
      </div>
    </>
  );
}

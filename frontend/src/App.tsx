import { useState } from "react";
import { Zap, Database } from "lucide-react";
import { PipelinePage } from "./pages/PipelinePage";
import { RecordsPage } from "./pages/RecordsPage";
import { cn } from "./lib/utils";

type Tab = "pipeline" | "records";

const TABS = [
  { id: "pipeline" as Tab, label: "Run Pipeline", icon: Zap },
  { id: "records" as Tab, label: "Records History", icon: Database },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("pipeline");

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <div>
              <div className="text-sm font-bold leading-none text-gray-900">ArcVault</div>
              <div className="text-[10px] text-gray-400 leading-tight">Intake & Triage Pipeline</div>
            </div>
          </div>

          <nav className="flex gap-1">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  tab === id
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-500 hover:bg-gray-100 hover:text-gray-700"
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Page content */}
      <main>
        {tab === "pipeline" ? <PipelinePage /> : <RecordsPage />}
      </main>
    </div>
  );
}

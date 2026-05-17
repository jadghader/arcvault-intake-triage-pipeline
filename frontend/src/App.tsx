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
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-6 px-6 py-3">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <div>
              <div className="text-sm font-bold leading-none text-slate-900 tracking-tight">ArcVault</div>
              <div className="text-[11px] text-slate-400 leading-tight mt-0.5">Intake & Triage Pipeline</div>
            </div>
          </div>

          {/* Nav */}
          <nav className="flex gap-0.5">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  tab === id
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </button>
            ))}
          </nav>

          {/* Right side */}
          <div className="ml-auto">
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-400">
              Proof of concept
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        {tab === "pipeline" ? <PipelinePage /> : <RecordsPage />}
      </main>
    </div>
  );
}

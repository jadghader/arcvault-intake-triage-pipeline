import { useQuery } from "@tanstack/react-query";
import { Download, RefreshCw, AlertTriangle } from "lucide-react";
import type { ProcessedRecord } from "../types";
import { formatConfidence, formatTimestamp, PRIORITY_COLORS, QUEUE_COLORS } from "../lib/utils";
import { cn } from "../lib/utils";

async function fetchRecords(): Promise<ProcessedRecord[]> {
  const res = await fetch("/api/records");
  if (!res.ok) throw new Error("Failed to load records");
  return res.json();
}

function Badge({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={cn("inline-block rounded-full px-2 py-0.5 text-xs font-semibold", className)}>
      {children}
    </span>
  );
}

export function RecordsTable() {
  const {
    data: records,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["records"],
    queryFn: fetchRecords,
    refetchInterval: 10_000,
  });

  const handleExport = () => {
    window.open("/api/records/export/excel", "_blank");
  };

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">
            Records History
          </h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {records
              ? `${records.length} record${records.length !== 1 ? "s" : ""} — auto-refreshes every 10 s`
              : "Auto-refreshes every 10 s"}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
          <button
            onClick={handleExport}
            disabled={!records?.length}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-40"
          >
            <Download className="h-3.5 w-3.5" />
            Export Excel
          </button>
        </div>
      </div>

      {/* States */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load records — make sure the backend is running.
        </div>
      )}

      {records?.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-200 py-16 text-center text-slate-400">
          <p className="text-sm font-medium">No records yet</p>
          <p className="text-xs mt-1">Run a message through the pipeline to see results here.</p>
        </div>
      )}

      {records && records.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                {[
                  "ID",
                  "Source",
                  "Category",
                  "Priority",
                  "Confidence",
                  "Queue",
                  "Escalated",
                  "Timestamp",
                  "Summary",
                ].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-500"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {records.map((r) => (
                <tr
                  key={r.id}
                  className={cn(
                    "transition-colors hover:bg-slate-50",
                    r.routing.escalation_flag && "bg-red-50/40 hover:bg-red-50/70"
                  )}
                >
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-400">
                    {r.id}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-600">{r.source}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-800">
                    {r.classification.category}
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      className={
                        PRIORITY_COLORS[r.classification.priority] ?? "bg-slate-100 text-slate-600"
                      }
                    >
                      {r.classification.priority}
                    </Badge>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                    {formatConfidence(r.classification.confidence_score)}
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      className={
                        QUEUE_COLORS[r.routing.destination_queue] ?? "bg-slate-100 text-slate-600"
                      }
                    >
                      {r.routing.destination_queue}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    {r.routing.escalation_flag ? (
                      <span className="flex items-center gap-1 text-xs font-semibold text-red-600">
                        <AlertTriangle className="h-3 w-3" />
                        Yes
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-400">
                    {formatTimestamp(r.timestamp)}
                  </td>
                  <td className="max-w-xs px-4 py-3 text-xs text-slate-500">
                    <span className="line-clamp-2">{r.summary}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { Download, RefreshCw } from "lucide-react";
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
    <span className={cn("inline-block rounded-full px-2 py-0.5 text-xs font-medium", className)}>
      {children}
    </span>
  );
}

export function RecordsTable() {
  const { data: records, isLoading, error, refetch } = useQuery({
    queryKey: ["records"],
    queryFn: fetchRecords,
    refetchInterval: 10_000,
  });

  const handleExport = () => {
    window.open("/api/records/export/excel", "_blank");
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Records History
          {records && (
            <span className="ml-2 text-sm font-normal text-gray-400">({records.length})</span>
          )}
        </h2>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm hover:bg-gray-50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
          <button
            onClick={handleExport}
            disabled={!records?.length}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-40"
          >
            <Download className="h-3.5 w-3.5" />
            Export Excel
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="flex justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load records. Make sure the backend is running.
        </div>
      )}

      {records?.length === 0 && (
        <div className="py-12 text-center text-gray-400">
          No records yet — run a message through the pipeline first.
        </div>
      )}

      {records && records.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                {["ID", "Source", "Category", "Priority", "Confidence", "Queue", "Escalated", "Timestamp", "Summary"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {records.map((r) => (
                <tr key={r.id} className={cn(
                  "hover:bg-gray-50 transition-colors",
                  r.routing.escalation_flag && "bg-red-50"
                )}>
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-gray-500">{r.id}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-gray-600">{r.source}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-gray-800">{r.classification.category}</td>
                  <td className="px-4 py-3">
                    <Badge className={PRIORITY_COLORS[r.classification.priority] ?? ""}>
                      {r.classification.priority}
                    </Badge>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-gray-600">
                    {formatConfidence(r.classification.confidence_score)}
                  </td>
                  <td className="px-4 py-3">
                    <Badge className={QUEUE_COLORS[r.routing.destination_queue] ?? ""}>
                      {r.routing.destination_queue}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    {r.routing.escalation_flag ? (
                      <Badge className="bg-red-100 text-red-700">Yes</Badge>
                    ) : (
                      <Badge className="bg-gray-100 text-gray-500">No</Badge>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-400">
                    {formatTimestamp(r.timestamp)}
                  </td>
                  <td className="max-w-xs px-4 py-3 text-xs text-gray-600 truncate">{r.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

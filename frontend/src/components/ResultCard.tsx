import type { ProcessedRecord } from "../types";
import { formatConfidence, formatTimestamp, PRIORITY_COLORS, QUEUE_COLORS } from "../lib/utils";
import { cn } from "../lib/utils";
import { AlertTriangle } from "lucide-react";

function Badge({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold",
        className
      )}
    >
      {children}
    </span>
  );
}

function Field({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <dt className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</dt>
      <dd className="mt-1 text-sm text-slate-800">{children}</dd>
    </div>
  );
}

interface Props {
  record: ProcessedRecord;
}

export function ResultCard({ record }: Props) {
  const { classification, enrichment, routing, summary } = record;
  const escalated = routing.escalation_flag;

  return (
    <div
      className={cn(
        "rounded-xl border shadow-sm overflow-hidden",
        escalated ? "border-red-200" : "border-slate-200"
      )}
    >
      {/* Escalation banner */}
      {escalated && (
        <div className="flex items-center gap-2.5 border-b border-red-200 bg-red-50 px-5 py-3">
          <AlertTriangle className="h-4 w-4 flex-shrink-0 text-red-600" />
          <div>
            <span className="text-sm font-semibold text-red-800">Escalated</span>
            {routing.escalation_reason && (
              <span className="ml-2 text-sm text-red-600">{routing.escalation_reason}</span>
            )}
          </div>
        </div>
      )}

      <div className="bg-white p-6 space-y-5">
        {/* Header row */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-slate-900">{record.id}</h3>
            <p className="text-xs text-slate-400 mt-0.5">{formatTimestamp(record.timestamp)} · {record.source}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge
              className={
                PRIORITY_COLORS[classification.priority] ?? "bg-slate-100 text-slate-600"
              }
            >
              {classification.priority}
            </Badge>
            <Badge
              className={
                QUEUE_COLORS[routing.destination_queue] ?? "bg-slate-100 text-slate-600"
              }
            >
              → {routing.destination_queue}
            </Badge>
          </div>
        </div>

        {/* Classification grid */}
        <div className="grid grid-cols-2 gap-4 rounded-lg bg-slate-50 p-4 sm:grid-cols-4">
          <Field label="Category">{classification.category}</Field>
          <Field label="Priority">{classification.priority}</Field>
          <Field label="Confidence">{formatConfidence(classification.confidence_score)}</Field>
          <Field label="Model">
            <span className="font-mono text-xs text-slate-600">{record.model_used}</span>
          </Field>
        </div>

        {/* Enrichment */}
        <div className="space-y-3">
          <Field label="Core Issue">{enrichment.core_issue}</Field>
          <Field label="Urgency Signal">
            <span className="text-slate-600">{enrichment.urgency_signal}</span>
          </Field>

          {Object.keys(enrichment.identifiers).length > 0 && (
            <Field label="Identifiers">
              <div className="mt-1 flex flex-wrap gap-1.5">
                {Object.entries(enrichment.identifiers).map(([k, v]) => (
                  <span
                    key={k}
                    className="rounded-md border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-700"
                  >
                    <span className="font-medium text-slate-500">{k}:</span> {v}
                  </span>
                ))}
              </div>
            </Field>
          )}
        </div>

        {/* Summary */}
        <div>
          <dt className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
            Handoff Summary
          </dt>
          <dd className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-relaxed text-slate-700">
            {summary}
          </dd>
        </div>
      </div>
    </div>
  );
}

import type { ProcessedRecord } from "../types";
import { formatConfidence, formatTimestamp, PRIORITY_COLORS, QUEUE_COLORS } from "../lib/utils";
import { cn } from "../lib/utils";

function Badge({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={cn("inline-block rounded-full px-2.5 py-0.5 text-xs font-medium", className)}>
      {children}
    </span>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-gray-400">{label}</dt>
      <dd className="mt-0.5 text-sm text-gray-800">{children}</dd>
    </div>
  );
}

interface Props {
  record: ProcessedRecord;
}

export function ResultCard({ record }: Props) {
  const { classification, enrichment, routing, summary } = record;

  return (
    <div className={cn(
      "rounded-xl border p-6 shadow-sm",
      routing.escalation_flag ? "border-red-200 bg-red-50" : "border-green-200 bg-white"
    )}>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Result — {record.id}</h3>
        <div className="flex gap-2">
          <Badge className={PRIORITY_COLORS[classification.priority] ?? "bg-gray-100 text-gray-600"}>
            {classification.priority}
          </Badge>
          <Badge className={QUEUE_COLORS[routing.destination_queue] ?? "bg-gray-100 text-gray-600"}>
            {routing.destination_queue}
          </Badge>
          {routing.escalation_flag && (
            <Badge className="bg-red-100 text-red-700">Escalated</Badge>
          )}
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
        <Field label="Category">{classification.category}</Field>
        <Field label="Confidence">{formatConfidence(classification.confidence_score)}</Field>
        <Field label="Source">{record.source}</Field>
        <Field label="Model">{record.model_used}</Field>
        <Field label="Timestamp">{formatTimestamp(record.timestamp)}</Field>
      </dl>

      <div className="mt-4 space-y-3">
        <Field label="Core Issue">{enrichment.core_issue}</Field>
        <Field label="Urgency Signal">{enrichment.urgency_signal}</Field>

        {Object.keys(enrichment.identifiers).length > 0 && (
          <Field label="Identifiers">
            <div className="flex flex-wrap gap-1 mt-1">
              {Object.entries(enrichment.identifiers).map(([k, v]) => (
                <span key={k} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                  {k}: {v}
                </span>
              ))}
            </div>
          </Field>
        )}

        {routing.escalation_reason && (
          <Field label="Escalation Reason">
            <span className="text-red-700">{routing.escalation_reason}</span>
          </Field>
        )}

        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-gray-400">Summary</dt>
          <dd className="mt-1 rounded-lg bg-gray-50 p-3 text-sm leading-relaxed text-gray-700">
            {summary}
          </dd>
        </div>
      </div>
    </div>
  );
}
